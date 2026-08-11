"""Relocate a repository's `.git` into the central store, leaving a symlink.

Deciding *which* store a workdir gets is the half that must not be
ambiguous. A wrong encoder does not fail: it silently names a second
store for a repository that already has one, and the commits carry on
into a directory nobody looks in. `import claude_code_slug` binds to the
encoder installed beside this file; naming `claude-path` on a command
line binds to whatever the shell, editor or cron daemon last put on
PATH. So the store is computed here and handed to `relocate.sh`, which
drives git and stays bash for exactly that reason.

Usage: git-localhost-store [HOOK-NAME]
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .paths import repos_root, store_path

BASH = "/bin/bash"
RELOCATE = Path(__file__).parent / "relocate.sh"

# Hooks inherit our environment, and the recovery merge in relocate.sh writes
# refs straight into the store -- so a store still carrying its own
# pre-2026-07-13 reference-transaction hook re-enters this command from that
# nested git. One level down there is nothing left to do.
ACTIVE = "GIT_LOCALHOST_STORE_ACTIVE"


def read_toplevel() -> str:
    """The root of the worktree we were invoked in, as git reports it.

    git's own answer rather than a resolved cwd: hooks run with GIT_DIR
    set and cwd already at the top, and `--show-toplevel` is the spelling
    every store on disk was named from.
    """
    return subprocess.run(
        ("git", "rev-parse", "--show-toplevel"),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def main() -> int:
    if os.environ.get(ACTIVE):
        return 0

    hook_name = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        workdir = read_toplevel()
    except subprocess.CalledProcessError as error:
        return error.returncode  # git has already said why

    repos = repos_root()
    repos.mkdir(parents=True, exist_ok=True)
    repos.chmod(0o700)

    os.execve(
        BASH,
        [BASH, str(RELOCATE), workdir, str(store_path(repos, workdir)), hook_name],
        {**os.environ, ACTIVE: "1"},
    )
