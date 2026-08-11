#!/bin/bash
# git-localhost-store: shared hook body. post-index-change, post-commit, and
# post-checkout are symlinks to this file -- guarding/state logic lives in
# the relocator itself, this just dispatches into it.
#
# `git-localhost-store-install` writes this into the template directory, and
# git copies it from there into every repo it initializes. A copy therefore
# outlives the release that made it, which is why the exec target below is
# the stable public path rather than this venv's `bin/`: the installer points
# that one path at whichever venv is current, and every copy ever made
# follows.

set -euo pipefail

export DEBUG="${DEBUG:-0}"
if (( DEBUG > 0 )); then
  set -x
  : "$(basename "$0")" "$@"
fi

exec "${XDG_DATA_HOME:-$HOME/.local/share}/git-localhost-store/bin/git-localhost-store" "$(basename "$0")"
