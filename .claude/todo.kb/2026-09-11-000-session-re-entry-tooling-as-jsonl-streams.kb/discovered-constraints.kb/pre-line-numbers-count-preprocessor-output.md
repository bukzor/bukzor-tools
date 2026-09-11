---
measured: 2026-09-11
session: 01f46623
---

# Under --pre, line numbers count the preprocessor's output

`rg --json --pre CMD` runs `CMD FILE` and searches its stdout, tagging
each match with the file's path and the line number within that stdout.
A decoder that drops or splits records therefore yields line numbers
that do not address the source file. Source addresses must be emitted by
the decoder itself, which is one reason records are identified by `uuid`.
