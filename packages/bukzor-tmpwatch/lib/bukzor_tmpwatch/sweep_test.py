import os
from dataclasses import replace
from datetime import date
from pathlib import Path

from .config_test import DEFAULTS
from .sweep import (
    Change,
    entry_count,
    expired_batches,
    has_recent_write,
    idle_entries,
    parse_datestamp,
    proc_purge,
    proc_quarantine,
)

OLD = 1_000_000_000.0
NEW = 2_000_000_000.0
CUTOFF = 1_500_000_000.0
TODAY = date(2026, 6, 1)
QUARANTINE = DEFAULTS.quarantine_dir
# Anything idle at all is quarantined, and a batch is purged a month later, so
# a test says what it means by the timestamps it sets rather than by arithmetic.
NOW = replace(DEFAULTS, quarantine_after_days=0, purge_after_days=30)


def age(path: Path, when: float) -> None:
    os.utime(path, (when, when), follow_symlinks=False)


def make_tree(root: Path, relative: str, when: float) -> Path:
    """A file at `root/relative`, with every directory made to look old."""
    leaf = root / relative
    leaf.parent.mkdir(parents=True, exist_ok=True)
    leaf.write_text("x")
    age(leaf, when)
    for parent in leaf.parents:
        age(parent, OLD)
        if parent == root:
            break
    return leaf


class DescribeParseDatestamp:
    def it_reads_an_iso_date(self):
        assert parse_datestamp("2026-08-28") == date(2026, 8, 28)

    def it_rejects_anything_else(self):
        assert parse_datestamp("20260828") is None
        assert parse_datestamp("notes") is None


class DescribeHasRecentWrite:
    def it_sees_a_write_buried_deep(self, tmp_path: Path):
        make_tree(tmp_path, "a/b/c.txt", NEW)
        assert has_recent_write(tmp_path, CUTOFF)

    def it_reports_none_when_everything_is_old(self, tmp_path: Path):
        make_tree(tmp_path, "a/b/c.txt", OLD)
        assert not has_recent_write(tmp_path, CUTOFF)

    def it_does_not_follow_symlinks(self, tmp_path: Path):
        make_tree(tmp_path, "elsewhere/fresh.txt", NEW)
        home = tmp_path / "home"
        home.mkdir()
        (home / "link").symlink_to(tmp_path / "elsewhere")
        age(home / "link", OLD)
        age(home, OLD)
        assert not has_recent_write(home, CUTOFF)


class DescribeIdleEntries:
    def it_returns_only_entries_with_no_recent_write(self, tmp_path: Path):
        make_tree(tmp_path, "stale/deep.txt", OLD)
        make_tree(tmp_path, "busy/deep.txt", NEW)
        assert idle_entries(tmp_path, CUTOFF, keep=()) == [tmp_path / "stale"]

    def it_never_sweeps_a_symlink(self, tmp_path: Path):
        (tmp_path / "link").symlink_to(tmp_path / "absent")
        age(tmp_path / "link", OLD)
        assert idle_entries(tmp_path, CUTOFF, keep=()) == []

    def it_honors_kept_names(self, tmp_path: Path):
        make_tree(tmp_path, "notes/old.txt", OLD)
        assert idle_entries(tmp_path, CUTOFF, keep={"notes"}) == []


class DescribeExpiredBatches:
    def it_expires_batches_older_than_the_cutoff(self, tmp_path: Path):
        (tmp_path / "2026-01-01").mkdir()
        assert expired_batches(tmp_path, date(2026, 6, 1)) == [tmp_path / "2026-01-01"]

    def it_keeps_a_batch_dated_on_the_cutoff(self, tmp_path: Path):
        (tmp_path / "2026-06-01").mkdir()
        assert expired_batches(tmp_path, date(2026, 6, 1)) == []

    def it_ignores_names_that_are_not_datestamps(self, tmp_path: Path):
        (tmp_path / "keepsakes").mkdir()
        assert expired_batches(tmp_path, date(2026, 6, 1)) == []

    def it_tolerates_a_root_that_has_never_been_swept(self, tmp_path: Path):
        assert expired_batches(tmp_path / "absent", date(2026, 6, 1)) == []


