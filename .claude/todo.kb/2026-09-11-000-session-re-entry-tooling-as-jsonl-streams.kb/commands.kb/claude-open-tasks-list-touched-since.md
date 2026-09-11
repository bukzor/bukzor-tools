---
status: partial
effort-sweh: 1
replaces:
  - ~/bin/claude-open-tasks
  - ~/bin/claude-open-tasks-list
---

# claude-open-tasks-list --touched-since

The existing lister, re-based on [frontmatter] joined with [checkboxes],
plus a time filter. The frontmatter `status` skip list and the
"existence is the signal" rule for `todo.kb` files are `jq` predicates.
Gains `--help`, which one of the two current scripts lacks.

The worktree dedup by effective mtime (commit time when clean, else file
mtime) is a real algorithm and stays in Python as a small helper the view
calls, or is dropped if worktree siblings stop being common. Not decided.

[frontmatter]: ../streams.kb/frontmatter.md
[checkboxes]: ../streams.kb/checkboxes.md
