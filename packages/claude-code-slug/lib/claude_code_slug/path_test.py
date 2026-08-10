"""What the doctests can't reach: behavior that needs a real filesystem.

Every case here is one the port could have gotten wrong silently, and each
wrong answer means a second store directory for a directory that already
had one.
"""

import os
from pathlib import Path

import pytest

from .path import logical_cwd, normalize, path_slug


@pytest.fixture
def linked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A directory entered through a symlink, as a shell would enter it."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    monkeypatch.chdir(real)
    monkeypatch.setenv("PWD", str(link))
    return link


class DescribeLogicalCwd:
    def it_keeps_the_symlink_the_shell_walked_through(self, linked: Path):
        assert logical_cwd() == str(linked)

    def it_falls_back_when_pwd_names_a_different_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """PWD is inherited, so a chdir since startup leaves it stale."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PWD", str(tmp_path.parent))
        assert logical_cwd() == os.getcwd()

    def it_falls_back_when_pwd_is_unset_or_relative(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PWD", raising=False)
        assert logical_cwd() == os.getcwd()
        monkeypatch.setenv("PWD", "relative/nonsense")
        assert logical_cwd() == os.getcwd()


class DescribeNormalize:
    def it_does_not_resolve_symlinks(self, linked: Path):
        """`realpath -L`, not `Path.resolve()` -- the store key follows the
        name the worktree was reached by, not the one it lives at."""
        assert normalize(".") == str(linked)

    def it_tolerates_paths_that_do_not_exist(self, linked: Path):
        """`realpath -m`: this runs before the directory gets created."""
        assert normalize("nope/../also-nope") == f"{linked}/also-nope"


class DescribeConsistency:
    def it_encodes_the_dot_and_the_bare_call_alike(self, linked: Path):
        """One directory, one key, however the caller spells it -- the bug
        that `--relative-to=.` used to hide in the bash version."""
        assert path_slug(".") == path_slug(str(linked)) == path_slug(os.environ["PWD"])
