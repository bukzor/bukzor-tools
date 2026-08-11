# git-localhost-store

**Protect your local git repositories from accidental deletion.**

## Problem

A stray `rm -rf` can destroy weeks of work if you haven't pushed to a
remote. Local git repositories are fragile and ephemeral.

## Solution

Every repository's objects live in a central store, indexed by working
directory path. Delete the entire working directory and the commits are
still there, recoverable by recreating the directory.

## How It Works

`git init` copies the hooks in but fires none of them; the first `git
add`, commit, or checkout in the new repository runs
`git-localhost-store`, as does the checkout at the end of a `git clone`.
It:

1. Moves `.git/` into a per-repo store under
   `~/.local/state/git-localhost-store/repos/<encoded-path>/`.
2. Replaces `.git` with a **symbolic link** to that store.

After the swap, `.git` is a symlink rather than a directory. Git follows
it transparently. Naive readers (lazy.nvim, ad-hoc shell scripts, IDE
plugins) that do `open(repo + "/.git/HEAD")` work unchanged, because the
symlink resolves through the filesystem.

### Path encoding

`claude-code-slug` names the store: every character that is not ASCII
alphanumeric becomes exactly one `-`.

```
/home/you/projects/myrepo → -home-you-projects-myrepo
```

It is a dependency rather than a copy because the name has to survive
the tool that wrote it: a store is *named* by this function, so a second
implementation that disagrees anywhere doesn't fail, it strands a
repository in a directory nobody looks in.

## Installation

```bash
uv tool install git-localhost-store
git-localhost-store-install
```

The second command is the one that touches your system, and it is
idempotent -- re-run it after upgrading, or after moving the venv. It
creates the store root, writes the hook template, points
`init.templateDir` at it, and aims one stable path
(`~/.local/share/git-localhost-store/bin/git-localhost-store`) at the
freshly installed relocator.

git allows exactly one `init.templateDir`. If yours is already set to
something else, the installer says so and changes nothing; merge the
hooks by hand.

Existing repositories keep their old hooks and are unaffected -- hooks
are copied at init time, not read from the template afterwards. To
convert one, run `git-localhost-store` in it.

## Recovery

After `rm -rf` of a working directory:

```bash
mkdir ~/projects/myrepo && cd ~/projects/myrepo
git init
git-localhost-store   # adopts the surviving store, restores tracked files
```

**Re-cloning instead:** if the workdir had a remote, a plain `git clone`
into the original path works directly -- the hook force-syncs
remote-tracking refs and fast-forwards the local branch when it can. It
refuses only when the store holds local commits that are not a
fast-forward of the fresh clone. That refusal wants a human, not another
`rm -rf`.

## Commands

### `git-localhost-store [HOOK-NAME]`

Convert the repository containing the current directory, or recover it
if its store already exists. Idempotent, and a no-op when `.git` is
already a symlink, or is a gitfile (worktree or submodule). Any other
shape is an error: it asserts and exits non-zero rather than guess.

Hooks pass their own name as the argument; you don't.

### `git-localhost-store-install`

See Installation.

## Layout

```
~/.local/share/git-localhost-store/    # written by the installer
├── bin/git-localhost-store            # -> the installed console script
└── template-repo/hooks/               # git init template
    ├── shared                         # the hook body
    └── post-{index-change,commit,checkout}  # -> shared

~/.local/state/git-localhost-store/    # your repositories -- back this up
└── repos/<encoded-path>/              # one gitdir per workdir
```

## Limitations

- Protects commits and staged changes, not unstaged modifications.
- Recovery requires recreating the directory at the exact original path.
- Stores in the state directory can still be deleted by hand.
- Not a substitute for a remote.
- One worktree per store. `git worktree add` from the central gitdir
  still works; it is just not automated here.

## Design Principles

- **Automatic** -- works without user intervention.
- **Transparent to naive readers** -- `.git/HEAD` resolves through the
  symlink as an ordinary file.
- **Deterministic** -- the recovery path follows from the workdir path.
- **Explicit errors** -- failures are visible. No `|| true`.
- **Idempotent** -- hooks and `git-localhost-store` are safe to re-run.
