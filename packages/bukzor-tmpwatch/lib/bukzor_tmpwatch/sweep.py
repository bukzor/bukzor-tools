"""Two-phase sweep of one scratch root.

Nothing is deleted that was not first quarantined somewhere visible: an idle
top-level entry moves to `<root>/lost-and-found/<sweep-date>/`, and a whole
quarantine batch is deleted once its own datestamp is old enough.
"""

import os
import shutil
from collections.abc import Container, Iterator, Sequence
from datetime import date
from pathlib import Path

QUARANTINE_DIR = "lost-and-found"
PROC_STAT = Path("/proc/stat")


def boot_stamp() -> int:
    """Epoch seconds at which this kernel booted."""
    for line in PROC_STAT.read_text().splitlines():
        field, _, value = line.partition(" ")
        if field == "btime":
            return int(value)
    raise AssertionError(PROC_STAT)


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


def proc_sweep(
    root: Path,
    idle_cutoff: float,
    purge_cutoff: date,
    today: date,
    keep: Container[str],
    dry_run: bool,
) -> Iterator[str]:
    """Quarantine then purge `root`, yielding one report line per action."""
    batch = root / QUARANTINE_DIR / today.isoformat()
    for entry in idle_entries(root, idle_cutoff, keep):
        if not dry_run:
            batch.mkdir(parents=True, exist_ok=True)
            shutil.move(entry, batch / entry.name)
        verb = "would quarantine" if dry_run else "quarantined"
        yield f"{verb} {entry} -> {batch}/"
    for stale in expired_batches(root / QUARANTINE_DIR, purge_cutoff):
        count = entry_count(stale)
        if not dry_run:
            shutil.rmtree(stale)
        verb = "would purge" if dry_run else "purged"
        yield f"{verb} {stale} ({count} entries)"


__all__: Sequence[str] = (
    "QUARANTINE_DIR",
    "boot_stamp",
    "entry_count",
    "expired_batches",
    "has_recent_write",
    "idle_entries",
    "parse_datestamp",
    "proc_sweep",
)
