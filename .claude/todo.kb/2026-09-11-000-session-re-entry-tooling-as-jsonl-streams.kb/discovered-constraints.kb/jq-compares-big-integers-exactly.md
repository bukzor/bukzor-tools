---
measured: 2026-09-23
session: 32e41eca
---

# jq compares big integers exactly and ranks objects above numbers

Nanoseconds since the epoch exceed 2^53. jq 1.8.2 passes
`1790186975411343607` through unchanged and compares it exactly: it is
`>` `1790186975411343600` and not `==` to it. Arithmetic rounds it to a
double (`$t + 0` gives `…600`), an error of a few hundred nanoseconds,
which no duration or `/1e9` conversion notices.

jq orders values by type before value, and objects rank above numbers:
`{"@value": 1, "s": "x"} > 1790186975411343607` is `true`. A time filter
run over annotated lines passes every line and raises no error.
