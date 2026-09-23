# records

One line per transcript record, decoded and flat. Produced by
[record-decoding]; the substrate every other question is asked of.

```
kind      "record"                       constant
session   string                         the transcript's sessionId
uuid      string                         present on every talk record
parent    string|null                    parentUuid
time_ns   integer                        nanoseconds since the Unix epoch
type      enum                           see below
text      string                         decoded text, blocks joined, "" when none
cwd       string
sidechain boolean                        true inside a subagent transcript
agent     string|null                    agent name for subagent records
model     string|null
tool      string|null                    tool name on tool-use / tool-result
title     string|null                    on type=title only
file      string?                        only when tagged by rg; see below
line      integer?                       only when tagged by rg
```

`type` collapses the sixteen raw record kinds to nine:
`user-text`, `tool-result`, `assistant-text`, `tool-use`, `thinking`,
`system`, `compact`, `title`, `injected`. `injected` is user-role text the
harness wrote (command wrappers, compaction summaries, interruption
markers); `title` folds the `custom-title`, `agent-name`, and `ai-title`
records. Raw kinds that carry no session content (`mode`,
`permission-mode`, `atis-latch`, `file-history-*`, `cost-state`,
`queue-operation`) are dropped.

Invariants a consumer may rely on: every line has `session`, `time_ns`,
and `type`; `text` is never JSON-escaped twice; the empty string, not
null, means no text. `file` and `line` appear only when the stream was produced
through the tagger and are addresses into the raw file, not identity.
Identity is `uuid`; see [cite-by-uuid].

[record-decoding]: ../stages.kb/record-decoding.md
[cite-by-uuid]: ../open-questions.kb/cite-records-by-uuid-not-line.md
