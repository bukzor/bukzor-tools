"""The two things this system promises, driven through real git.

Nothing here stubs git or the hooks: the failures worth catching all
live in the seams -- which hook fires when, what `git init` copies out
of a template, whether the store a hook computes is the store the
relocator adopts. Every path is redirected into `tmp_path`, because a
test that reached the real store would be editing the repositories this
tool exists to protect.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest
from claude_code_slug import path_slug

BIN = Path(sys.executable).parent
RELOCATE = BIN / "git-localhost-store"
INSTALL = BIN / "git-localhost-store-install"

Env = Mapping[str, str]


def run(*command: str | Path, env: Env, cwd: Path | None = None) -> str:
    return subprocess.run(
        command, env=env, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE
    ).stdout.strip()


@pytest.fixture
def env(tmp_path: Path) -> Env:
    """A home of our own: no XDG path, and no git config, is the real one.

    `GIT_*` is dropped rather than inherited. Anything that runs these
    tests from inside a git operation -- `pre-commit`, most obviously --
    exports `GIT_INDEX_FILE` and `GIT_DIR` for *its* repository, and
    those beat `-C` in every git call below. `GIT_LOCALHOST_STORE_ACTIVE`
    is in the same family, and would turn the relocator into a no-op.
    """
    home = tmp_path / "home"
    home.mkdir()
    return {
        **{name: value for name, value in os.environ.items() if name[:4] != "GIT_"},
        "HOME": str(home),
        "XDG_STATE_HOME": str(home / ".local/state"),
        "XDG_DATA_HOME": str(home / ".local/share"),
        "GIT_CONFIG_GLOBAL": str(home / ".gitconfig"),
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }


@pytest.fixture
def template(env: Env) -> Path:
    """The installed template directory -- the installer's whole output."""
    run(INSTALL, env=env)
    return Path(env["XDG_DATA_HOME"]) / "git-localhost-store/template-repo"


def store_of(workdir: Path, env: Env) -> Path:
    return (
        Path(env["XDG_STATE_HOME"])
        / "git-localhost-store/repos"
        / path_slug(run("git", "-C", workdir, "rev-parse", "--show-toplevel", env=env))
    )


def commit(workdir: Path, env: Env, message: str) -> None:
    (workdir / "file.txt").write_text(message)
    run("git", "-C", workdir, "add", "file.txt", env=env)
    run("git", "-C", workdir, "commit", "-m", message, env=env)


@pytest.fixture
def relocated(tmp_path: Path, template: Path, env: Env) -> Path:
    """A repo that has relocated itself, by hook, on its first commit."""
    workdir = tmp_path / "repo"
    workdir.mkdir()
    run("git", "-C", workdir, "init", f"--template={template}", env=env)
    commit(workdir, env, "first")
    return workdir


class DescribeInstall:
    def it_aims_the_public_path_at_this_venv(self, template: Path, env: Env):
        """Every hook ever copied addresses this one path, not a venv."""
        link = (
            Path(env["XDG_DATA_HOME"]) / "git-localhost-store/bin/git-localhost-store"
        )
        assert link.readlink() == RELOCATE

    def it_leaves_a_foreign_template_dir_alone(self, template: Path, env: Env):
        run("git", "config", "--global", "init.templateDir", "/elsewhere", env=env)
        run(INSTALL, env=env)
        assert (
            run("git", "config", "--global", "init.templateDir", env=env)
            == "/elsewhere"
        )


class DescribeRelocation:
    def it_moves_git_into_the_store_on_first_commit(self, relocated: Path, env: Env):
        store = store_of(relocated, env)
        assert (relocated / ".git").readlink() == store
        assert (store / "HEAD").is_file()

    def it_leaves_an_already_relocated_repo_alone(self, relocated: Path, env: Env):
        commit(relocated, env, "second")
        assert (relocated / ".git").readlink() == store_of(relocated, env)
        assert (
            run("git", "-C", relocated, "log", "--format=%s", env=env)
            == "second\nfirst"
        )


class DescribeRecovery:
    def it_adopts_the_surviving_store_and_restores_the_files(
        self, relocated: Path, env: Env
    ):
        """The whole point: `rm -rf` of a workdir loses nothing committed."""
        store = store_of(relocated, env)
        shutil.rmtree(relocated)
        relocated.mkdir()
        run("git", "-C", relocated, "init", env=env)
        run(RELOCATE, env=env, cwd=relocated)

        assert (relocated / ".git").readlink() == store
        assert run("git", "-C", relocated, "log", "--format=%s", env=env) == "first"
        assert (relocated / "file.txt").read_text() == "first"
