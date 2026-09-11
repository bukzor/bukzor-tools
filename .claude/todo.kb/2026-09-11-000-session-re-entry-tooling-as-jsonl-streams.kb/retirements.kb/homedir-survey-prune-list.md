---
path: ~/claude/homedir-archeology/lib/bukzor_homedir_archeology/survey.py
replaced-by:
  - ../stages.kb/selection.md
---

# homedir survey prune list

`survey.find()` owns the list of directories a homedir sweep skips
(`trash/`, `node_modules/`, virtualenvs, build caches, most of `.claude/`)
and applies it through `find` primaries. The list moves to an `rg`
ignore file that `rg --files --ignore-file` reads; the survey keeps its
subcommands and reads the same file. On 2026-09-10 its day view was
mostly node compile cache under `~/tmp`, one line the list lacked.
