"""Put this command's files where systemd and the user will find them.

A wheel lands in a venv; `systemctl --user` reads only its own search path, and
bukzor-tmpwatch refuses to run until every setting has a file. The units and the
annotated settings ship beside this module so they are version-controlled and
reviewable as a diff, and installation puts them where they are read.

Units are linked, settings are copied, and the difference is deliberate: a unit
is ours and should never go stale against the package, while a settings file
becomes yours the moment you edit it. Re-run after an upgrade to pick up a
setting that did not exist before.

Usage: bukzor-tmpwatch-install
"""

import shutil
from pathlib import Path
from subprocess import run

from .config import TEMPLATES, config_dir, setting_names, xdg_config_home

HERE = Path(__file__).parent
UNITS = ("bukzor-tmpwatch.service", "bukzor-tmpwatch.timer")


def unit_dir() -> Path:
    """Where `systemctl --user` reads units this user owns."""
    return xdg_config_home() / "systemd/user"


def proc_install(target: Path) -> list[Path]:
    """Link every unit into `target`, returning what was written.

    A link, not a copy: the package is installed editable, so an edited unit is
    live after `systemctl --user daemon-reload` rather than waiting for someone
    to remember to reinstall. This is also what `systemctl enable` does to a
    unit that lives outside the search path.
    """
    target.mkdir(parents=True, exist_ok=True)
    written = [target / name for name in UNITS]
    for name, dest in zip(UNITS, written):
        if dest.is_symlink() or dest.exists():
            dest.unlink()
        dest.symlink_to(HERE / name)
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
