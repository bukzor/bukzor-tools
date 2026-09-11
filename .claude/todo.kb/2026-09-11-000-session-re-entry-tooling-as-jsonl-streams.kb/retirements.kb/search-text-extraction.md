---
path: ~/repo/github.com/bukzor/bukzor-tools/packages/claude-code-archeology/lib/claude_code_archeology/search.py
replaced-by:
  - ../stages.kb/record-decoding.md
  - ../commands.kb/claude-search.md
---

# search.py text extraction

Builds the searchable text of a record, including tool inputs serialised
with `json.dumps`, then regex-matches it. The extraction is the decoder's
job; the match and the per-session report become the `claude-search` view.
