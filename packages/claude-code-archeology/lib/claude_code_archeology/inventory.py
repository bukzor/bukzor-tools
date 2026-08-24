"""List resumable Claude Code sessions across projects, newest first.

Answers "what was I working on, and how do I pick it back up?" after a
crash, freeze, or reboot: one row per session file with last-activity
time, working directory, and a human label; `--sh` emits paste-ready
resume commands instead.

Usage:
    claude-inventory [--days N | --all] [--sh]
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import session as session_mod
from .format_short import truncate
from .session import Node, Session, is_user_text
from .timefmt import Clock

PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Harness-injected user-role text; useless as a "what was this session about" label.
BOILERPLATE_PREFIXES = (
    "Base directory for this skill:",
    "This session is being continued",
    "[Request interrupted",
    "Caveat: the messages below",
    "<command-",
    "<local-command",
)


def is_substantive(text: str) -> bool:
    """Whether this user message could serve as the session's label.

    Harness-injected text, slash commands, and my own shorthand ("c",
    "s", "...") all say nothing about the topic, and the shorthand is
    what a session most often ends on -- so an unfiltered "last thing the
    user typed" label is usually the least informative line in the file.

    >>> is_substantive("fix the balloon driver")
    True
    >>> is_substantive("c"), is_substantive("...."), is_substantive("  ")
    (False, False, False)
    >>> is_substantive("/compact"), is_substantive("<command-name>x")
    (False, False)
    >>> is_substantive("This session is being continued from...")
    False
    """
    text = text.strip()
    return (
        len(text) >= 4
        and any(c.isalnum() for c in text)
        and not text.startswith("/")
        and not text.startswith(BOILERPLATE_PREFIXES)
    )


@dataclass(frozen=True)
class Summary:
    mtime_ns: int
    session_id: str
    cwd: str | None
    label: str
    path: Path
    sidechain: bool = False


def summarize(
    sess: Session, mtime_ns: int, resumable_only: bool = True
) -> Summary | None:
    """Distill one session file to an inventory row; None if not resumable.

    Sidechain files (subagent transcripts) and empty files are not
    independently resumable. The label prefers an explicit title record,
    falling back to the last thing the user typed.

    Search wants the sidechains too -- a subagent's transcript is still a
    record of what happened -- so `resumable_only=False` keeps them,
    flagged, rather than dropping them.

    >>> from .session import Node, build_session
    >>> sess = build_session(Path("p/abc.jsonl"), iter([
    ...     Node(0, {"uuid": "a", "parentUuid": None, "type": "user",
    ...              "sessionId": "sid-1", "cwd": "/w",
    ...              "message": {"content": "fix the bug"}}),
    ...     Node(1, {"type": "ai-title", "title": "Bug fixing"}),
    ... ]))
    >>> s = summarize(sess, mtime_ns=1786216000_000000000)
    >>> s.session_id, s.cwd, s.label
    ('sid-1', '/w', 'Bug fixing')
    >>> untitled = build_session(Path("p/def.jsonl"), iter([
    ...     Node(0, {"uuid": "a", "parentUuid": None, "type": "user",
    ...              "message": {"content": "do things"}}),
    ... ]))
    >>> summarize(untitled, 0).session_id, summarize(untitled, 0).label
    ('def', 'do things')
    >>> noisy = build_session(Path("p/x.jsonl"), iter([
    ...     Node(0, {"uuid": "a", "parentUuid": None, "type": "user",
    ...              "message": {"content": "real question"}}),
    ...     Node(1, {"uuid": "b", "parentUuid": "a", "type": "user",
    ...              "message": {"content": "Base directory for this skill: /x"}}),
    ... ]))
    >>> summarize(noisy, 0).label
    'real question'
    >>> summarize(build_session(Path("x"), iter([])), 0) is None
    True
    >>> sidechain = build_session(Path("x"), iter([
    ...     Node(0, {"uuid": "a", "parentUuid": None, "type": "user",
    ...              "isSidechain": True, "message": {"content": "sub"}}),
    ... ]))
    >>> summarize(sidechain, 0) is None
    True
    >>> summarize(sidechain, 0, resumable_only=False).sidechain
    True
    """
    if not sess.nodes:
        return None
    is_sidechain = bool(sess.nodes[0].record.get("isSidechain"))
    if is_sidechain and resumable_only:
        return None
    titles = [
        n.record["title"]
        for n in sess.nodes
        if n.type in ("custom-title", "ai-title") and n.record.get("title")
    ]

    def text_of(n: Node) -> str:
        msg = n.record["message"]["content"]
        return msg if isinstance(msg, str) else msg[0].get("text", "")

    user_texts = [text_of(n) for n in sess.nodes if is_user_text(n)]
    speech = [t for t in user_texts if is_substantive(t)]
    if titles:
        label = titles[-1]
    elif speech or user_texts:
        label = (speech or user_texts)[-1]
    else:
        label = "(no user messages)"
    return Summary(
        mtime_ns=mtime_ns,
        session_id=sess.session_id or sess.path.stem,
        cwd=sess.cwd(),
        label=truncate(label, 60),
        path=sess.path,
        sidechain=is_sidechain,
    )


def _shorten(path: str, home: str) -> str:
    """
    >>> _shorten("/home/u/proj", "/home/u")
    '~/proj'
    >>> _shorten("/home/u", "/home/u")
    '~'
    >>> _shorten("/home/unrelated", "/home/u")
    '/home/unrelated'
    >>> _shorten("/etc", "/home/u")
    '/etc'
    """
    if path == home or path.startswith(home + "/"):
        return "~" + path.removeprefix(home)
    else:
        return path


def format_row(s: Summary, clock: Clock, home: str) -> str:
    """One aligned human-readable line per session.

    `clock` is shared across a run of rows in chronological order -- see
    `timefmt.Clock` -- so consecutive close-together sessions read as a
    cluster of small deltas, not two independent absolute stamps a reader
    has to diff by hand.

    >>> from datetime import timezone
    >>> from .timefmt import Clock
    >>> s = Summary(mtime_ns=1786216000_000000000, session_id="0e9272f7-aaaa-bbbb",
    ...             cwd="/home/u/proj", label="Bug fixing", path=Path("x"))
    >>> format_row(s, clock=Clock(timezone.utc), home="/home/u")
    '[Aug08 19:06 +0000]  0e9272f7  ~/proj  Bug fixing'

    A subagent transcript is marked, because `--resume` cannot open one.

    >>> import dataclasses
    >>> format_row(dataclasses.replace(s, sidechain=True), Clock(timezone.utc), "/home/u")
    '[Aug08 19:06 +0000]  0e9272f7  ~/proj  [subagent] Bug fixing'
    """
    cwd = _shorten(s.cwd, home) if s.cwd else "(cwd unknown)"
    mark = "[subagent] " if s.sidechain else ""
    return f"{clock.stamp(s.mtime_ns)}  {s.session_id[:8]}  {cwd}  {mark}{s.label}"


def format_sh(s: Summary, clock: Clock, home: str) -> str:
    """A paste-ready resume command, labeled by a comment line.

    >>> from datetime import timezone
    >>> from .timefmt import Clock
    >>> s = Summary(mtime_ns=1786216000_000000000, session_id="0e9272f7-aaaa-bbbb",
    ...             cwd="/home/u/proj", label="Bug fixing", path=Path("x"))
    >>> print(format_sh(s, clock=Clock(timezone.utc), home="/home/u"))
    # [Aug08 19:06 +0000]  Bug fixing
    (cd ~/proj && claude --resume 0e9272f7-aaaa-bbbb)
    """
    comment = f"# {clock.stamp(s.mtime_ns)}  {s.label}"
    if not s.cwd:
        return f"{comment}\n# no cwd recorded; resume from its original directory: {s.path}"
    return f"{comment}\n(cd {_shorten(s.cwd, home)} && claude --resume {s.session_id})"


def scan(projects_dir: Path, cutoff_ns: int | None) -> list[Summary]:
    """Load every recent-enough session file. Newest first."""
    out: list[Summary] = []
    for path in projects_dir.glob("*/*.jsonl"):
        mtime_ns = path.stat().st_mtime_ns
        if cutoff_ns is not None and mtime_ns < cutoff_ns:
            continue
        summary = summarize(session_mod.load(path), mtime_ns)
        if summary:
            out.append(summary)
    return sorted(out, key=lambda s: s.mtime_ns, reverse=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--days", type=float, default=7.0, help="how far back to look (default 7)"
    )
    p.add_argument("--all", action="store_true", help="no time limit")
    p.add_argument(
        "--sh", action="store_true", help="emit resume commands instead of a table"
    )
    p.add_argument("--projects-dir", type=Path, default=PROJECTS_DIR)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cutoff_ns = (
        None if args.all else int(time.time() * 1e9) - int(args.days * 86400 * 1e9)
    )
    summaries = scan(args.projects_dir, cutoff_ns)
    tz = datetime.now().astimezone().tzinfo
    assert tz, tz
    clock = Clock(tz)
    home = str(Path.home())
    fmt = format_sh if args.sh else format_row
    for s in summaries:
        print(fmt(s, clock, home))
    print(f"# {len(summaries)} sessions", file=sys.stderr)
    return 0
