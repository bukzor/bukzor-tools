"""Claude Code's projects/<slug>/ naming scheme, as one function.

The encoding is frozen. git-localhost-store names store directories with
it, so a later improvement does not fix old names -- it orphans them.
"""

from .path import path_slug
from .slug import slug

__all__ = ["path_slug", "slug"]
