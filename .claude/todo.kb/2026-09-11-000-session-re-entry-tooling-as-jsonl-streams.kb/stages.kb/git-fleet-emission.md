---
status: missing
effort-sweh: 1
---

# git-fleet-emission

Name consumer: repo paths on stdin, [git-fleet] lines out. Not a content
filter and should not pretend to be one; `cat` of a repository is
meaningless. Selection is still separate: the repo list comes from
`find -name .git` or `rg --files` over the same prune list [selection]
uses.

Per repo, `git log --since` with a NUL-separated format converted to
JSON, and `git status --porcelain` for the dirty lines. Both commands are
read-only. What exists is a twelve-line shell loop written during the
2026-09-10 sitting, in that session's transcript; nothing on disk.

[git-fleet]: ../streams.kb/git-fleet.md
[selection]: ./selection.md
