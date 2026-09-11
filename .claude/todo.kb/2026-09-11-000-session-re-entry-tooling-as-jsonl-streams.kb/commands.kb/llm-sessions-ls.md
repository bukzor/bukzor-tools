---
status: missing
effort-sweh: 0.5
---

# llm-sessions ls

Lists `sessions.kb` entries touched since a date, with their open
checkboxes and the session ids they cover. [frontmatter-extraction] over
the entries joined with [checkbox-extraction] on `path`; the session ids
are `.["@value"].session.uuid[]`.

The `llm-sessions` skill ships no executable today, only a `SKILL.md` and
a schema. This and [llm-sessions-uncovered] would be its first two, and
both are `jq` files.

[frontmatter-extraction]: ../stages.kb/frontmatter-extraction.md
[checkbox-extraction]: ../stages.kb/checkbox-extraction.md
[llm-sessions-uncovered]: ./llm-sessions-uncovered.md
