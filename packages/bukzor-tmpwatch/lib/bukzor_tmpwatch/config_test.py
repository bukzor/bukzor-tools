import time
from dataclasses import replace
from pathlib import Path

import pytest

from . import config as config_module
from .config import (
    APP,
    DEFAULT_KEEP,
    DEFAULT_PRUNE,
    DEFAULT_PURGE_AFTER_DAYS,
    DEFAULT_QUARANTINE_AFTER_DAYS,
    DEFAULT_QUARANTINE_DIR,
    DEFAULT_ROOTS,
    DEFAULT_TRASH_DIR,
    TEMPLATES,
    Config,
    MissingSettings,
    boot_stamp,
    config_dir,
    expand_keep,
    load_config,
    missing_settings,
    parse_lines,
    read_days,
    read_value,
    read_values,
    setting_names,
    xdg_config_home,
)
from .install import proc_write_settings

# A Config for tests elsewhere: the real defaults, but with nothing exempt and
# no roots of its own, so a test states only what it is about.
DEFAULTS = Config(
    roots=(),
    prune=frozenset(DEFAULT_PRUNE),
    keep=frozenset(),
    trash_dir=DEFAULT_TRASH_DIR,
    quarantine_dir=DEFAULT_QUARANTINE_DIR,
    quarantine_after_days=DEFAULT_QUARANTINE_AFTER_DAYS,
    purge_after_days=DEFAULT_PURGE_AFTER_DAYS,
)


def write(directory: Path, name: str, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text)


def seed(directory: Path) -> Path:
    """A settings directory holding every default, as the installer leaves it."""
    proc_write_settings(directory)
    return directory


class DescribeParseLines:
    def it_drops_comments_and_surrounding_space(self):
        assert parse_lines("# note\n\n  a  \nb # why\n") == ["a", "b"]

    def it_reads_nothing_from_an_all_comment_file(self):
        assert parse_lines("# only\n# comments\n") == []


class DescribeXdgConfigHome:
    def it_honors_the_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert xdg_config_home() == tmp_path

    def it_falls_back_to_dot_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        assert xdg_config_home() == tmp_path / ".config"


