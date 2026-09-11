---
measured: 2026-09-11
session: 01f46623
---

# Every slug under projects/ begins with a dash

The directory for a cwd is its path with `/` and `.` mapped to `-`, so
every transcript path relative to `~/.claude/projects` starts with `-`.
`rg -home-bukzor/...` parsed the name as flags and failed; `jq` inside a
`--pre` script did the same. Every command that takes these paths as
arguments needs `--` before them, and a preprocessor must read the file
by stdin redirection.
