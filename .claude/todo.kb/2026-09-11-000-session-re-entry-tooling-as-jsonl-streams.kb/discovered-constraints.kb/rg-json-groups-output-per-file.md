---
measured: 2026-09-11
session: 01f46623
---

# rg --json output is grouped per file

Over nine files searched in one invocation, the `begin` and `end` records
strictly alternated: no file's matches interleave with another's, even
though `rg` searches files in parallel. A consumer may treat the stream
as a sequence of per-file blocks without buffering. Order of files is not
guaranteed and does not matter, since every match carries its path.
