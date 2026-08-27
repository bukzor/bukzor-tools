"""Extract an orphaned branch into a new session JSONL you can resume.

The Claude Code rewind bug (anthropics/claude-code#55347) leaves orphaned
branches unreachable: `/resume` picks one chain at load time -- the newest
message whose uuid is registered as a `leafUuid`, walked back via
`parentUuid` -- and the in-session rewind picker only walks that chain
backward. There is no fast-forward, and no UI reaches a sibling branch.
So we hand-build a file whose newest leaf is the branch you want.

Given any record on a branch, this traces *forward* to that branch's tip
(you can rewind afterward; you cannot fast-forward), collects every record
belonging to it, and writes them out under a fresh `sessionId`.

`--at` cuts just past the named record instead of running to the branch
tip. What that buys is narrower than it looks, because the default plus
`/rewind` already covers a lot: resume the whole branch and the in-session
picker will cut it at any prompt of *yours*. So `--at` is for the states
that leaves out -- one that must *keep* an assistant reply or a tool
result and drop what came after it, one sitting inside a turn, or a
promoted subagent's, whose user-role records are tool results rather than
prompts. Wanting a reply answered differently is not one of those: rewind
to the prompt that produced it and send it again.

The other half of the case is economy. Rewinding drops the later era
after the session has loaded it; `--at` drops it before, which is the
difference between resuming 185 records and 701.

The cut keeps one message *after* the ref, because the two errors are not
symmetric. A message cut away is gone from the resumed session and only
another extraction brings it back; a message kept too many is droppable
there, since `/rewind` offers your own prompts as cut points and the
message following an assistant reply is one of those. The ref is also
usually the record a search matched, and what you want to resume is the
exchange it belongs to -- the reply that answers the prompt you found, the
reaction that follows the turn you found -- not its first half.

`--as-session` re-homes a subagent transcript as a session of its own.
Subagent records live beside their parent, marked `isSidechain`, and
`--resume` never offers them; stripping the marks and pointing `cwd` at
the directory the work belongs in makes the extracted branch resumable
like any other session.

"Belonging to it" is more than the parent chain -- attachments, file
snapshots and session settings hang off the chain rather than living in
it, and most of them belong to *other* branches. See `belongs_to_branch`.

Usage:
    claude-branch-extract <session.jsonl> <ref>
                                             [--out PATH] [--session-id ID]

`<ref>` can be a full uuid or an integer line number from `branch_list`;
any record on the branch will do, including the one your grep found.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid as uuidlib
from collections.abc import Iterator
from pathlib import Path

from . import session as session_mod
from .inventory import PROJECTS_DIR
from .session import Node, Record, Session

# Session-scoped settings, keyed by sessionId rather than by message: Claude
# Code reads only the final record of each type, so keeping every historical
# one is dead weight -- and keeping any written *after* our tip would import
# a sibling branch's title, mode or leaf pointer.
LAST_WINS = frozenset(
    {
        "last-prompt",
        "custom-title",
        "ai-title",
        "tag",
        "mode",
        "permission-mode",
        "relocated",
        "agent-name",
        "agent-color",
        "agent-setting",
    }
)


def resolve_ref(sess: Session, ref: str) -> Node:
    """Find the record named by a uuid or a branch_list line number."""
    if ref in sess.by_uuid:
        return sess.by_uuid[ref]
    try:
        line = int(ref)
    except ValueError:
        raise SystemExit(
            f"ref {ref!r} is neither a uuid in this file nor an int line number"
        )
    for n in sess.nodes:
        if n.line == line:
            return n
    raise SystemExit(f"line {line} not found in {sess.path}")


def message_after(sess: Session, node: Node) -> Node | None:
    """Pure: the next user/assistant record after `node` on its branch.

    None when `node` is the branch's last message. Records that are not
    messages -- attachments, system notices, file-history snapshots --
    are skipped rather than counted, since a cut landing on one of those
    would keep no more conversation than cutting at the ref.

    >>> from pathlib import Path
    >>> from .session import build_session
    >>> sess = build_session(Path("x"), iter([
    ...     Node(1, {"uuid": "a", "parentUuid": None, "type": "user"}),
    ...     Node(2, {"uuid": "b", "parentUuid": "a", "type": "assistant"}),
    ...     Node(3, {"uuid": "sys", "parentUuid": "b", "type": "system"}),
    ...     Node(4, {"uuid": "c", "parentUuid": "sys", "type": "user"}),
    ... ]))
    >>> message_after(sess, sess.by_uuid["b"]).uuid
    'c'
    >>> print(message_after(sess, sess.by_uuid["c"]))
    None
    """
    assert node.uuid, node
    tip = sess.tip_of(node.uuid)
    if tip is None or not tip.uuid:
        return None
    passed = False
    for n in sess.ancestors_of(tip.uuid):
        if passed and n.type in ("user", "assistant"):
            return n
        passed = passed or n.uuid == node.uuid
    return None


def belongs_to_branch(sess: Session, chain: set[str], node: Node) -> bool:
    """Pure: is `node` structurally part of the branch whose spine is `chain`?

    Three ways to belong, mirroring how Claude Code reassembles a session:

    - the conversation spine itself (`uuid` in the parent chain);
    - decorations hanging off the spine -- attachments and system notices
      name their message as `parentUuid`. Sibling *branch heads* hang off
      the spine too, which is exactly what we are shedding, so user and
      assistant records are excluded here;
    - file-history snapshots and deltas, which reference their message by
      `messageId` (these back `/rewind`'s file restore).

    Session-scoped settings belong to no message at all; `branch_records`
    handles those.
    """
    rec, uuid = node.record, node.uuid
    if uuid and uuid in chain:
        return True
    if node.type in LAST_WINS:
        return False
    if rec.get("messageId"):
        return rec["messageId"] in chain
    if uuid and node.parent_uuid in chain:
        return node.type not in ("user", "assistant")
    return False


def branch_records(sess: Session, tip: Node) -> list[Node]:
    """Pure: every record of tip's branch, in file order, last-wins collapsed.

    Settings are kept up to the branch's last record -- past that point the
    file is describing some other branch -- and then collapsed to the final
    one of each type, since that is all Claude Code will read.

    The off-branch attachment is dropped despite sitting between two kept
    records; `early` is dropped as superseded, `sibling-era` as too late.

    >>> from pathlib import Path
    >>> from .session import build_session
    >>> sess = build_session(Path("x"), iter([
    ...     Node(0, {"uuid": "a", "parentUuid": None, "type": "user"}),
    ...     Node(1, {"type": "mode", "mode": "early"}),
    ...     Node(2, {"uuid": "keep", "parentUuid": "a", "type": "attachment"}),
    ...     Node(3, {"type": "mode", "mode": "current"}),
    ...     Node(4, {"uuid": "b", "parentUuid": "a", "type": "assistant"}),
    ...     Node(5, {"uuid": "sibling", "parentUuid": "a", "type": "user"}),
    ...     Node(6, {"uuid": "drop", "parentUuid": "sibling", "type": "attachment"}),
    ...     Node(7, {"type": "file-history-snapshot", "messageId": "b"}),
    ...     Node(8, {"type": "file-history-snapshot", "messageId": "sibling"}),
    ...     Node(9, {"type": "mode", "mode": "sibling-era"}),
    ... ]))
    >>> [n.uuid or n.record.get("mode") or n.record["messageId"]
    ...  for n in branch_records(sess, sess.by_uuid["b"])]
    ['a', 'keep', 'current', 'b', 'b']
    """
    assert tip.uuid, tip
    chain = {n.uuid for n in sess.ancestors_of(tip.uuid) if n.uuid}
    assert chain, (sess.path, tip.line)
    kept = [n for n in sess.nodes if belongs_to_branch(sess, chain, n)]
    cutoff = max(n.line for n in kept)
    settings = [n for n in sess.nodes if n.type in LAST_WINS and n.line <= cutoff]
    survivor = {n.type: n.line for n in settings}
    kept += [n for n in settings if survivor[n.type] == n.line]
    kept.sort(key=lambda n: n.line)
    return kept


SIDECHAIN_MARKS = ("isSidechain", "agentId", "attributionAgent")
"""What marks a record as a subagent's rather than a session's own."""


def promoted(rec: Record, cwd: str | None) -> Record:
    """Pure: one record as a top-level session's, run from `cwd`.

    A subagent inherits its parent's `cwd`, so a promoted branch usually
    belongs somewhere else -- and the projects/<slug>/ dir it is written
    to must agree with the `cwd` it claims, or resume looks in the wrong
    place.

    >>> sorted(promoted({"isSidechain": True, "agentId": "a", "cwd": "/p"},
    ...                 "/w").items())
    [('cwd', '/w')]
    """
    if cwd is None:
        return rec
    kept = {k: v for k, v in rec.items() if k not in SIDECHAIN_MARKS}
    if "cwd" in kept:
        kept["cwd"] = cwd
    return kept


def project_dir_for_cwd(cwd: str) -> Path:
    """The projects/<slug>/ dir holding sessions run from `cwd`.

    Encoding only: the slug maps both '/' and '.' to '-', which is why
    reading a cwd back out of a dir name is not allowed anywhere here.

    >>> project_dir_for_cwd("/home/u/repo/a.b").name
    '-home-u-repo-a-b'
    """
    return PROJECTS_DIR / re.sub(r"[/.]", "-", cwd)


def rewrite(
    records: Iterator[Node], tip: Node, new_session_id: str, cwd: str | None = None
) -> Iterator[Record]:
    """Pure: retarget records at a new session, pinning tip as its leaf.

    uuid/parentUuid are preserved, so cross-references survive; only
    `sessionId` changes. The surviving `last-prompt` record carries the
    `leafUuid` that resume anchors on, so it is repointed at our tip --
    without that, a stale pointer into a branch we just dropped could
    leave the new session unresumable.

    >>> from pathlib import Path
    >>> from .session import build_session
    >>> sess = build_session(Path("x"), iter([
    ...     Node(0, {"uuid": "a", "parentUuid": None,
    ...              "sessionId": "old", "type": "user"}),
    ...     Node(1, {"type": "last-prompt", "sessionId": "old", "leafUuid": "gone"}),
    ... ]))
    >>> for rec in rewrite(iter(sess.nodes), sess.by_uuid["a"], "new"):
    ...     print(sorted(rec.items()))
    [('parentUuid', None), ('sessionId', 'new'), ('type', 'user'), ('uuid', 'a')]
    [('leafUuid', 'a'), ('sessionId', 'new'), ('type', 'last-prompt')]
    """
    pinned = False
    for node in records:
        rec = dict(promoted(node.record, cwd))
        if "sessionId" in rec:
            rec["sessionId"] = new_session_id
        if rec.get("type") == "last-prompt":
            rec["leafUuid"], pinned = tip.uuid, True
        yield rec
    if not pinned:
        yield {"type": "last-prompt", "sessionId": new_session_id, "leafUuid": tip.uuid}


def write_jsonl(records: Iterator[Record], out_path: Path) -> int:
    """Impure: write records as JSONL. Returns count written."""
    written = 0
    with out_path.open("w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
            written += 1
    return written


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="source session JSONL")
    p.add_argument("ref", help="uuid or line number of any record on the branch")
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output path (default: <slug>/<new-uuid>.jsonl)",
    )
    p.add_argument(
        "--session-id",
        default=None,
        help="session id for the new file (default: random uuid4)",
    )
    p.add_argument(
        "--at",
        action="store_true",
        help="cut just past ref (ref plus the next message) instead of"
        " running to its branch tip -- everything after is dropped",
    )
    p.add_argument(
        "--as-session",
        metavar="CWD",
        default=None,
        help="re-home a subagent branch as its own session, run from CWD",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    sess = session_mod.load(args.path)
    if not sess.nodes:
        print(f"empty or unparseable: {args.path}", file=sys.stderr)
        return 1

    ref = resolve_ref(sess, args.ref)
    assert ref.uuid, (args.path, args.ref)
    tip = (message_after(sess, ref) or ref) if args.at else sess.tip_of(ref.uuid)
    assert tip, (args.path, args.ref)
    new_sid = args.session_id or str(uuidlib.uuid4())
    home = (
        project_dir_for_cwd(args.as_session)
        if args.as_session
        else session_mod.project_dir_for(sess.path)
    )
    out = args.out or home / f"{new_sid}.jsonl"
    if out.exists():
        print(f"refusing to overwrite existing: {out}", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)

    kept = branch_records(sess, tip)
    count = write_jsonl(rewrite(iter(kept), tip, new_sid, args.as_session), out)
    if args.as_session:
        print(
            "promoted: the agent definition does not come with it --"
            " model, effort and tool access are the resuming session's.",
            file=sys.stderr,
        )
    print(f"wrote {count} of {len(sess.nodes)} records to {out}", file=sys.stderr)
    if tip.line != ref.line:
        label = "cut after" if args.at else "branch tip"
        print(f"{label}: line {tip.line} {tip.uuid} ({tip.timestamp})", file=sys.stderr)
    print(
        f"resume it:  cd {args.as_session or sess.cwd(among=kept)}"
        f" && claude --resume {new_sid}",
        file=sys.stderr,
    )
    print(out)
    return 0
