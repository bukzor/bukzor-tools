---
path: ~/claude/homedir-archeology/claude-code-holistics/render.py
replaced-by:
  - ../stages.kb/record-decoding.md
---

# holistics render.py, the text path

`speaker`, `first_text`, `plain_text`, and `render_block` decode records
into readable talk with a `# L<n>` address per record. The decoding
retires into the stream; the readable rendering stays as a view over it,
and its address form is the subject of
`../open-questions.kb/cite-records-by-uuid-not-line.md`. `split_parts`
and the context-budget split are untouched.
