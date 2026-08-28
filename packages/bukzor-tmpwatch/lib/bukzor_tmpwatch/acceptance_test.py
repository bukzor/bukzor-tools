"""End-to-end checks against the installed console scripts.

These drive the real entry points as subprocesses, so they cover the wiring a
unit test cannot see: argv parsing, settings read from disk, the console
scripts existing at all, and the packaged files surviving the build.

Every run is given its own XDG_CONFIG_HOME, so these never consult -- or are
steered by -- the settings of whoever is running the tests.
"""

import os
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path
from subprocess import CompletedProcess, run

import pytest

from .config import APP, setting_names
from .install import proc_write_settings

BIN = Path(sys.executable).parent
COMMAND = BIN / "bukzor-tmpwatch"
INSTALLER = BIN / "bukzor-tmpwatch-install"
PACKAGE = Path(__file__).parent
REPO = PACKAGE.parents[3]
DAY = 24 * 60 * 60
OLD = 1_000_000_000.0


def has_user_systemd() -> bool:
    """Whether `systemctl --user` can reach a session bus."""
    if not shutil.which("systemctl"):
        return False
    probe = run(
        ["systemctl", "--user", "show", "--property=Version"], capture_output=True
    )
    return probe.returncode == 0


def isolated(home: Path) -> dict[str, str]:
    """Environment whose settings live under `home`, wherever the tester's are."""
    return dict(os.environ) | {"XDG_CONFIG_HOME": str(home / "config")}


def settings_dir(home: Path) -> Path:
    """The settings directory of an isolated run, holding every default."""
    path = home / "config" / APP
    proc_write_settings(path)
    return path


def tmpwatch(home: Path, *args: str) -> CompletedProcess[str]:
    settings_dir(home)
    return run(
        [str(COMMAND), *args], capture_output=True, text=True, env=isolated(home)
    )


def tmpwatch_unconfigured(home: Path, *args: str) -> CompletedProcess[str]:
    """Run without seeding, to see what an unconfigured machine is told."""
    return run(
        [str(COMMAND), *args], capture_output=True, text=True, env=isolated(home)
    )


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
        scratch = tmp_path / "scratch"
        stale_file(scratch, "stale.txt", days=60)
        done = tmpwatch(tmp_path, str(scratch))
        assert done.returncode == 0, done.stderr
        assert "would quarantine" in done.stdout
        assert (scratch / "stale.txt").exists()

    def it_states_the_action_and_root_once_for_the_whole_list(self, tmp_path: Path):
        """The report is grouped, not one self-repeating line per entry."""
        scratch = tmp_path / "scratch"
        stale_file(scratch, "README.md", days=60)
        stale_file(scratch, "notes.txt", days=60)
        assert tmpwatch(tmp_path, str(scratch)).stdout == (
            f"# would quarantine, to lost-and-found/{date.today().isoformat()}/\n"
            f"{scratch}/\n"
            "  README.md\n"
            "  notes.txt\n"
        )

    def it_tolerates_a_reader_that_stops_early(self, tmp_path: Path):
        """`bukzor-tmpwatch | head` must not spray a traceback."""
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        # Enough output to overflow the stdout buffer, so the write fails while
        # head(1) is demonstrably gone, not merely at interpreter shutdown.
        for index in range(500):
            entry = scratch / f"entry-{index:04d}-named-long-enough-to-fill-it"
            entry.write_text("")
            os.utime(entry, (OLD, OLD))
        os.utime(scratch, (OLD, OLD))
        settings_dir(tmp_path)
        done = run(
            f"'{COMMAND}' '{scratch}' | head -2",
            shell=True,
            capture_output=True,
            text=True,
            env=isolated(tmp_path),
        )
        assert done.stderr == ""

    def it_says_on_stderr_how_to_apply(self, tmp_path: Path):
        scratch = tmp_path / "scratch"
        stale_file(scratch, "stale.txt", days=60)
        assert "--write to apply" in tmpwatch(tmp_path, str(scratch)).stderr

    def it_stays_quiet_when_there_is_nothing_to_do(self, tmp_path: Path):
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        done = tmpwatch(tmp_path, str(scratch))
        assert (done.stdout, done.stderr) == ("", "")

    def it_refuses_to_guess_when_there_are_no_settings(self, tmp_path: Path):
        """Silently defaulting would delete by a rule nobody chose."""
        done = tmpwatch_unconfigured(tmp_path, str(tmp_path))
        assert done.returncode == 2, done
        assert "bukzor-tmpwatch-install" in done.stderr
        assert "quarantine-after-days" in done.stderr

    def it_names_only_the_setting_that_is_gone(self, tmp_path: Path):
        (settings_dir(tmp_path) / "keep").unlink()
        done = tmpwatch_unconfigured(tmp_path, str(tmp_path))
        assert done.returncode == 2, done
        assert "roots" not in done.stderr
        assert done.stderr.count("no such setting") == 1

    def it_refuses_the_flag_that_used_to_mean_dry_run(self, tmp_path: Path):
        done = tmpwatch(tmp_path, "-n", str(tmp_path))
        assert done.returncode != 0
        assert "unrecognized arguments: -n" in done.stderr


