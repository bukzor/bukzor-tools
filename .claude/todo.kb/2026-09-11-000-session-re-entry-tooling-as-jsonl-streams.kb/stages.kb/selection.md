---
status: partial
effort-sweh: 0.5
replaces:
  - ~/claude/homedir-archeology/lib/bukzor_homedir_archeology/survey.py
---

# selection

Map, degenerate: takes a root, emits file paths. Every other stage is fed
by this one through `xargs`, so which files a question covers is decided
here and nowhere else.

Settled form: `rg --files` with `-g` globs. Two flags are mandatory below
the home directory, both measured in [home-gitignore]: `--no-ignore-parent`
so the dotfiles repo's ignore rules do not hide every other repo, and
`--ignore-file` naming a three-line prune list (`trash/`, `node_modules/`,
`.venv/`) that replaces the Python prune list in the homedir survey. With
both, the sweep of markdown under `~/repo` dropped from thirty-six
thousand files to fifty-four hundred with zero from `trash/`.

Transcript selection is the same command over `~/.claude/projects` with
`-g '*.jsonl'`; a time cut is a `jq` filter on `last_time_ns` downstream,
not a `find -mtime` here, for the reason in [mtime-moves-on-exit].

What exists: `bukzor-homedir-archeology find` owns the prune logic today
and takes `find` primaries. The change is to express that list as an
ignore file `rg` reads, and point the survey at it.

[home-gitignore]: ../discovered-constraints.kb/home-gitignore-hides-everything-below.md
[mtime-moves-on-exit]: ../discovered-constraints.kb/transcript-mtime-moves-on-exit.md
