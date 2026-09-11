---
status: exists
effort-sweh: 0.5
replaces:
  - ~/.local/bin/claude-search
---

# claude-search

Exists and works; the change is to make it a view. `select(.text|test($p))`
over [records], grouped by session for the report, with `--role` as a
predicate on `type`. Its own text extraction retires into
[record-decoding], and its hits cite `uuid` instead of a line number.

[records]: ../streams.kb/records.md
[record-decoding]: ../stages.kb/record-decoding.md
