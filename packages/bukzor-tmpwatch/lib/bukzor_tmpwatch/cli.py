"""Garbage-collect scratch directories, without ever deleting unannounced.

Roots are ~/tmp and every gitignored trash/ below $HOME. An entry idle for
--quarantine-after days moves to <root>/lost-and-found/<today>/; a batch there
is deleted --purge-after days after the sweep that made it. Nothing vanishes in
under a month, and it spends the second half of that month somewhere you can
see it and move it back.
"""

import argparse
import sys
import time
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path

from .roots import scratch_roots
from .sweep import QUARANTINE_DIR, boot_stamp, proc_sweep

QUARANTINE_AFTER_DAYS = 15
PURGE_AFTER_DAYS = 15
SECONDS_PER_DAY = 24 * 60 * 60


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "root",
        nargs="*",
        type=Path,
        help="sweep these roots instead of the discovered ones",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="report what would happen, change nothing",
    )
    parser.add_argument(
        "--quarantine-after",
        type=int,
        default=QUARANTINE_AFTER_DAYS,
        metavar="DAYS",
    )
    parser.add_argument(
        "--purge-after",
        type=int,
        default=PURGE_AFTER_DAYS,
        metavar="DAYS",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])
    roots: list[Path] = args.root or scratch_roots(Path.home())
    today = date.today()
    # The live boot's tree is never idle, however quiet it looks.
    keep = {QUARANTINE_DIR, f"boot={boot_stamp()}"}
    for root in roots:
        if not root.is_dir():
            continue
        for line in proc_sweep(
            root,
            idle_cutoff=time.time() - args.quarantine_after * SECONDS_PER_DAY,
            purge_cutoff=today - timedelta(days=args.purge_after),
            today=today,
            keep=keep,
            dry_run=args.dry_run,
        ):
            print(line)
    return 0
