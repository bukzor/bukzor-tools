---
status: built
effort-sweh: 3
replaces:
  - ~/repo/github.com/bukzor/bukzor-tools/packages/claude-code-archeology/lib/claude_code_archeology/format_short.py
  - ~/claude/homedir-archeology/claude-code-holistics/render.py
  - ~/claude/homedir-archeology/claude-code-holistics/usage-mix.py
---

# record-decoding

Map: raw transcript records in, [records] lines out. The one place the
transcript format is understood; every consumer reads the stream instead.

Built in 80f5051 as `claude_code_archeology.records` and the
`claude-jsonl-records` console script. It reads stdin only and ignores its
arguments, which gives two invocation forms from one decoder. As a filter it
reads concatenated raw JSONL, which is lossless because every talk record
carries its session id ([session-id-on-records]). Under `rg --pre` it runs
per file with `rg`'s parallelism and origin tagging; `rg` connects the file
to the preprocessor's stdin and passes the path as an argument, which is
ignored because every path under `~/.claude/projects` begins with a dash
([dash-slugs]). The tagged line numbers count the decoder's output, not the
source ([pre-line-numbers]). Both forms emit identical records; a day of
transcripts decodes in about two seconds either way, the whole corpus in
twenty-two.

Classification builds on `claude_code_archeology.provenance` (`typed`,
`strip_harness_spans`) and `session.is_user_text`. Two rules came from the
corpus rather than the design: queued prompts and typed slash commands
decode as `user-text` ([queued-prompts]).

Text extraction is still duplicated in `format_short.label`, holistics
`render.py`, `search.py`, and `usage-mix.py`; moving them onto this stream
is [retirements]. The live `claude --print --output-format stream-json`
feed has not been tried through the decoder. Whether the decoded stream is
cached beside each transcript is [cache-the-records-stream].

[records]: ../streams.kb/records.md
[session-id-on-records]: ../discovered-constraints.kb/talk-records-carry-session-id.md
[pre-line-numbers]: ../discovered-constraints.kb/pre-line-numbers-count-preprocessor-output.md
[dash-slugs]: ../discovered-constraints.kb/project-slugs-begin-with-a-dash.md
[queued-prompts]: ../discovered-constraints.kb/queued-prompts-exist-only-as-attachments.md
[retirements]: ../retirements.kb/CLAUDE.md
[cache-the-records-stream]: ../open-questions.kb/cache-the-records-stream.md
