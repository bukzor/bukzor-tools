---
path: ~/claude/homedir-archeology/claude-code-holistics/members.py
replaced-by:
  - ../stages.kb/session-reduction.md
---

# holistics members.py

Decides which transcripts are corpus members and computes `last_activity`
by reading the newest timestamp from the file's tail. That recency rule
is the right one and is what the sessions stream adopts; the membership
predicate (exclude the pipeline's own cwd and scratchpads) becomes a
`select` on `cwd`.
