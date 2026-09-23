# records

One line per transcript record, decoded and flat. Produced by
[record-decoding]; the substrate every other question is asked of.

```
kind      "record"                       constant
session   string                         the transcript's sessionId
uuid      string|null                    null on title and relocation records
parent    string|null                    parentUuid
time_ns   integer                        nanoseconds since the Unix epoch
type      enum                           see below
text      string                         decoded text, blocks joined, "" when none
cwd       string|null                    null on title records
sidechain boolean                        true inside a subagent transcript
agent     string|null                    agentId, on subagent records
model     string|null                    on assistant records
tool      string|null                    tool name on tool-use / tool-result
file      string?                        only when tagged by rg; see below
line      integer?                       only when tagged by rg
```

`type` collapses the raw record kinds to nine:

- `user-text` -- what the person typed: a prompt, a prompt queued while the
  agent was busy (stored only as a `queued_command` attachment), or a slash
  command rebuilt as `/name args`. Harness spans are stripped. Inside a
  subagent, the caller's brief.
- `injected` -- user-role text nobody in this session typed: skill bodies,
  compaction summaries, interruption markers, command output, task
  notifications, and messages relayed from peer sessions.
- `tool-result`, `assistant-text`, `thinking`, `tool-use` -- typed by the
  record's first content block; `text` joins every block, tool inputs as
  JSON.
- `system` -- harness notices, including `away_summary` and relocations
  (`text` and `cwd` are the new directory).
- `compact` -- a compaction boundary.
- `title` -- `custom-title`, `agent-name`, and `ai-title`; `text` is the
  title.

Every other attachment and the metadata kinds (`mode`, `permission-mode`,
`atis-latch`, `cost-state`, `file-history-*`, `queue-operation`,
`last-prompt`, `agent-color`, `agent-setting`, `bridge-session`,
`fork-context-ref`) are dropped. A kind the decoder has not met is dropped
with a warning on stderr.

Invariants a consumer may rely on: every line has `session`, `time_ns`,
and `type`; `text` is never JSON-escaped twice; the empty string, not
null, means no text. A record the transcript gives no timestamp (titles,
relocations) carries its session's previous `time_ns`, or its next when it
comes first. Subagent records carry their parent's `session`, so a
per-session count of the main thread filters on `sidechain`. `file` and
`line` appear only when the stream was produced through the tagger and are
addresses into the decoder's output, not identity. Identity is `uuid`; see
[cite-by-uuid].

[record-decoding]: ../stages.kb/record-decoding.md
[cite-by-uuid]: ../open-questions.kb/cite-records-by-uuid-not-line.md
