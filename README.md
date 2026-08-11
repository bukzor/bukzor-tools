# bukzor-tools

Assorted small tools: too small for their own repos, too heavy for
dotfiles. One package per tool under `packages/`, plus a `bukzor-tools`
meta-package that depends on all of them.

Dotfiles hold glue -- wrappers and shims that only make sense beside my
config. These are programs: they carry knowledge worth testing, grow
subcommands, and shouldn't ride along to every machine that clones my
dotfiles.

## Tools

| package                                                     | command                                                                      | what it does                                                  |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------- |
| [claude-code-archeology](packages/claude-code-archeology)   | `claude-search`, `claude-inventory`, `claude-branch-list`, `-branch-extract` | find, resume and recover past Claude Code sessions            |
| [claude-code-slug](packages/claude-code-slug)               | `claude-slug`, `claude-path`                                                 | Claude Code's `projects/<slug>/` path encoding                |
| [git-localhost-store](packages/git-localhost-store)         | `git-localhost-store`, `-install`                                            | keep every `.git` in a central store, so `rm -rf` can't lose commits |
| [google-issuetracker](packages/google-issuetracker)         | `google-issuetracker`                                                        | search Google's public issue trackers (Buganizer) anonymously |
| [upstream-replies](packages/upstream-replies)               | `upstream-replies`                                                           | nag when bug reports I filed get replies                      |

## Install

```bash
uv tool install .                             # everything, shims into ~/.local/bin
uv tool install ./packages/upstream-replies   # or just one
```

Upgrade after pulling: `uv tool upgrade bukzor-tools` (or
`uv tool install . --force` from a working copy).

`git-localhost-store` wants one step more, every time it moves: git
looks for its hooks outside any venv, so `git-localhost-store-install`
writes them there and aims the public path at the venv you just
installed into.

## Develop

```bash
uv sync --all-packages
uv run pytest
uv run pre-commit run --all-files
```

## Adding a tool

Copy the shape of the smallest existing package: a `pyproject.toml`
(hatchling, `packages = ["lib/NAME"]`, a `[project.scripts]` entry), the
module under `lib/`, and `*_test.py` beside the code it tests. Add it to
the meta-package's `dependencies`, `[tool.uv.sources]`, and
`[project.scripts]` (that last one is what puts the command on PATH for
people who installed the meta-package).

## Graduation

A tool leaves when it stops being small: its own release cadence, users
who aren't me, or dependencies the other tools shouldn't carry. Extract
it to its own repo then -- the packages are already independently
buildable, so extraction is a directory move plus a dependency swap.
Node tools are welcome under the same rule (a pnpm workspace goes in
when the first one lands).
