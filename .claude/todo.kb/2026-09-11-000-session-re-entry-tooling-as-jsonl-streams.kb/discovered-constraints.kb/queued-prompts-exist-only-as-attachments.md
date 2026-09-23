---
measured: 2026-09-23
session: 32e41eca
---

# A prompt queued mid-turn exists only as an attachment

A prompt typed while the agent is busy is stored as an `attachment` record
with `attachment.type` `queued_command` and `commandMode` `prompt`, beside
two `queue-operation` records; no `user` record repeats it. In session
a9fd5254 the prompt "on the smoke-test idea: ..." appeared at 20:16:30 in
those three records and next only inside a compaction summary ten minutes
later. Over the whole corpus, 177 of 520 `queued_command` attachments are
prompts; the rest are task notifications. One prompt was a block list
(text and image), not a string.

Typed slash commands are likewise stored only as harness wrappers: 642
`user` records and 314 `system` `local_command` records whose text opens
with `<command-name>` or `<command-message>`, none flagged `isMeta`.
