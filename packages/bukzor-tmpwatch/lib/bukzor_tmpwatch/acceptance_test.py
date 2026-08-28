"""End-to-end checks against the installed console scripts.

These drive the real entry points as subprocesses, so they cover the wiring a
unit test cannot see: argv parsing, the console scripts existing at all, and
the packaged systemd units surviving the build.
"""

import os
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path
from subprocess import CompletedProcess, run

import pytest

BIN = Path(sys.executable).parent
COMMAND = BIN / "bukzor-tmpwatch"
INSTALLER = BIN / "bukzor-tmpwatch-install"
PACKAGE = Path(__file__).parent
REPO = PACKAGE.parents[3]
DAY = 24 * 60 * 60


def has_user_systemd() -> bool:
    """Whether `systemctl --user` can reach a session bus."""
    if not shutil.which("systemctl"):
        return False
    probe = run(
        ["systemctl", "--user", "show", "--property=Version"], capture_output=True
    )
    return probe.returncode == 0


def tmpwatch(*args: str) -> CompletedProcess[str]:
    return run([str(COMMAND), *args], capture_output=True, text=True)


def stale_file(root: Path, name: str, days: int) -> Path:
    """A file under `root` whose whole path looks untouched for `days`."""
    leaf = root / name
    leaf.parent.mkdir(parents=True, exist_ok=True)
    leaf.write_text("x")
    when = os.stat(leaf).st_mtime - days * DAY
    for path in (leaf, *leaf.parents):
        os.utime(path, (when, when))
        if path == root:
            break
    return leaf


class DescribeTheCommand:
    def it_is_installed(self):
        assert COMMAND.is_file(), COMMAND

    def it_reports_without_writing_by_default(self, tmp_path: Path):
        stale_file(tmp_path, "stale.txt", days=60)
        done = tmpwatch(str(tmp_path))
        assert done.returncode == 0, done.stderr
        assert "would quarantine" in done.stdout
        assert (tmp_path / "stale.txt").exists()

    def it_says_on_stderr_how_to_apply(self, tmp_path: Path):
        stale_file(tmp_path, "stale.txt", days=60)
        assert "--write to apply" in tmpwatch(str(tmp_path)).stderr

    def it_stays_quiet_when_there_is_nothing_to_do(self, tmp_path: Path):
        done = tmpwatch(str(tmp_path))
        assert (done.stdout, done.stderr) == ("", "")

    def it_refuses_the_flag_that_used_to_mean_dry_run(self, tmp_path: Path):
        done = tmpwatch("-n", str(tmp_path))
        assert done.returncode != 0
        assert "unrecognized arguments: -n" in done.stderr


class WhenWriting:
    def it_quarantines_into_a_batch_named_for_today(self, tmp_path: Path):
        stale_file(tmp_path, "stale.txt", days=60)
        done = tmpwatch("--write", str(tmp_path))
        assert (done.returncode, done.stderr) == (0, "")
        batch = tmp_path / "lost-and-found" / date.today().isoformat()
        assert (batch / "stale.txt").is_file()
        assert not (tmp_path / "stale.txt").exists()

    def it_leaves_an_entry_whose_contents_are_fresh(self, tmp_path: Path):
        stale_file(tmp_path, "project/deep/old.txt", days=60)
        (tmp_path / "project/deep/new.txt").write_text("x")
        # Only the walk can see this: the entry's own mtime stays old, because
        # writing inside project/deep/ does not touch project/.
        os.utime(tmp_path / "project", (0, 0))
        tmpwatch("--write", str(tmp_path))
        assert (tmp_path / "project/deep/old.txt").is_file()

    def it_never_sweeps_a_symlink(self, tmp_path: Path):
        stale_file(tmp_path, "elsewhere/old.txt", days=60)
        link = tmp_path / "link"
        link.symlink_to(tmp_path / "elsewhere")
        os.utime(link, (0, 0), follow_symlinks=False)
        tmpwatch("--write", str(tmp_path))
        assert link.is_symlink()

    def it_purges_a_batch_once_its_datestamp_is_old_enough(self, tmp_path: Path):
        doomed = tmp_path / "lost-and-found/2020-01-01"
        doomed.mkdir(parents=True)
        (doomed / "forgotten.txt").write_text("x")
        done = tmpwatch("--write", "--purge-after", "1", str(tmp_path))
        assert "purged" in done.stdout, done.stdout
        assert not doomed.exists()

    def it_keeps_a_batch_that_is_still_young(self, tmp_path: Path):
        recent = tmp_path / "lost-and-found" / date.today().isoformat()
        recent.mkdir(parents=True)
        (recent / "kept.txt").write_text("x")
        tmpwatch("--write", "--purge-after", "1", str(tmp_path))
        assert (recent / "kept.txt").is_file()


@pytest.mark.skipif(not has_user_systemd(), reason="no systemd user session")
class DescribeTheInstaller:
    def it_writes_both_units_where_systemd_reads_them(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        done = run(
            [str(INSTALLER)], capture_output=True, text=True, env=dict(os.environ)
        )
        assert done.returncode == 0, done.stderr
        installed = tmp_path / "systemd/user"
        for name in ("bukzor-tmpwatch.service", "bukzor-tmpwatch.timer"):
            assert (installed / name).read_bytes() == (PACKAGE / name).read_bytes()

    def it_installs_a_unit_that_asks_for_the_write(self):
        service = (PACKAGE / "bukzor-tmpwatch.service").read_text()
        assert "bukzor-tmpwatch --write" in service


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> zipfile.ZipFile:
    out = tmp_path_factory.mktemp("dist")
    run(
        ["uv", "build", "--package", "bukzor-tmpwatch", "--out-dir", str(out)],
        cwd=REPO,
        capture_output=True,
        check=True,
    )
    (built,) = out.glob("*.whl")
    return zipfile.ZipFile(built)


@pytest.mark.skipif(not shutil.which("uv"), reason="uv builds the wheel")
class DescribeTheWheel:
    def it_ships_the_systemd_units(self, wheel: zipfile.ZipFile):
        shipped = set(wheel.namelist())
        assert "bukzor_tmpwatch/bukzor-tmpwatch.service" in shipped
        assert "bukzor_tmpwatch/bukzor-tmpwatch.timer" in shipped

    def it_omits_the_tests(self, wheel: zipfile.ZipFile):
        assert [name for name in wheel.namelist() if name.endswith("_test.py")] == []
