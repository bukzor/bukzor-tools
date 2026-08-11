"""Every path this system owns, and the rule that names a store.

The split between the two roots is the XDG one, and it is load-bearing:
a store *is* a repository, so it is state and never regenerated, while
the template directory and the public `bin/` are data -- rewritten from
the wheel by `git-localhost-store-install` whenever it runs.
"""

from __future__ import annotations

import os
from pathlib import Path

from claude_code_slug import path_slug


def xdg(variable: str, fallback: str) -> Path:
    """An XDG base directory, by its spec-defined default."""
    return Path(os.environ.get(variable) or Path.home() / fallback)


def repos_root() -> Path:
    """Holds one directory per workdir that has ever been relocated."""
    return xdg("XDG_STATE_HOME", ".local/state") / "git-localhost-store/repos"


def share_root() -> Path:
    """The stable public path -- what every hook copy ever made addresses."""
    return xdg("XDG_DATA_HOME", ".local/share") / "git-localhost-store"


def template_dir() -> Path:
    """What `git config --global init.templateDir` is pointed at."""
    return share_root() / "template-repo"


def relocator_link() -> Path:
    """The public name of the relocator, a symlink into the current venv."""
    return share_root() / "bin/git-localhost-store"


def store_path(repos: Path, workdir: str) -> Path:
    """The store directory belonging to `workdir`.

    >>> store_path(Path("/state/repos"), "/home/you/src")
    PosixPath('/state/repos/-home-you-src')

    The encoding is frozen and is not collision-free: `-` is the image of
    `/`, of `.`, and of itself, so two workdirs can name one store. That
    is tolerated rather than fixed, because a store is *named* by this
    function -- changing it orphans stores instead of renaming them.
    """
    return repos / path_slug(workdir)
