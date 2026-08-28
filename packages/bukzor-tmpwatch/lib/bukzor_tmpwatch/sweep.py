"""Two-phase sweep of one scratch root.

Nothing is deleted that was not first quarantined somewhere visible: an idle
top-level entry moves to `<root>/<quarantine dir>/<sweep date>/`, and a whole
quarantine batch is deleted once its own datestamp is old enough. The two
phases are separate passes so that a report can group by phase across roots.
"""

import os
import shutil
from collections.abc import Container, Iterator, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .config import Config

SECONDS_PER_DAY = 24 * 60 * 60


@dataclass(frozen=True)
class Change:
    """One entry a sweep moved or deleted, or would have.

    The destination is not recorded: it is the same for every change of one
    kind, so the report states it once in a header rather than on every line.
    """

    verb: str
    root: Path
    name: str
    detail: str = ""


def parse_datestamp(name: str) -> date | None:
    """`name` as a date, or None unless it is exactly YYYY-MM-DD."""
    try:
        stamp = date.fromisoformat(name)
    except ValueError:
        return None
    return stamp if stamp.isoformat() == name else None


def has_recent_write(path: Path, cutoff: float) -> bool:
    """Whether anything at or under `path` has an mtime at or after `cutoff`.

    A directory's own mtime tracks only its direct children, so an entry whose
    activity is buried deep would otherwise read as idle. Symlinks are examined,
    never followed.
    """
    if path.lstat().st_mtime >= cutoff:
        return True
    for dirpath, dirnames, filenames in os.walk(path):
        for name in (*dirnames, *filenames):
            if (Path(dirpath) / name).lstat().st_mtime >= cutoff:
                return True
    return False


def idle_entries(root: Path, cutoff: float, keep: Container[str]) -> list[Path]:
    """Top-level entries under `root` with no write since `cutoff`.

    A symlink is a pointer, not content: sweeping one loses wiring and moves no
    data, so symlinks are never idle. Names in `keep` are never swept.
    """
    return [
        entry
        for entry in sorted(root.iterdir())
        if entry.name not in keep
        and not entry.is_symlink()
        and not has_recent_write(entry, cutoff)
    ]


def expired_batches(quarantine: Path, cutoff: date) -> list[Path]:
    """Quarantine batches whose own datestamped name predates `cutoff`.

    Keying retention on the name rather than on timestamps is what keeps it
    legible: a move preserves mtime but resets ctime, so a timestamp-based
    purge would silently restart the clock on everything it just quarantined.
    Names that are not datestamps are left alone.
    """
    if not quarantine.is_dir():
        return []
    return sorted(
        batch
        for batch in quarantine.iterdir()
        if batch.is_dir()
        and (stamp := parse_datestamp(batch.name)) is not None
        and stamp < cutoff
    )


def entry_count(path: Path) -> int:
    """How many paths a batch holds, for the purge report."""
    return sum(1 for _ in path.rglob("*"))


def proc_quarantine(
    root: Path, config: Config, now: float, today: date, dry_run: bool
) -> Iterator[Change]:
    """Move every idle entry in `root` into today's batch."""
    batch = root / config.quarantine_dir / today.isoformat()
    # Quarantining the quarantine would rename a directory into its own
    # subdirectory, so it is exempt whatever the configuration says.
    keep = config.keep | {config.quarantine_dir}
    cutoff = now - config.quarantine_after_days * SECONDS_PER_DAY
    for entry in idle_entries(root, cutoff, keep):
        if not dry_run:
            batch.mkdir(parents=True, exist_ok=True)
            shutil.move(entry, batch / entry.name)
        yield Change("quarantine", root, entry.name)


def proc_purge(
    root: Path, config: Config, today: date, dry_run: bool
) -> Iterator[Change]:
    """Delete every quarantine batch in `root` that has waited long enough."""
    quarantine = root / config.quarantine_dir
    cutoff = today - timedelta(days=config.purge_after_days)
    for stale in expired_batches(quarantine, cutoff):
        count = entry_count(stale)
        if not dry_run:
            shutil.rmtree(stale)
        yield Change("purge", root, stale.name, f" ({count} entries)")


__all__: Sequence[str] = (
    "SECONDS_PER_DAY",
    "Change",
    "entry_count",
    "expired_batches",
    "has_recent_write",
    "idle_entries",
    "parse_datestamp",
    "proc_purge",
    "proc_quarantine",
)