class DescribeEntryCount:
    def it_counts_every_path_below(self, tmp_path: Path):
        make_tree(tmp_path, "a/b.txt", OLD)
        assert entry_count(tmp_path) == 2


class DescribeProcQuarantine:
    def it_moves_an_idle_entry_into_a_dated_batch(self, tmp_path: Path):
        make_tree(tmp_path, "stale/deep.txt", OLD)
        assert list(proc_quarantine(tmp_path, NOW, CUTOFF, TODAY, False)) == [
            Change("quarantine", tmp_path, "stale")
        ]
        assert (tmp_path / QUARANTINE / "2026-06-01/stale/deep.txt").exists()

    def it_never_quarantines_the_quarantine_itself(self, tmp_path: Path):
        """Renaming a directory into its own subdirectory cannot be undone."""
        make_tree(tmp_path, f"{QUARANTINE}/2026-05-30/recent.txt", OLD)
        assert list(proc_quarantine(tmp_path, NOW, CUTOFF, TODAY, False)) == []
        assert (tmp_path / QUARANTINE / "2026-05-30/recent.txt").exists()

    def it_honors_a_renamed_quarantine(self, tmp_path: Path):
        make_tree(tmp_path, "stale/deep.txt", OLD)
        config = replace(NOW, quarantine_dir="attic")
        list(proc_quarantine(tmp_path, config, CUTOFF, TODAY, False))
        assert (tmp_path / "attic/2026-06-01/stale/deep.txt").exists()

    def it_exempts_the_names_the_config_keeps(self, tmp_path: Path):
        make_tree(tmp_path, "notes/old.txt", OLD)
        config = replace(NOW, keep=frozenset({"notes"}))
        assert list(proc_quarantine(tmp_path, config, CUTOFF, TODAY, False)) == []
        assert (tmp_path / "notes/old.txt").exists()

    def it_waits_the_configured_number_of_days(self, tmp_path: Path):
        """A day short of the wait is not idle yet."""
        make_tree(tmp_path, "stale/deep.txt", CUTOFF - 9 * 86400)
        config = replace(NOW, quarantine_after_days=10)
        assert list(proc_quarantine(tmp_path, config, CUTOFF, TODAY, False)) == []
        assert (tmp_path / "stale/deep.txt").exists()

    def it_changes_nothing_when_dry(self, tmp_path: Path):
        make_tree(tmp_path, "stale/deep.txt", OLD)
        assert list(proc_quarantine(tmp_path, NOW, CUTOFF, TODAY, True)) == [
            Change("quarantine", tmp_path, "stale")
        ]
        assert (tmp_path / "stale/deep.txt").exists()


class DescribeProcPurge:
    def it_deletes_an_expired_batch(self, tmp_path: Path):
        make_tree(tmp_path, f"{QUARANTINE}/2026-01-01/old.txt", OLD)
        assert list(proc_purge(tmp_path, NOW, TODAY, False)) == [
            Change("purge", tmp_path, "2026-01-01", " (1 entries)")
        ]
        assert not (tmp_path / QUARANTINE / "2026-01-01").exists()

    def it_keeps_a_batch_younger_than_the_purge_wait(self, tmp_path: Path):
        make_tree(tmp_path, f"{QUARANTINE}/2026-05-30/recent.txt", OLD)
        assert list(proc_purge(tmp_path, NOW, TODAY, False)) == []
        assert (tmp_path / QUARANTINE / "2026-05-30/recent.txt").exists()

    def it_changes_nothing_when_dry(self, tmp_path: Path):
        make_tree(tmp_path, f"{QUARANTINE}/2026-01-01/old.txt", OLD)
        assert list(proc_purge(tmp_path, NOW, TODAY, True)) == [
            Change("purge", tmp_path, "2026-01-01", " (1 entries)")
        ]
        assert (tmp_path / QUARANTINE / "2026-01-01/old.txt").exists()
