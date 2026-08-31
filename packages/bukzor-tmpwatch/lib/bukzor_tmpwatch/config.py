"""Settings, one plain-text file per setting, under $XDG_CONFIG_HOME/bukzor-tmpwatch/.

Every file is read the same way: `#` starts a comment, surrounding whitespace
goes, blank lines vanish, and what remains is one value per line. A value
therefore cannot contain `#`.

Each file is named for its setting, so `ls` on the directory is the reference
and `cat` is the documentation. Every setting must have a file: a tool that
deletes things should not be guessing at what its owner meant, so a missing
file is an error naming the installer that writes it, not a silent default.
A file emptied of values means the empty value, which is how a setting is
switched off.
"""

import os
from collections.abc import Sequence
from dataclasses import dataclass, fields
from pathlib import Path

APP = "bukzor-tmpwatch"
BOOT = "{boot}"
PROC_STAT = Path("/proc/stat")
TEMPLATES = Path(__file__).parent / "config.d"

DEFAULT_ROOTS = ("~/tmp",)
DEFAULT_PRUNE = (
    ".git",
    ".cache",
    ".npm",
    ".rustup",
    ".venv",
    "node_modules",
    "target",
)
DEFAULT_KEEP = (f"boot={BOOT}",)
DEFAULT_TRASH_DIR = "trash"
DEFAULT_QUARANTINE_DIR = "lost-and-found"
DEFAULT_QUARANTINE_AFTER_DAYS = 15
DEFAULT_PURGE_AFTER_DAYS = 30


class MissingSettings(Exception):
    """Setting files that must exist do not. Carries the list of paths."""


@dataclass(frozen=True)
class Config:
    """Everything about a sweep that a user may decide."""

    roots: tuple[Path, ...]
    prune: frozenset[str]
    keep: frozenset[str]
    trash_dir: str
    quarantine_dir: str
    quarantine_after_days: int
    purge_after_days: int

    def __post_init__(self) -> None:
        # An empty name would put the quarantine at the root itself, and the
        # first sweep would try to rename the root into its own subdirectory.
        assert self.quarantine_dir, self
        # Both are matched against a single directory name, so anything with a
        # separator in it -- or `..` -- can never match, and would silently
        # exempt nothing while looking like it exempts something.
        assert Path(self.quarantine_dir).name == self.quarantine_dir, self
        assert not self.trash_dir or Path(self.trash_dir).name == self.trash_dir, self
        # A relative root resolves against whatever working directory the
        # sweeper happens to have, which for a systemd unit is not yours.
        assert all(root.is_absolute() for root in self.roots), self


def setting_names() -> tuple[str, ...]:
    """Every configurable file name."""
    return tuple(field.name.replace("_", "-") for field in fields(Config))


def missing_settings(directory: Path) -> list[Path]:
    """Every setting file that belongs in `directory` and is not there."""
    return [
        directory / name for name in setting_names() if not (directory / name).is_file()
    ]


def parse_lines(text: str) -> list[str]:
    """The values in a config file's text."""
    return [
        value for line in text.splitlines() if (value := line.split("#", 1)[0].strip())
    ]


def xdg_config_home() -> Path:
    """The base directory holding this user's configuration."""
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def config_dir() -> Path:
    """The directory holding this command's setting files."""
    return xdg_config_home() / APP


def read_values(directory: Path, setting: str) -> list[str]:
    """The values configured for `setting`."""
    path = directory / setting.replace("_", "-")
    if not path.is_file():
        raise MissingSettings([path])
    return parse_lines(path.read_text())


def read_value(directory: Path, setting: str) -> str:
    """The single value configured for `setting`, empty if its file is."""
    values = read_values(directory, setting)
    assert len(values) <= 1, (setting, values)
    return values[0] if values else ""


def read_days(directory: Path, setting: str) -> int:
    """A whole number of days configured for `setting`."""
    value = read_value(directory, setting)
    assert value.isdigit(), (setting, value)
    return int(value)


def boot_stamp() -> int:
    """Epoch seconds at which this kernel booted."""
    for line in PROC_STAT.read_text().splitlines():
        field, _, value = line.partition(" ")
        if field == "btime":
            return int(value)
    raise AssertionError(PROC_STAT)


def expand_keep(names: Sequence[str]) -> frozenset[str]:
    """`names` with {boot} replaced by this kernel's boot time.

    The stamp is read only when a name asks for it, so a host with no
    /proc/stat is merely unable to use that one substitution.
    """
    if not any(BOOT in name for name in names):
        return frozenset(names)
    else:
        stamp = str(boot_stamp())
        return frozenset(name.replace(BOOT, stamp) for name in names)


def load_config(directory: Path) -> Config:
    """Every setting, read from `directory`, which must hold all of them."""
    missing = missing_settings(directory)
    if missing:
        raise MissingSettings(missing)
    return Config(
        roots=tuple(
            Path(value).expanduser() for value in read_values(directory, "roots")
        ),
        prune=frozenset(read_values(directory, "prune")),
        keep=expand_keep(read_values(directory, "keep")),
        trash_dir=read_value(directory, "trash_dir"),
        quarantine_dir=read_value(directory, "quarantine_dir"),
        quarantine_after_days=read_days(directory, "quarantine_after_days"),
        purge_after_days=read_days(directory, "purge_after_days"),
    )


__all__: Sequence[str] = (
    "APP",
    "BOOT",
    "TEMPLATES",
    "Config",
    "MissingSettings",
    "boot_stamp",
    "config_dir",
    "expand_keep",
    "load_config",
    "missing_settings",
    "parse_lines",
    "read_days",
    "read_value",
    "read_values",
    "setting_names",
    "xdg_config_home",
)
