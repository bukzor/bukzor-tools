---
path: ~/bin/claude-open-tasks
replaced-by:
  - ../commands.kb/claude-open-tasks-list-touched-since.md
---

# claude-open-tasks

The older of two task aggregators: scans todo files, counts open items,
reads `status:` with its own regex, prints an mtime histogram. Fully
subsumed by the newer lister once that is a view; the histogram is a
`group_by` on the frontmatter stream if anyone still wants it.
