"""Encode a filesystem path the way Claude Code names its projects/ dirs.

Usage:
    claude-path [PATH]

Encodes PATH (or the current directory), made absolute first: the scheme
has no relative form, since a projects/ directory name -- and a
git-localhost-store key -- must name one directory from every cwd. For
text with no path semantics at all, use `claude-slug`.
"""

from __future__ import annotations

import argparse
import os

from .slug import slug


def logical_cwd() -> str:
    """The current directory as the shell sees it: `$PWD`, not the real path.

    `os.getcwd()` resolves symlinks; a shell's `$PWD` keeps the ones you
    walked through. The difference is load-bearing, because these two
    spellings of one directory encode to two different names, and
    git-localhost-store would give them two different stores.

    `$PWD` is trusted only after `samefile` confirms it still names the
    directory we are in -- it is inherited, so a `chdir` since the process
    started leaves it stale.
    """
    logical = os.environ.get("PWD")
    if logical and os.path.isabs(logical):
        try:
            if os.path.samefile(logical, "."):
                return logical
        except OSError:
            pass
    return os.getcwd()


def normalize(path: str) -> str:
    """Absolutize and normalize `path` lexically, as `realpath -Lm` does.

    Lexically is the operative word, and both halves matter: symlinks are
    *not* resolved (`-L`), and the path need not exist (`-m`).

    >>> normalize("/tmp/./a/b/../c")
    '/tmp/a/c'
    >>> normalize("/no/such/path/..")
    '/no/such'

    A relative path resolves against the current directory, so every caller
    naming one directory gets one answer:

    >>> normalize(".") == logical_cwd()
    True
    """
    return os.path.normpath(os.path.join(logical_cwd(), path))


def path_slug(path: str) -> str:
    """The projects/ directory name -- or store key -- for `path`.

    >>> path_slug("/home/bukzor/repo/github.com")
    '-home-bukzor-repo-github-com'
    """
    return slug(normalize(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path", nargs="?", default=".", help="path to encode (default: cwd)"
    )
    print(path_slug(parser.parse_args().path))
    return 0