class WhenConfigured:
    def it_waits_the_number_of_days_a_setting_file_gives(self, tmp_path: Path):
        """Nothing else in this test would quarantine a three-day-old file."""
        (settings_dir(tmp_path) / "quarantine-after-days").write_text("2\n")
        scratch = tmp_path / "scratch"
        stale_file(scratch, "stale.txt", days=3)
        assert "would quarantine" in tmpwatch(tmp_path, str(scratch)).stdout

    def it_exempts_a_name_a_setting_file_keeps(self, tmp_path: Path):
        settings = settings_dir(tmp_path)
        (settings / "quarantine-after-days").write_text("2\n")
        (settings / "keep").write_text("# mine\nstale.txt\n")
        scratch = tmp_path / "scratch"
        stale_file(scratch, "stale.txt", days=3)
        assert tmpwatch(tmp_path, str(scratch)).stdout == ""

    def it_parks_swept_entries_where_a_setting_file_says(self, tmp_path: Path):
        (settings_dir(tmp_path) / "quarantine-dir").write_text("attic\n")
        scratch = tmp_path / "scratch"
        stale_file(scratch, "stale.txt", days=60)
        done = tmpwatch(tmp_path, "--write", str(scratch))
        assert (done.returncode, done.stderr) == (0, "")
        assert (scratch / "attic" / date.today().isoformat() / "stale.txt").is_file()

    def it_lets_a_flag_override_a_setting_file(self, tmp_path: Path):
        (settings_dir(tmp_path) / "quarantine-after-days").write_text("90\n")
        scratch = tmp_path / "scratch"
        stale_file(scratch, "stale.txt", days=60)
        assert tmpwatch(tmp_path, str(scratch)).stdout == ""
        assert (
            "would quarantine"
            in tmpwatch(tmp_path, "--quarantine-after", "30", str(scratch)).stdout
        )


class WhenWriting:
    def it_quarantines_into_a_batch_named_for_today(self, tmp_path: Path):
        scratch = tmp_path / "scratch"
        stale_file(scratch, "stale.txt", days=60)
        done = tmpwatch(tmp_path, "--write", str(scratch))
        assert (done.returncode, done.stderr) == (0, "")
        batch = scratch / "lost-and-found" / date.today().isoformat()
        assert (batch / "stale.txt").is_file()
        assert not (scratch / "stale.txt").exists()

    def it_leaves_an_entry_whose_contents_are_fresh(self, tmp_path: Path):
        scratch = tmp_path / "scratch"
        stale_file(scratch, "project/deep/old.txt", days=60)
        (scratch / "project/deep/new.txt").write_text("x")
        # Only the walk can see this: the entry's own mtime stays old, because
        # writing inside project/deep/ does not touch project/.
        os.utime(scratch / "project", (0, 0))
        tmpwatch(tmp_path, "--write", str(scratch))
        assert (scratch / "project/deep/old.txt").is_file()

    def it_never_sweeps_a_symlink(self, tmp_path: Path):
        scratch = tmp_path / "scratch"
        stale_file(scratch, "elsewhere/old.txt", days=60)
        link = scratch / "link"
        link.symlink_to(scratch / "elsewhere")
        os.utime(link, (0, 0), follow_symlinks=False)
        tmpwatch(tmp_path, "--write", str(scratch))
        assert link.is_symlink()

    def it_purges_a_batch_once_its_datestamp_is_old_enough(self, tmp_path: Path):
        doomed = tmp_path / "scratch/lost-and-found/2020-01-01"
        doomed.mkdir(parents=True)
        (doomed / "forgotten.txt").write_text("x")
        done = tmpwatch(
            tmp_path, "--write", "--purge-after", "1", str(tmp_path / "scratch")
        )
        assert "purged" in done.stdout, done.stdout
        assert not doomed.exists()

    def it_keeps_a_batch_that_is_still_young(self, tmp_path: Path):
        recent = tmp_path / "scratch/lost-and-found" / date.today().isoformat()
        recent.mkdir(parents=True)
        (recent / "kept.txt").write_text("x")
        tmpwatch(tmp_path, "--write", "--purge-after", "1", str(tmp_path / "scratch"))
        assert (recent / "kept.txt").is_file()


@pytest.mark.skipif(not has_user_systemd(), reason="no systemd user session")
class DescribeTheInstaller:
    def it_writes_both_units_where_systemd_reads_them(self, tmp_path: Path):
        done = run(
            [str(INSTALLER)], capture_output=True, text=True, env=isolated(tmp_path)
        )
        assert done.returncode == 0, done.stderr
        installed = tmp_path / "config/systemd/user"
        for name in ("bukzor-tmpwatch.service", "bukzor-tmpwatch.timer"):
            assert (installed / name).read_bytes() == (PACKAGE / name).read_bytes()

    def it_seeds_every_setting_where_the_command_will_look(self, tmp_path: Path):
        run([str(INSTALLER)], capture_output=True, check=True, env=isolated(tmp_path))
        seeded = tmp_path / "config" / APP
        assert sorted(path.name for path in seeded.iterdir()) == sorted(setting_names())

    def it_leaves_a_seeded_file_alone_on_reinstall(self, tmp_path: Path):
        mine = settings_dir(tmp_path) / "purge-after-days"
        mine.write_text("90\n")
        run([str(INSTALLER)], capture_output=True, check=True, env=isolated(tmp_path))
        assert mine.read_text() == "90\n"

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

    def it_ships_every_setting_template(self, wheel: zipfile.ZipFile):
        shipped = set(wheel.namelist())
        for name in setting_names():
            assert f"bukzor_tmpwatch/config.d/{name}" in shipped

    def it_omits_the_tests(self, wheel: zipfile.ZipFile):
        assert [name for name in wheel.namelist() if name.endswith("_test.py")] == []
