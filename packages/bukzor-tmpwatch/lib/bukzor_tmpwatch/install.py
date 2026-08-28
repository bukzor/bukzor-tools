"""Put the systemd units where systemd looks for them.

A wheel lands in a venv; `systemctl --user` reads only its own search path. The
units ship beside this module so they are version-controlled and reviewable as a
diff, and installation copies them out. Re-run after an upgrade.

Usage: bukzor-tmpwatch-install
"""

import os
import shutil
from collections.abc import Sequence
from pathlib import Path
from subprocess import run

HERE = Path(__file__).parent
UNITS = ("bukzor-tmpwatch.service", "bukzor-tmpwatch.timer")


def unit_dir() -> Path:
    """Where `systemctl --user` reads units this user owns."""
    config = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(config) / "systemd/user"


def proc_install(target: Path) -> list[Path]:
    """Copy every unit into `target`, returning what was written."""
    target.mkdir(parents=True, exist_ok=True)
    written = [target / name for name in UNITS]
    for name, dest in zip(UNITS, written):
        shutil.copyfile(HERE / name, dest)
    return written


def main() -> int:
    written = proc_install(unit_dir())
    run(["systemctl", "--user", "daemon-reload"], check=True)
    for path in written:
        print(path)
    print("enable with: systemctl --user enable --now bukzor-tmpwatch.timer")
    return 0


__all__: Sequence[str] = ("UNITS", "proc_install", "unit_dir")
