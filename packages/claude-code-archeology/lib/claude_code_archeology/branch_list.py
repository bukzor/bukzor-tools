"""Print a Claude Code session JSONL as a tree, marking branch points.

Usage:
    claude-branch-list <session.jsonl> [--branches-only]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from . import session as session_mod
from . import tree as tree_mod
from .timefmt import Clock


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="session JSONL file")
    p.add_argument(
        "--branches-only",
        action="store_true",
        help="show only branch points, their children, and tips",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    sess = session_mod.load(args.path)
    if not sess.nodes:
        print(f"empty or unparseable: {args.path}", file=sys.stderr)
        return 1

    tz = datetime.now().astimezone().tzinfo
    assert tz is not None
    clock = Clock(tz)

    bps = sess.branch_points()
    print(f"# session: {sess.session_id or '?'}", file=sys.stderr)
    print(f"# file:    {args.path}", file=sys.stderr)
    print(f"# nodes:   {len(sess.nodes)}", file=sys.stderr)
    print(f"# branches: {len(bps)}  tips: {len(sess.tips())}", file=sys.stderr)
    print(file=sys.stderr)

    tree_mod.render(sess, branches_only=args.branches_only, clock=clock)
    return 0
