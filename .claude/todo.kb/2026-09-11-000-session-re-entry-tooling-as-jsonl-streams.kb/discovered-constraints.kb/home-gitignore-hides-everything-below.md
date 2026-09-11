---
measured: 2026-09-11
session: 01f46623
---

# The home directory's ignore rules hide every repo below it

The home directory is itself a git repository, so `rg --files` run
anywhere under it consults that repo's ignore rules. With defaults,
`rg --files -g '*.md' ~/repo/github.com/bukzor` returned zero files
against thirty-six thousand with `--no-ignore`. `--no-ignore-parent`
restored per-repo ignore behaviour: 5402 files, three under `trash/`.
Adding `--ignore-file` with `trash/`, `node_modules/`, `.venv/` gave 5399
with none. The exact home rule responsible was not identified; the
escape flag was.
