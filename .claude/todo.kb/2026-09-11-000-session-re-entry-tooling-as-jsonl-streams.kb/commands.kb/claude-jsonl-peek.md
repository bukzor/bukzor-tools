---
status: missing
effort-sweh: 0.5
---

# claude-jsonl-peek

The last N exchanges of one session, talk only: [record-decoding] on the
file, a `jq` tail over `type` in `{user-text, assistant-text}`. Already in
`~/.claude/todo.md` as a gap found twice; the 2026-09-10 sitting wrote it
a third time as a throwaway.

With the stream in place the `--range LO HI` and `--around N` forms in
that todo are the same view with a different `select`, keyed on `uuid`
rather than line number ([cite-by-uuid]).

[record-decoding]: ../stages.kb/record-decoding.md
[cite-by-uuid]: ../open-questions.kb/cite-records-by-uuid-not-line.md
