from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from .cli import format_changes, header, parse_args
from .config_test import DEFAULTS
from .sweep import Change

TODAY = date(2026, 6, 1)
CONFIG = replace(DEFAULTS, quarantine_dir="lost-and-found")
TMP = Path("/home/bukzor/tmp")


class DescribeParseArgs:
    def it_reports_without_writing_by_default(self):
        assert not parse_args([]).write

    def it_writes_only_when_asked(self):
        assert parse_args(["--write"]).write
        assert parse_args(["-w"]).write

    def it_refuses_the_flag_that_used_to_mean_dry_run(self):
        """A silently-accepted -n would read as a safeguard while writing."""
        with pytest.raises(SystemExit):
            parse_args(["-n"])

    def it_takes_roots_positionally(self):
        assert parse_args(["/x", "/y"]).root == [Path("/x"), Path("/y")]


class DescribeHeader:
    def it_names_the_batch_things_move_into(self):
        assert header("quarantine", CONFIG, TODAY, dry_run=True) == (
            "# would quarantine, to lost-and-found/2026-06-01/"
        )

    def it_names_the_directory_things_are_deleted_from(self):
        assert header("purge", CONFIG, TODAY, dry_run=True) == (
            "# would purge, from lost-and-found/"
        )

    def it_speaks_in_the_past_once_the_work_is_done(self):
        assert header("quarantine", CONFIG, TODAY, dry_run=False) == (
            "# quarantined, to lost-and-found/2026-06-01/"
        )
        assert header("purge", CONFIG, TODAY, dry_run=False) == (
            "# purged, from lost-and-found/"
        )

    def it_refuses_a_verb_it_has_no_wording_for(self):
        with pytest.raises(AssertionError):
            header("incinerate", CONFIG, TODAY, dry_run=True)


class DescribeFormatChanges:
    def it_says_nothing_about_nothing(self):
        assert list(format_changes([], CONFIG, TODAY, dry_run=True)) == []

    def it_states_the_action_and_root_once_each(self):
        changes = [
            Change("quarantine", TMP, "README.md"),
            Change("quarantine", TMP, "notes.txt"),
        ]
        assert list(format_changes(changes, CONFIG, TODAY, dry_run=True)) == [
            "# would quarantine, to lost-and-found/2026-06-01/",
            "/home/bukzor/tmp/",
            "  README.md",
            "  notes.txt",
        ]

    def it_repeats_the_root_only_when_it_changes(self):
        other = Path("/home/bukzor/repo/x/trash")
        changes = [
            Change("quarantine", TMP, "a"),
            Change("quarantine", other, "b"),
        ]
        assert list(format_changes(changes, CONFIG, TODAY, dry_run=True)) == [
            "# would quarantine, to lost-and-found/2026-06-01/",
            "/home/bukzor/tmp/",
            "  a",
            "/home/bukzor/repo/x/trash/",
            "  b",
        ]

    def it_separates_the_two_kinds_of_change(self):
        changes = [
            Change("quarantine", TMP, "a"),
            Change("purge", TMP, "2020-01-01", " (14 entries)"),
        ]
        assert list(format_changes(changes, CONFIG, TODAY, dry_run=True)) == [
            "# would quarantine, to lost-and-found/2026-06-01/",
            "/home/bukzor/tmp/",
            "  a",
            "",
            "# would purge, from lost-and-found/",
            "/home/bukzor/tmp/",
            "  2020-01-01 (14 entries)",
        ]
