---
measured: 2026-09-11
session: 01f46623
---

# Every talk record carries its session id, uuid, and timestamp

Counted over two transcripts, 3922 records: every `user`, `assistant`,
`attachment`, and `system` record has `sessionId`, `uuid`, and
`timestamp`. Title and mode records (`custom-title`, `agent-name`,
`ai-title`, `last-prompt`, `mode`, `permission-mode`, `atis-latch`,
`cost-state`) have `sessionId` but no uuid or timestamp. Only
`file-history-snapshot` lacks `sessionId`. Concatenating transcripts
therefore loses nothing a consumer needs except the file line number.
