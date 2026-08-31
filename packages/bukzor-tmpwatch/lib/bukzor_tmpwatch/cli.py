"""Garbage-collect scratch directories, without ever deleting unannounced.

Reports by default and changes nothing; --write applies. That inverts the
tmpwatch tradition on purpose: previewing when you meant to act costs one
re-run, acting when you meant to preview costs data.

An idle entry moves to a dated batch inside its root's quarantine directory,
and that batch is deleted purge-after-days later. That second wait is the floor
on how long anything survives, and it is a month: a file moved into a scratch
directory keeps its old mtime, so it can be quarantined by the very next sweep
with no wait at all, and everything it gets, it gets after quarantine -- in a
directory you can see and move it back out of.

Which directories are swept, how long each wait is, and what is exempt are all
settings, one plain-text file each under $XDG_CONFIG_HOME/bukzor-tmpwatch/.
Every one must exist; run bukzor-tmpwatch-install to write them.
"""

import argparse
import signal
import sys
import time
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import replace
from datetime import date
from itertools import chain
from pathlib import Path

from .config import Config, MissingSettings, config_dir, load_config
from .roots import scratch_roots
from .sweep import Change, proc_purge, proc_quarantine

PAST = {"quarantine": "quarantined", "purge": "purged"}


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
        type=whole_days,
        default=None,
        metavar="DAYS",
        help="override the quarantine-after-days setting",
    )
    parser.add_argument(
        "--purge-after",
        type=whole_days,
        default=None,
        metavar="DAYS",
        help="override the purge-after-days setting",
    )
    return parser.parse_args(argv)


def whole_days(value: str) -> int:
    """A count of days from the command line: zero or more, as a file must be.

    A negative wait puts the cutoff in the future, which purges the batch the
    same sweep just made.
    """
    if not value.isdigit():
        raise argparse.ArgumentTypeError(f"not a whole number of days: {value!r}")
    return int(value)


def header(verb: str, config: Config, today: date, dry_run: bool) -> str:
    """The line introducing every change of one kind."""
    tense = f"would {verb}" if dry_run else PAST[verb]
    if verb == "quarantine":
        return f"# {tense}, to {config.quarantine_dir}/{today.isoformat()}/"
    elif verb == "purge":
        return f"# {tense}, from {config.quarantine_dir}/"
    else:
        raise AssertionError(verb)


def format_changes(
    changes: Iterable[Change], config: Config, today: date, dry_run: bool
) -> Iterator[str]:
    """The report: each action named once, each root named once, then names.

    `changes` must be grouped by verb and then by root, which is the order the
    two sweep phases produce across all roots.
    """
    verb: str | None = None
    root: Path | None = None
    for change in changes:
        if change.verb != verb:
            if verb is not None:
                yield ""
            verb, root = change.verb, None
            yield header(change.verb, config, today, dry_run)
        if change.root != root:
            root = change.root
            yield f"{change.root}/"
        yield f"  {change.name}{change.detail}"


def remembering(changes: Iterable[Change], seen: list[Change]) -> Iterator[Change]:
    """Yield each change as it happens, recording it for the closing summary.

    The report streams, so a sweep that fails partway has still said what it
    did before it failed. Collecting first would move a thousand files and then
    print nothing at all.
    """
    for change in changes:
        seen.append(change)
        yield change


def settings(args: argparse.Namespace) -> Config:
    """The configuration this run should use, with any flag applied over it."""
    config = load_config(config_dir())
    if args.quarantine_after is not None:
        config = replace(config, quarantine_after_days=args.quarantine_after)
    if args.purge_after is not None:
        config = replace(config, purge_after_days=args.purge_after)
    return config


def main() -> int:
    # Die quietly when a reader such as head(1) goes away, the way any filter
    # does, rather than raising BrokenPipeError out of print(). Every move and
    # delete has already happened by the time anything is printed.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    args = parse_args(sys.argv[1:])
    try:
        config = settings(args)
    except MissingSettings as error:
        # Defaulting would let this delete things by a rule nobody chose.
        (missing,) = error.args
        for path in missing:
            print(f"no such setting: {path}", file=sys.stderr)
        print("run bukzor-tmpwatch-install to write the defaults", file=sys.stderr)
        return 2

    roots = [
        root
        for root in (args.root or scratch_roots(Path.home(), config))
        if root.is_dir()
    ]
    now = time.time()
    today = date.today()
    dry_run = not args.write
    # Both phases run over every root before the next begins, so the report can
    # state each action once instead of once per root.
    changes = chain(
        (
            change
            for root in roots
            for change in proc_quarantine(root, config, now, today, dry_run)
        ),
        (
            change
            for root in roots
            for change in proc_purge(root, config, today, dry_run)
        ),
    )
    seen: list[Change] = []
    for line in format_changes(remembering(changes, seen), config, today, dry_run):
        print(line)
    if seen and dry_run:
        # Through a pipe stdout is block-buffered and stderr is not, so without
        # this the hint overtakes the report it is commenting on.
        sys.stdout.flush()
        # The default is the opposite of tmpwatch's, so say so once.
        print(f"nothing changed; --write to apply these {len(seen)}", file=sys.stderr)
    return 0
