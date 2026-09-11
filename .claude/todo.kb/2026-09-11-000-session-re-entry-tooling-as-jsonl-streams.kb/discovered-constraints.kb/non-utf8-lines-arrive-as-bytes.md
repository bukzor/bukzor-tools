---
measured: 2026-09-11
session: 01f46623
---

# A non-UTF-8 line arrives as base64 bytes

For a line that is not valid UTF-8, `rg --json` emits `lines.bytes`
(base64) instead of `lines.text`. Verified on a three-line file with one
invalid byte sequence. The decoding expression is
`.data.lines.text // (.data.lines.bytes|@base64d)`, after which `fromjson`
succeeded on all three lines.
