"""Which directories are scratch, and therefore sweepable.

The convention is a `trash/` created and gitignored beside the work it serves,
plus the roots named in configuration. Directories merely *named* trash/ are
common in content that must survive: vendored packages ship one, and a
repository's own interior holds `refs/heads/trash/` for any branch under that
name. Git is the arbiter -- a scratch trash/ holds nothing git tracks.
"""

import os
from collections.abc import Container, Iterator, Sequence
from pathlib import Path
from subprocess import run

from .config import Config


def is_git_dir(path: Path) -> bool:
    """Whether `path` is a repository's interior, bare or otherwise.

    A directory that may not be read holds nothing this tool could sweep, so it
    answers False and the walk finds nothing inside it. Container image stores
    under $HOME are full of these.
    """
    try:
        return (
            (path / "HEAD").is_file()
            and (path / "objects").is_dir()
            and (path / "refs").is_dir()
        )
    except PermissionError:
        return False


def find_dirs_named(top: Path, name: str, prune: Container[str]) -> Iterator[Path]:
    """Every directory called `name` below `top`, not descending into one.

    A repository interior is never walked, listed in `prune` or not.
    """
    for dirpath, dirnames, _ in os.walk(top):
        here = Path(dirpath)
        dirnames[:] = [
            child
            for child in dirnames
            if child not in prune and not is_git_dir(here / child)
        ]
        if name in dirnames:
            dirnames.remove(name)
            yield here / name


def git_env() -> dict[str, str]:
    """Environment for a git subprocess, with no repository inherited.

    Hooks and wrappers export GIT_DIR, GIT_INDEX_FILE and friends. Inheriting
    them makes every query answer for the caller's repository instead of the
    path being asked about -- which here decides whether a directory is scratch
    or content.
    """
    return {name: v for name, v in os.environ.items() if not name.startswith("GIT_")}


def git_tracks_content(path: Path) -> bool:
    """Whether git knows of any tracked file under `path`.

    A path outside any work tree cannot be judged, so it counts as content:
    this errs toward leaving things alone.
    """
    proc = run(
        ["git", "-C", str(path), "ls-files", "--", "."],
        capture_output=True,
        text=True,
        env=git_env(),
    )
    return proc.returncode != 0 or bool(proc.stdout)


def scratch_roots(home: Path, config: Config) -> list[Path]:
    """Every sweepable root: the configured ones, plus scratch found below `home`."""
    if not config.trash_dir:
        return list(config.roots)
    else:
        return list(config.roots) + [
            found
            for found in find_dirs_named(home, config.trash_dir, config.prune)
            if not git_tracks_content(found)
        ]


__all__: Sequence[str] = (
    "find_dirs_named",
    "git_env",
    "git_tracks_content",
    "is_git_dir",
    "scratch_roots",
)
