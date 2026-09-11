---
path: ~/repo/github.com/bukzor/bukzor-tools/packages/claude-code-archeology/lib/claude_code_archeology/inventory.py
replaced-by:
  - ../stages.kb/session-reduction.md
  - ../commands.kb/claude-inventory-index.md
---

# inventory.Summary and scan

Walks the projects directory, loads each session, and builds a `Summary`
keyed on file mtime with the last substantive user text as label. The
mtime key is the defect the sessions stream fixes; `is_substantive` and
the label choice survive as the reduce's rule for `last_prompt`.
`format_row` and `format_sh` become the view.
