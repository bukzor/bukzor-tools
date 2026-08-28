"""Cut a session JSONL's tail -- the cut `/rewind` cannot reach.

The operation for a poisoned or unwanted ending: mid-turn tails,
harness-injected turns, an era that belonged to someone else. See
`Skill(claude-code-surgery)` for when to do this at all.

Two output modes; dry-run (neither) previews the plan and touches
nothing:

- `--write` lands the kept prefix as a NEW session under a fresh id
  (or --session-id), records retargeted exactly as branch extraction
  does -- sessionId rewritten, resume leaf re-anchored on the kept
  tip -- and prints the new file's path on stdout. The original is
  never opened for writing, so this is safe even on a live session:
  an append-only file's kept prefix is already frozen.
- `--in-place` keeps the file's own id, for when the id is
  load-bearing: a subagent is bound to its `agentId`, and a session's
  `subagents/` stay reachable only under its own id. Kept lines are
  preserved byte-for-byte; a timestamped backup lands beside the file
  (or in --backup-dir) before anything is written; a file modified in
  the last minute is presumed live and refused (--force-live
  overrides). A kept `last-prompt` anchored in the dropped era is
  reported; --repoint-leaf rewrites that one record (the sole
  exception to never-rewrite).

Either way, a cut that would leave a `tool_use` with no `tool_result`
is refused outright, with the nearest clean boundary suggested.

Usage:
    claude-jsonl-truncate <session.jsonl> <ref> [--write | --in-place]
    claude-jsonl-truncate <session.jsonl> --match REGEX [--write | --in-place]
    claude-jsonl-truncate <session.jsonl> --check

`<ref>` is a uuid or line number naming the FIRST record to drop; with
--match, the first record whose raw line matches the regex. --check
diagnoses the current tail without naming a cut.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import uuid as uuidlib
from collections.abc import Mapping, Sequence
from pathlib import Path

from . import session as session_mod
from .branch_extract import resolve_ref, rewrite, write_jsonl
from .session import JsonValue, Node, Record, Session

LIVE_SECONDS = 60
"""A transcript this recently modified is presumed to have a live writer."""


def content_blocks(node: Node) -> list[Record]:
    """The message content blocks of a record, [] where there are none.

    >>> content_blocks(Node(1, {"type": "user", "message": {"content": [
    ...     {"type": "tool_result", "tool_use_id": "t1"}, "stray",
    ... ]}}))
    [{'type': 'tool_result', 'tool_use_id': 't1'}]
    >>> content_blocks(Node(1, {"type": "mode", "mode": "default"}))
    []
    """
    msg: Record | None = node.record.get("message")
    if not isinstance(msg, Mapping):
        return []
    content: str | list[JsonValue] | None = msg.get("content")
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, Mapping)]


def dangling_tool_uses(nodes: Sequence[Node]) -> set[str]:
    """tool_use ids in `nodes` whose tool_result is not also in `nodes`.

    A cut may not strand one: the resumed agent would sit on an
    unanswerable call forever.

    >>> use = Node(1, {"type": "assistant", "message": {"content": [
    ...     {"type": "tool_use", "id": "t1", "name": "Bash"}]}})
    >>> result = Node(2, {"type": "user", "message": {"content": [
    ...     {"type": "tool_result", "tool_use_id": "t1"}]}})
    >>> dangling_tool_uses([use, result])
    set()
    >>> dangling_tool_uses([use])
    {'t1'}
    """
    uses: set[str] = set()
    results: set[str] = set()
    for node in nodes:
        for block in content_blocks(node):
            kind = block.get("type")
            if kind == "tool_use" and isinstance(block.get("id"), str):
                uses.add(block["id"])
            elif kind == "tool_result" and isinstance(block.get("tool_use_id"), str):
                results.add(block["tool_use_id"])
    return uses - results


def latest_clean_cut(nodes: Sequence[Node], at: Node) -> Node | None:
    """The latest record at-or-before `at` where cutting leaves no dangling
    tool_use; None when no boundary at all is clean (never, in practice --
    an empty prefix is clean).

    >>> use = Node(1, {"type": "assistant", "message": {"content": [
    ...     {"type": "tool_use", "id": "t1", "name": "Bash"}]}})
    >>> result = Node(2, {"type": "user", "message": {"content": [
    ...     {"type": "tool_result", "tool_use_id": "t1"}]}})
    >>> text = Node(3, {"type": "assistant", "message": {"content": [
    ...     {"type": "text", "text": "done"}]}})
    >>> latest_clean_cut([use, result, text], result).line
    1
    >>> latest_clean_cut([use, result, text], text).line
    3
    """
    candidates = [n for n in nodes if n.line <= at.line]
    for boundary in reversed(candidates):
        kept = [n for n in nodes if n.line < boundary.line]
        if not dangling_tool_uses(kept):
            return boundary
    return None


def dangling_leaf(kept: Sequence[Node]) -> str | None:
    """The leafUuid a kept `last-prompt` names, when the kept records lack
    it -- resume anchors there, so a dangling one wants --repoint-leaf.
    None when there is no last-prompt or its leaf survives the cut.

    >>> spine = Node(1, {"type": "user", "uuid": "a"})
    >>> dangling_leaf([spine, Node(2, {"type": "last-prompt", "leafUuid": "a"})])
    >>> dangling_leaf([spine, Node(2, {"type": "last-prompt", "leafUuid": "gone"})])
    'gone'
    >>> dangling_leaf([spine])
    """
    kept_uuids = {n.uuid for n in kept if n.uuid}
    leaf: str | None = None
    for node in kept:
        if node.type == "last-prompt":
            raw = node.record.get("leafUuid")
            leaf = raw if isinstance(raw, str) else None
    if leaf is None or leaf in kept_uuids:
        return None
    return leaf


def leaf_anchor(kept: Sequence[Node]) -> Node:
    """The record resume should anchor on: the newest kept speaker.

    Mirrors `Session.tip_of`: resume anchors only on user/assistant
    records, newest timestamp winning, line order breaking ties.

    >>> a = Node(1, {"uuid": "a", "type": "user",
    ...              "timestamp": "2026-01-01T00:00:00Z"})
    >>> b = Node(2, {"uuid": "b", "type": "assistant",
    ...              "timestamp": "2026-01-01T00:00:05Z"})
    >>> late = Node(3, {"uuid": "c", "type": "attachment",
    ...                 "timestamp": "2026-01-01T00:00:09Z"})
    >>> leaf_anchor([a, b, late]).uuid
    'b'
    """
    speakers = [n for n in kept if n.type in ("user", "assistant") and n.uuid]
    assert speakers, [n.line for n in kept]
    return max(speakers, key=lambda n: (n.timestamp or "", n.line))


def find_match(sess: Session, raw_lines: Sequence[str], pattern: str) -> Node:
    """The first record whose raw line matches `pattern` -- the grep-shaped
    locator, for boundaries easier to name by content than by uuid.
    """
    rx = re.compile(pattern)
    for node in sess.nodes:
        if rx.search(raw_lines[node.line - 1]):
            return node
    raise SystemExit(f"no record matches {pattern!r}")


def describe(node: Node) -> str:
    """One line a human can check a cut plan against."""
    uuid8 = (node.uuid or "-")[:8]
    ts = (node.timestamp or "")[:19]
    text = (
        " ".join(
            str(b.get("text") or b.get("name") or "") for b in content_blocks(node)
        ).strip()
        or str(node.record.get("content", ""))[:60]
    )
    return f"[{node.line}] {node.type} {uuid8} {ts} {text[:60]!r}"


def repoint_leaf_line(raw_line: str, leaf: str) -> str:
    """That one record, re-anchored -- the documented never-rewrite exception.

    >>> repoint_leaf_line('{"type": "last-prompt", "leafUuid": "gone"}\\n', "a")
    '{"type": "last-prompt", "leafUuid": "a"}\\n'
    """
    rec = json.loads(raw_line)
    rec["leafUuid"] = leaf
    return json.dumps(rec) + "\n"


def write_truncated(path: Path, kept_raw: Sequence[str], backup_dir: Path) -> Path:
    """Impure: back up, then atomically replace `path` with the kept lines.

    Returns the backup path. Backup first, unconditionally: the backup is
    the undo.
    """
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = backup_dir / f"{path.stem}.pre-truncate.{stamp}{path.suffix}"
    assert not backup.exists(), backup
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(kept_raw))
    tmp.replace(path)
    return backup


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("path", type=Path, help="session or subagent JSONL")
    p.add_argument(
        "ref", nargs="?", help="uuid or line number of the first record to drop"
    )
    p.add_argument("--match", help="regex; first matching raw line is the cut point")
    p.add_argument("--check", action="store_true", help="diagnose the tail; no cut")
    p.add_argument(
        "--write",
        action="store_true",
        help="write the kept prefix as a new session; prints its path (default: dry run)",
    )
    p.add_argument(
        "--in-place", action="store_true", help="cut the file itself, keeping its id"
    )
    p.add_argument(
        "--session-id", default=None, help="id for the new session (default: uuid4)"
    )
    p.add_argument(
        "--backup-dir", type=Path, default=None, help="default: beside the file"
    )
    p.add_argument(
        "--force-live", action="store_true", help="cut even a recently-written file"
    )
    p.add_argument(
        "--repoint-leaf",
        action="store_true",
        help="re-anchor a kept last-prompt whose leafUuid was dropped",
    )
    args = p.parse_args()
    if args.check == bool(args.ref or args.match) or (args.ref and args.match):
        p.error("name a cut point (ref | --match) or diagnose with --check")
    if args.repoint_leaf and not args.in_place:
        p.error("--repoint-leaf implies --in-place; the new-session mode re-anchors")
    return args


def report_check(sess: Session) -> int:
    """Diagnose the current tail: dangling tool_uses and the last record."""
    dangling = dangling_tool_uses(sess.nodes)
    print(f"tail: {describe(sess.nodes[-1])}", file=sys.stderr)
    if dangling:
        print(f"dangling tool_use: {sorted(dangling)}", file=sys.stderr)
        return 3
    print("clean: every tool_use has its result", file=sys.stderr)
    return 0


def main() -> int:
    args = parse_args()
    sess = session_mod.load(args.path)
    if not sess.nodes:
        print(f"empty or unparseable: {args.path}", file=sys.stderr)
        return 1
    if args.check:
        return report_check(sess)

    with args.path.open() as f:
        raw = f.readlines()
    target = (
        find_match(sess, raw, args.match) if args.match else resolve_ref(sess, args.ref)
    )
    kept_nodes = [n for n in sess.nodes if n.line < target.line]
    if not kept_nodes:
        print(f"cut at {describe(target)} keeps nothing; refusing", file=sys.stderr)
        return 2

    print(f"cut at:   {describe(target)}", file=sys.stderr)
    print(f"new tail: {describe(kept_nodes[-1])}", file=sys.stderr)
    print(
        f"keeps {target.line - 1} of {len(raw)} lines"
        f" ({len(sess.nodes) - len(kept_nodes)} records dropped)",
        file=sys.stderr,
    )

    dangling = dangling_tool_uses(kept_nodes)
    if dangling:
        print(f"REFUSED: cut strands tool_use {sorted(dangling)}", file=sys.stderr)
        clean = latest_clean_cut(sess.nodes, target)
        if clean and clean.line != target.line:
            print(f"nearest clean cut: {describe(clean)}", file=sys.stderr)
        return 3

    leaf = dangling_leaf(kept_nodes)
    if leaf and not args.repoint_leaf:
        print(
            f"note: kept last-prompt anchors on dropped {leaf!r};"
            " --in-place wants --repoint-leaf (a new session re-anchors itself)",
            file=sys.stderr,
        )
    if args.in_place:
        return cut_in_place(args, raw, kept_nodes, target.line - 1, leaf)
    if args.write:
        return cut_new_session(args, sess, kept_nodes)
    print(
        "dry run; --write lands a new session, --in-place cuts this file",
        file=sys.stderr,
    )
    return 0


def cut_in_place(
    args: argparse.Namespace,
    raw: Sequence[str],
    kept_nodes: Sequence[Node],
    cut_line: int,
    leaf: str | None,
) -> int:
    """Impure: the same-id cut -- liveness-guarded, backed up, byte-preserving."""
    age = time.time() - args.path.stat().st_mtime
    if age < LIVE_SECONDS and not args.force_live:
        print(
            f"REFUSED: modified {age:.0f}s ago -- stop the writer first"
            " (--force-live overrides)",
            file=sys.stderr,
        )
        return 4
    kept_raw = list(raw[:cut_line])
    if leaf and args.repoint_leaf:
        anchor = leaf_anchor(kept_nodes)
        fixes = [n for n in kept_nodes if n.type == "last-prompt"]
        idx = fixes[-1].line - 1
        kept_raw[idx] = repoint_leaf_line(kept_raw[idx], anchor.uuid or "")
        print(f"repointed leafUuid {leaf!r} -> {anchor.uuid}", file=sys.stderr)
    backup = write_truncated(args.path, kept_raw, args.backup_dir or args.path.parent)
    print(f"backup: {backup}", file=sys.stderr)
    print(f"cut done: now ends at {describe(kept_nodes[-1])}", file=sys.stderr)
    print(args.path)
    return 0


def cut_new_session(
    args: argparse.Namespace, sess: Session, kept_nodes: Sequence[Node]
) -> int:
    """Impure: land the kept prefix as a fresh resumable session."""
    new_sid = args.session_id or str(uuidlib.uuid4())
    out = session_mod.project_dir_for(sess.path) / f"{new_sid}.jsonl"
    if out.exists():
        print(f"refusing to overwrite existing: {out}", file=sys.stderr)
        return 2
    anchor = leaf_anchor(kept_nodes)
    count = write_jsonl(rewrite(kept_nodes, anchor, new_sid), out)
    print(
        f"wrote {count} records; resume:"
        f" cd {sess.cwd(among=list(kept_nodes))} && claude --resume {new_sid}",
        file=sys.stderr,
    )
    print(out)
    return 0
