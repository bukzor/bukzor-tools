"""Render a session as a tree to stdout, marking real branch points.

A "real" branch is a node whose children include >1 user-text message —
that's what a rewind looks like. Single-child chains and tool-flow forks
(attachment + tool_result under one tool_use; parallel tool_use blocks)
are collapsed/de-noised.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import TextIO

from .format_short import label
from .session import Node, Session, is_user_text
from .timefmt import Clock

# ANSI
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BR_YELLOW = "\033[93m"


def user_text_child_count(sess: Session, parent_uuid: str) -> int:
    """Real-fork detector: count user-text children under one parent.

    Parallel tool calls within one assistant turn create multiple
    assistant-tool_use children — those are not forks. Tool_use chains
    create user(tool_result) children — also not forks.

    >>> from pathlib import Path
    >>> from .session import build_session, Node
    >>> sess = build_session(Path("x"), iter([
    ...     Node(0, {"uuid": "a", "parentUuid": None, "type": "user",
    ...              "message": {"content": "root"}}),
    ...     Node(1, {"uuid": "b", "parentUuid": "a", "type": "user",
    ...              "message": {"content": "rewrite-1"}}),
    ...     Node(2, {"uuid": "c", "parentUuid": "a", "type": "user",
    ...              "message": {"content": "rewrite-2"}}),
    ...     Node(3, {"uuid": "d", "parentUuid": "a", "type": "user",
    ...              "message": {"content": [{"type": "tool_result"}]}}),
    ... ]))
    >>> user_text_child_count(sess, "a")
    2
    """
    return sum(
        1
        for cu in sess.children.get(parent_uuid, [])
        if cu in sess.by_uuid and is_user_text(sess.by_uuid[cu])
    )


def active_path_uuids(sess: Session) -> set[str]:
    """Approximation of the chain `/resume` walks: ancestors of the last node."""
    if not sess.nodes:
        return set()
    for node in reversed(sess.nodes):
        if node.uuid:
            return {n.uuid for n in sess.ancestors_of(node.uuid) if n.uuid}
    return set()


def _stamp(ts: str, clock: Clock) -> str:
    """Record timestamps are UTC on disk; render them via `clock`, not verbatim.

    A raw `ts[11:19]` slice is the record's UTC clock digits printed as if
    they were local -- right next to filesystem mtimes that genuinely are
    local, an easy way to misjudge how far apart two events actually were.

    >>> from datetime import timezone
    >>> _stamp("2026-01-01T00:30:00.123Z", Clock(timezone.utc))
    '[Jan01 00:30 +0000]'
    >>> _stamp("", Clock(timezone.utc))
    ''
    >>> _stamp("not-a-timestamp", Clock(timezone.utc))
    'not-a-timestamp'
    """
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return ts
    return clock.stamp(int(dt.timestamp() * 1_000_000_000))


def format_line(
    node: Node, depth: int, mc_children: int, on_active: bool, clock: Clock
) -> str:
    indent = "  " * depth
    branch_marker = (
        f" {BR_YELLOW}[FORK×{mc_children}]{RESET}" if mc_children > 1 else ""
    )
    stamp = _stamp(node.timestamp or "", clock)
    type_color = {
        "user": CYAN,
        "assistant": MAGENTA,
        "system": YELLOW,
    }.get(node.type, DIM)
    type_str = f"{type_color}{node.type:9s}{RESET}"
    lbl = label(node)
    line_num = f"{node.line:5d}"
    uuid_short = (node.uuid or "")[:8]
    style = BOLD if (mc_children > 1 and not on_active) else ""
    return (
        f"{indent}{DIM}{line_num} {uuid_short}{RESET} {stamp} {type_str} "
        f"{style}{lbl}{RESET}{branch_marker}"
    )


def should_show(
    sess: Session, node: Node, n_kids: int, mc: int, branches_only: bool
) -> bool:
    if not branches_only:
        return True
    parent = node.parent_uuid
    parent_is_fork = parent is not None and user_text_child_count(sess, parent) > 1
    this_is_fork = mc > 1
    is_tip = n_kids == 0
    return parent_is_fork or this_is_fork or (is_tip and is_user_text(node))


def walk(
    sess: Session,
    uuid: str,
    depth: int,
    *,
    branches_only: bool,
    active: set[str],
    out: TextIO,
    clock: Clock,
) -> None:
    if uuid not in sess.by_uuid:
        return
    node = sess.by_uuid[uuid]
    kids = sess.children.get(uuid, [])
    mc = user_text_child_count(sess, uuid)
    if should_show(sess, node, len(kids), mc, branches_only):
        out.write(format_line(node, depth, mc, uuid in active, clock) + "\n")
    new_depth = depth + 1 if mc > 1 else depth
    for k in kids:
        walk(
            sess,
            k,
            new_depth,
            branches_only=branches_only,
            active=active,
            out=out,
            clock=clock,
        )


def render(
    sess: Session,
    *,
    branches_only: bool = False,
    out: TextIO = sys.stdout,
    clock: Clock | None = None,
) -> None:
    """Render the session tree to `out`.

    `branches_only=True` shows only nodes on a path that crosses a real fork.
    Per-line times go through `clock` (default: a fresh one on the system
    zone) -- record timestamps are stored UTC, so this is a conversion, not
    a relabeling. `clock` renders each row against the *previous printed
    row*, but a DFS walk isn't chronological (a rewind's sibling branch can
    predate or postdate the branch just finished) -- so a delta can go
    negative at a branch return. That's signal, not noise: it's the reader's
    cue that the tree just jumped, the same way a run of near-zero deltas
    elsewhere is the cue that nothing did.
    """
    if clock is None:
        tz = datetime.now().astimezone().tzinfo
        assert tz is not None
        clock = Clock(tz)
    active = active_path_uuids(sess)
    for root in sess.root_nodes():
        if root.uuid:
            walk(
                sess,
                root.uuid,
                0,
                branches_only=branches_only,
                active=active,
                out=out,
                clock=clock,
            )
