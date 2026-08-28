"""Which directories are scratch, and therefore sweepable.

The convention is a `trash/` created and gitignored beside the work it serves,
plus `~/tmp`. Directories merely *named* trash/ are common in content that must
survive: vendored packages ship one, and a repository's own interior holds
`refs/heads/trash/` for any branch under that name. Git is the arbiter -- a
scratch trash/ holds nothing git tracks.
"""

import os
from collections.abc import Iterator, Sequence
from pathlib import Path
from subprocess import run

TRASH = "trash"

# Skipped for speed, except .git: a repository interior must never be walked.
PRUNE = frozenset(
    {".git", ".cache", ".npm", ".rustup", ".venv", "node_modules", "target"}
)


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


def find_trash_dirs(top: Path) -> Iterator[Path]:
    """Every directory named `trash` below `top`, not descending into one."""
    for dirpath, dirnames, _ in os.walk(top):
        here = Path(dirpath)
        dirnames[:] = [
            name
            for name in dirnames
            if name not in PRUNE and not is_git_dir(here / name)
        ]
        if TRASH in dirnames:
            dirnames.remove(TRASH)
            yield here / TRASH


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


def scratch_roots(home: Path) -> list[Path]:
    """Every sweepable root: `home/tmp`, plus each untracked `trash/` below."""
    return [home / "tmp"] + [
        trash for trash in find_trash_dirs(home) if not git_tracks_content(trash)
    ]


__all__: Sequence[str] = (
    "PRUNE",
    "TRASH",
    "find_trash_dirs",
    "git_env",
    "git_tracks_content",
    "is_git_dir",
    "scratch_roots",
)