class DescribeConfigDir:
    def it_is_named_for_the_command(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert config_dir() == tmp_path / APP


class DescribeMissingSettings:
    def it_names_every_file_an_empty_directory_lacks(self, tmp_path: Path):
        assert missing_settings(tmp_path) == [
            tmp_path / name for name in setting_names()
        ]

    def it_names_nothing_once_the_settings_are_written(self, tmp_path: Path):
        assert missing_settings(seed(tmp_path)) == []

    def it_names_only_what_is_gone(self, tmp_path: Path):
        seed(tmp_path)
        (tmp_path / "keep").unlink()
        assert missing_settings(tmp_path) == [tmp_path / "keep"]


class DescribeReadValues:
    def it_refuses_a_setting_that_has_no_file(self, tmp_path: Path):
        """Guessing a default is how a sweep silently disagrees with its owner."""
        with pytest.raises(MissingSettings):
            read_values(tmp_path, "roots")

    def it_reads_one_value_per_line(self, tmp_path: Path):
        write(tmp_path, "prune", "target\n.venv\n")
        assert read_values(tmp_path, "prune") == ["target", ".venv"]

    def it_takes_an_emptied_file_as_the_empty_list(self, tmp_path: Path):
        """Emptying a file is how a setting is switched off."""
        write(tmp_path, "prune", "# nothing\n")
        assert read_values(tmp_path, "prune") == []

    def it_spells_a_setting_with_dashes(self, tmp_path: Path):
        write(tmp_path, "trash-dir", "scratch\n")
        assert read_values(tmp_path, "trash_dir") == ["scratch"]


class DescribeReadValue:
    def it_refuses_a_second_value(self, tmp_path: Path):
        write(tmp_path, "trash-dir", "a\nb\n")
        with pytest.raises(AssertionError):
            read_value(tmp_path, "trash_dir")

    def it_is_empty_when_the_file_is(self, tmp_path: Path):
        write(tmp_path, "trash-dir", "")
        assert read_value(tmp_path, "trash_dir") == ""


class DescribeReadDays:
    def it_reads_a_whole_number(self, tmp_path: Path):
        write(tmp_path, "purge-after-days", "3\n")
        assert read_days(tmp_path, "purge_after_days") == 3

    def it_refuses_anything_that_is_not_one(self, tmp_path: Path):
        write(tmp_path, "purge-after-days", "-1\n")
        with pytest.raises(AssertionError):
            read_days(tmp_path, "purge_after_days")


class DescribeBootStamp:
    def it_is_epoch_seconds_in_the_past(self):
        assert 0 < boot_stamp() <= time.time()


class DescribeExpandKeep:
    def it_substitutes_the_boot_stamp(self):
        assert expand_keep(["boot={boot}"]) == frozenset({f"boot={boot_stamp()}"})

    def it_leaves_a_plain_name_alone(self):
        assert expand_keep(["notes"]) == frozenset({"notes"})

    def it_does_not_read_a_boot_time_nobody_asked_for(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """A host without /proc/stat is configurable rather than unusable."""
        monkeypatch.setattr(config_module, "PROC_STAT", Path("/nonexistent"))
        assert expand_keep(["notes"]) == frozenset({"notes"})


class DescribeConfig:
    def it_refuses_an_empty_quarantine_dir(self):
        """Sweeping the quarantine into itself is not survivable."""
        with pytest.raises(AssertionError):
            Config(
                roots=(),
                prune=frozenset(),
                keep=frozenset(),
                trash_dir="trash",
                quarantine_dir="",
                quarantine_after_days=1,
                purge_after_days=1,
            )


class DescribeConfigNames:
    def it_refuses_a_quarantine_dir_that_is_a_path(self):
        """A name with a separator cannot be matched against an entry name."""
        with pytest.raises(AssertionError):
            replace(DEFAULTS, quarantine_dir="a/b")

    def it_refuses_a_trash_dir_that_is_a_path(self):
        with pytest.raises(AssertionError):
            replace(DEFAULTS, trash_dir="a/b")

    def it_refuses_a_relative_root(self):
        """A relative root resolves against whatever cwd the sweeper has."""
        with pytest.raises(AssertionError):
            replace(DEFAULTS, roots=(Path("tmp"),))


class DescribeLoadConfig:
    def it_refuses_a_directory_that_does_not_exist(self, tmp_path: Path):
        with pytest.raises(MissingSettings):
            load_config(tmp_path / "absent")

    def it_refuses_a_directory_with_one_setting_gone(self, tmp_path: Path):
        seed(tmp_path)
        (tmp_path / "purge-after-days").unlink()
        with pytest.raises(MissingSettings):
            load_config(tmp_path)

    def it_reads_what_the_installer_wrote(self, tmp_path: Path):
        loaded = load_config(seed(tmp_path))
        assert loaded.roots == (Path("~/tmp").expanduser(),)
        assert loaded.prune == frozenset(DEFAULT_PRUNE)
        assert loaded.trash_dir == DEFAULT_TRASH_DIR
        assert loaded.quarantine_dir == DEFAULT_QUARANTINE_DIR
        assert loaded.quarantine_after_days == DEFAULT_QUARANTINE_AFTER_DAYS
        assert loaded.purge_after_days == DEFAULT_PURGE_AFTER_DAYS

    def it_expands_a_tilde_in_a_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("HOME", "/home/someone")
        seed(tmp_path)
        write(tmp_path, "roots", "~/scratch\n")
        assert load_config(tmp_path).roots == (Path("/home/someone/scratch"),)

    def it_takes_every_setting_from_its_own_file(self, tmp_path: Path):
        for name, value in {
            "roots": "/srv/scratch",
            "prune": "target",
            "keep": "notes",
            "trash-dir": "junk",
            "quarantine-dir": "attic",
            "quarantine-after-days": "2",
            "purge-after-days": "3",
        }.items():
            write(tmp_path, name, value + "\n")
        assert load_config(tmp_path) == Config(
            roots=(Path("/srv/scratch"),),
            prune=frozenset({"target"}),
            keep=frozenset({"notes"}),
            trash_dir="junk",
            quarantine_dir="attic",
            quarantine_after_days=2,
            purge_after_days=3,
        )


class DescribeTheTemplates:
    def it_ships_one_per_setting(self):
        assert sorted(path.name for path in TEMPLATES.iterdir()) == sorted(
            setting_names()
        )

    def it_holds_the_default_the_code_declares(self):
        def values(name: str) -> list[str]:
            return parse_lines((TEMPLATES / name).read_text())

        assert values("roots") == list(DEFAULT_ROOTS)
        assert values("prune") == list(DEFAULT_PRUNE)
        assert values("keep") == list(DEFAULT_KEEP)
        assert values("trash-dir") == [DEFAULT_TRASH_DIR]
        assert values("quarantine-dir") == [DEFAULT_QUARANTINE_DIR]
        assert values("quarantine-after-days") == [str(DEFAULT_QUARANTINE_AFTER_DAYS)]
        assert values("purge-after-days") == [str(DEFAULT_PURGE_AFTER_DAYS)]
