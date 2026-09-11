---
measured: 2026-09-11
session: 01f46623
---

# The empty pattern matches at every byte

`rg --json ''` reports a submatch at every offset of every line. On a
5.9 MB transcript that produced 276 MB of JSON in 2 s, and the downstream
`jq` took 11 s. The same file with `rg --json '^'` produced 6.9 MB in
0.03 s, one submatch per line. The tagger's pattern is `^`, never `''`.
