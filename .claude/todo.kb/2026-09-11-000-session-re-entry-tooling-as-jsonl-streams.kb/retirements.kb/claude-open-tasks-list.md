---
path: ~/bin/claude-open-tasks-list
replaced-by:
  - ../commands.kb/claude-open-tasks-list-touched-since.md
  - ../stages.kb/checkbox-extraction.md
---

# claude-open-tasks-list

The lister the subtask skill documents as the backlog enumerator. Carries
its own `status:` regex, its own checkbox regex, and a worktree dedup by
effective mtime. The two regexes retire into the streams; the dedup is the
one part that is an algorithm and is decided in the command's file.
