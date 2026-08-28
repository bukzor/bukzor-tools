"""Garbage-collect scratch directories, without ever deleting unannounced.

Reports by default and changes nothing; --write applies. That inverts the
tmpwatch tradition on purpose: previewing when you meant to act costs one
re-run, acting when you meant to preview costs data.

An idle entry moves to a dated batch inside its root's quarantine directory,
and that batch is deleted a further wait later. Nothing vanishes in under a
month, and it spends the second half of that month somewhere you can see it
and move it back.

Which directories are swept, how long each wait is, and what is exempt are all
settings, one plain-text file each under $XDG_CONFIG_HOME/bukzor-tmpwatch/.
Run bukzor-tmpwatch-install to write the annotated defaults there.
"""

import argparse
import sys
import time
from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from pathlib import Path

from .config import config_dir, load_config
from .roots import scratch_roots
from .sweep import proc_sweep


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "root",
        nargs="*",
        type=Path,
        help="sweep these roots instead of the configured ones",
    )
    parser.add_argument(
        "-w",
        "--write",
        action="store_true",
        help="actually move and delete; without it, only report",
    )
    parser.add_argument(
        "--quarantine-after",
        type=int,
        default=None,
        metavar="DAYS",
        help="override the quarantine-after-days setting",
    )
    parser.add_argument(
        "--purge-after",
        type=int,
        default=None,
        metavar="DAYS",
        help="override the purge-after-days setting",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])
    config = load_config(config_dir())
    if args.quarantine_after is not None:
        config = replace(config, quarantine_after_days=args.quarantine_after)
    if args.purge_after is not None:
        config = replace(config, purge_after_days=args.purge_after)
    roots: list[Path] = args.root or scratch_roots(Path.home(), config)
    now = time.time()
    today = date.today()
    reported = 0
    for root in roots:
        if not root.is_dir():
            continue
        for line in proc_sweep(root, config, now, today, dry_run=not args.write):
            print(line)
            reported += 1
    if reported and not args.write:
        # The default is the opposite of tmpwatch's, so say so once.
        print(f"nothing changed; --write to apply these {reported}", file=sys.stderr)
    return 0
