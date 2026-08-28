"""Put this command's files where systemd and the user will find them.

A wheel lands in a venv; `systemctl --user` reads only its own search path, and
bukzor-tmpwatch refuses to run until every setting has a file. The units and the
annotated settings ship beside this module so they are version-controlled and
reviewable as a diff, and installation copies them out. Re-run after an upgrade
to pick up a setting that did not exist before.

Usage: bukzor-tmpwatch-install
"""

import shutil
from collections.abc import Sequence
from pathlib import Path
from subprocess import run

from .config import TEMPLATES, config_dir, setting_names, xdg_config_home

HERE = Path(__file__).parent
UNITS = ("bukzor-tmpwatch.service", "bukzor-tmpwatch.timer")


def unit_dir() -> Path:
    """Where `systemctl --user` reads units this user owns."""
    return xdg_config_home() / "systemd/user"


def proc_install(target: Path) -> list[Path]:
    """Copy every unit into `target`, returning what was written."""
    target.mkdir(parents=True, exist_ok=True)
    written = [target / name for name in UNITS]
    for name, dest in zip(UNITS, written):
        shutil.copyfile(HERE / name, dest)
    return written


def proc_write_settings(target: Path) -> list[Path]:
    """Copy each missing setting template into `target`, returning what was written.

    A file already there is the user's answer and is never overwritten, so this
    is safe to re-run: it only ever fills in settings that have no file yet.
    """
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in setting_names():
        dest = target / name
        if not dest.exists():
            shutil.copyfile(TEMPLATES / name, dest)
            written.append(dest)
    return written


def main() -> int:
    written = proc_install(unit_dir()) + proc_write_settings(config_dir())
    run(["systemctl", "--user", "daemon-reload"], check=True)
    for path in written:
        print(path)
    print("enable with: systemctl --user enable --now bukzor-tmpwatch.timer")
    return 0


__all__: Sequence[str] = (
    "UNITS",
    "proc_install",
    "proc_write_settings",
    "unit_dir",
)
