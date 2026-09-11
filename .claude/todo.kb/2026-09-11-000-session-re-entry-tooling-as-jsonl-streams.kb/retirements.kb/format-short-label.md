---
path: ~/repo/github.com/bukzor/bukzor-tools/packages/claude-code-archeology/lib/claude_code_archeology/format_short.py
replaced-by:
  - ../stages.kb/record-decoding.md
---

# format_short.label

Turns one record into a one-line label for the branch tree and the
inventory row: picks the text block, truncates, marks tool calls. One of
four decoders of the same record. Its block-walking becomes the decoder's
`text` field; its truncation becomes a view's concern.
