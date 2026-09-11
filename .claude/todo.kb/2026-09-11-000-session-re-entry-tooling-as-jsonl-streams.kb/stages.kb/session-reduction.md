---
status: missing
effort-sweh: 1
replaces:
  - ~/repo/github.com/bukzor/bukzor-tools/packages/claude-code-archeology/lib/claude_code_archeology/inventory.py
  - ~/claude/homedir-archeology/claude-code-holistics/members.py
  - ~/claude/homedir-archeology/claude-code-holistics/pending.py
---

# session-reduction

Reduce: [records] on stdin, [sessions] out. A `jq` file, `group_by(.session)`
then one object per group; `family` is a hash of `first_prompt`.

What exists, in pieces: `inventory.Summary` computes the label and
substantive-text test; holistics `members.py` has the record-time recency
rule (read from the file's tail) and `pending.py` joins it against digests.
None emits JSON and they disagree on recency. This stage is where they
agree, and the three become views over its output.

Wants the whole input, so it is the one stage that must never be run per
file under `xargs -n1`.

[records]: ../streams.kb/records.md
[sessions]: ../streams.kb/sessions.md
