---
status: missing
effort-sweh: 0.5
---

# llm-sessions uncovered

The anti-join: sessions active since a cut whose id appears in no
`sessions.kb` entry's `session.uuid`. Concatenate [sessions] and
[frontmatter] lines, `group_by(.session // .["@value"].session.uuid[])`,
keep groups with no frontmatter member.

This is the command that would have named the day's largest risk on
2026-09-10: the previous afternoon's holistics sitting had left work
uncommitted in three repos with no session entry, and only a hand sweep
found it.

[sessions]: ../streams.kb/sessions.md
[frontmatter]: ../streams.kb/frontmatter.md
