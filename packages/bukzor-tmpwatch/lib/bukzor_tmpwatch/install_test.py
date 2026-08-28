from pathlib import Path

import pytest

from .install import UNITS, proc_install, unit_dir


class DescribeUnitDir:
    def it_honors_xdg_config_home(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert unit_dir() == tmp_path / "systemd/user"

    def it_falls_back_to_dot_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        assert unit_dir() == tmp_path / ".config/systemd/user"


class DescribeProcInstall:
    def it_writes_every_unit(self, tmp_path: Path):
        assert proc_install(tmp_path) == [tmp_path / name for name in UNITS]
        for name in UNITS:
            assert (tmp_path / name).read_text().startswith("[Unit]")

    def it_creates_a_missing_target(self, tmp_path: Path):
        target = tmp_path / "config/systemd/user"
        proc_install(target)
        assert (target / UNITS[0]).is_file()

    def it_replaces_an_older_copy(self, tmp_path: Path):
        stale = tmp_path / UNITS[0]
        stale.write_text("[Unit]\nDescription=stale\n")
        proc_install(tmp_path)
        assert "stale" not in stale.read_text()
