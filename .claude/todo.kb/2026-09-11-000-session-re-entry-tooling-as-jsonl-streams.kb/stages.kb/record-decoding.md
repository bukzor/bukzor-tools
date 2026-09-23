---
status: partial
effort-sweh: 3
replaces:
  - ~/repo/github.com/bukzor/bukzor-tools/packages/claude-code-archeology/lib/claude_code_archeology/format_short.py
  - ~/claude/homedir-archeology/claude-code-holistics/render.py
  - ~/claude/homedir-archeology/claude-code-holistics/usage-mix.py
---

# record-decoding

Map: raw transcript records in, [records] lines out. The one place the
transcript format is understood; every consumer reads the stream instead.

Two invocation forms, same decoder. As a filter it reads concatenated raw
JSONL on stdin, which is lossless because every talk record already
carries its session id ([session-id-on-records]). Under `rg --pre` it runs
per file with `rg`'s parallelism and origin tagging, at the cost that the
tagged line numbers count the decoder's output, not the source
([pre-line-numbers]); inside the preprocessor the file must be read via
stdin redirection, not as an argument ([dash-slugs]). The live
`claude --print --output-format stream-json` feed is the same shape and
should go through the same decoder.

What exists: `claude_code_archeology.session` parses and classifies
(`is_user_text`, `role_of`), and is the survivor. Text extraction is
duplicated in `format_short.label`, holistics `render.py`, `search.py`,
and `usage-mix.py`; the decoder absorbs all four. The type collapse and
the `injected` classification are new. Converting the UTC timestamp to
`time_ns` is new and is where [timestamps-are-utc] stops recurring.

Whether the decoded stream is cached beside each transcript is
[cache-the-records-stream]. Home is
`claude_code_archeology`, as a module plus a `claude-jsonl-records`
console script.

[records]: ../streams.kb/records.md
[session-id-on-records]: ../discovered-constraints.kb/talk-records-carry-session-id.md
[pre-line-numbers]: ../discovered-constraints.kb/pre-line-numbers-count-preprocessor-output.md
[dash-slugs]: ../discovered-constraints.kb/project-slugs-begin-with-a-dash.md
[timestamps-are-utc]: ../discovered-constraints.kb/timestamps-are-utc.md
[cache-the-records-stream]: ../open-questions.kb/cache-the-records-stream.md
