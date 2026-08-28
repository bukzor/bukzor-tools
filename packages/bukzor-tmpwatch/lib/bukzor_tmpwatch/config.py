"""Settings, one plain-text file per setting, under $XDG_CONFIG_HOME/bukzor-tmpwatch/.

Every file is read the same way: `#` starts a comment, surrounding whitespace
goes, blank lines vanish, and what remains is one value per line. A value
therefore cannot contain `#`.

Each file is named for its setting, so `ls` on the directory is the reference.
A file that is absent means the built-in default; a file emptied of values
means the empty value, which is how a setting is switched off.
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
DEFAULT_PURGE_AFTER_DAYS = 15


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


def setting_names() -> tuple[str, ...]:
    """Every configurable file name."""
    return tuple(field.name.replace("_", "-") for field in fields(Config))


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


def read_values(directory: Path, setting: str, default: Sequence[str]) -> list[str]:
    """The values configured for `setting`, or `default` if it has no file."""
    path = directory / setting.replace("_", "-")
    if path.is_file():
        return parse_lines(path.read_text())
    else:
        return list(default)


def read_value(directory: Path, setting: str, default: str) -> str:
    """The single value configured for `setting`, empty if its file is."""
    values = read_values(directory, setting, (default,))
    assert len(values) <= 1, (setting, values)
    return values[0] if values else ""


def read_days(directory: Path, setting: str, default: int) -> int:
    """A whole number of days configured for `setting`."""
    value = read_value(directory, setting, str(default))
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
    """Every setting, taken from `directory` and defaulted where absent."""
    return Config(
        roots=tuple(
            Path(value).expanduser()
            for value in read_values(directory, "roots", DEFAULT_ROOTS)
        ),
        prune=frozenset(read_values(directory, "prune", DEFAULT_PRUNE)),
        keep=expand_keep(read_values(directory, "keep", DEFAULT_KEEP)),
        trash_dir=read_value(directory, "trash_dir", DEFAULT_TRASH_DIR),
        quarantine_dir=read_value(directory, "quarantine_dir", DEFAULT_QUARANTINE_DIR),
        quarantine_after_days=read_days(
            directory, "quarantine_after_days", DEFAULT_QUARANTINE_AFTER_DAYS
        ),
        purge_after_days=read_days(
            directory, "purge_after_days", DEFAULT_PURGE_AFTER_DAYS
        ),
    )


__all__: Sequence[str] = (
    "APP",
    "BOOT",
    "TEMPLATES",
    "Config",
    "boot_stamp",
    "config_dir",
    "expand_keep",
    "load_config",
    "parse_lines",
    "read_days",
    "read_value",
    "read_values",
    "setting_names",
    "xdg_config_home",
)
