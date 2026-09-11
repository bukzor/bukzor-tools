---
path: ~/claude/homedir-archeology/claude-code-holistics/pending.py
replaced-by:
  - ../stages.kb/session-reduction.md
  - ../stages.kb/frontmatter-extraction.md
---

# holistics pending.py

Classifies each member as unrendered, grown, undigested, or stale-digest
by comparing the transcript's last record against the render's recorded
span and the digest's frontmatter. That is a join of the sessions stream
with the digests' frontmatter stream on session id, and a comparison of
`t_last` against `span`.
