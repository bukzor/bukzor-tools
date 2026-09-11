---
path: ~/claude/homedir-archeology/claude-code-holistics/usage-mix.py
replaced-by:
  - ../stages.kb/record-decoding.md
---

# holistics usage-mix.py

Parses raw records for model and token usage and prints a per-day TSV.
With `model` and usage fields on the records stream this is a `jq`
`group_by` and a `@tsv`.
