"""Slugify text the way Claude Code names its projects/ directories.

Usage:
    claude-slug TEXT
"""

from __future__ import annotations

import argparse
import re

# Reverse-engineered from ~/.claude/projects/: every character that is not
# ASCII alphanumeric becomes exactly one '-'. No squeezing of runs, no case
# folding, no exemption for '.' or '_'.
NON_ALNUM = re.compile(r"[^A-Za-z0-9]")


def slug(text: str) -> str:
    """Encode `text` as Claude Code would encode it into a directory name.

    Runs are not squeezed, so the result is the same length as the input:

    >>> slug("/home/bukzor/repo/github.com/bukzor/bukzor-tools")
    '-home-bukzor-repo-github-com-bukzor-bukzor-tools'
    >>> slug("a--b")
    'a--b'

    Case survives. Nothing else does -- `.` and `_` are not exempt:

    >>> slug("Buck's Tools_v2")
    'Buck-s-Tools-v2'

    The mapping is many-to-one and so cannot be inverted: `-` is the image
    of `/`, of `.`, and of itself. Read a session's `cwd` field instead of
    decoding the directory name that holds it.

    >>> slug("prototype.chatfs/docs") == slug("prototype-chatfs-docs")
    True

    The substitution is per character, not per byte, so one non-ASCII
    character yields one dash however many bytes it encodes to:

    >>> slug("café")
    'caf-'
    """
    return NON_ALNUM.sub("-", text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", help="text to encode")
    print(slug(parser.parse_args().text))
    return 0
