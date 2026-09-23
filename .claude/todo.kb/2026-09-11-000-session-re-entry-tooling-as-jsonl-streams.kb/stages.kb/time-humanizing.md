---
status: missing
effort-sweh: 0.5
---

# time-humanizing

Reduce: any stream in, the same stream out, with the value of every key
ending `time_ns` replaced in place by
`{"@value": <the integer>, "s": "<local ISO 8601 with offset>"}`, e.g.
`{"@value": 1790186975411343607, "s": "2026-09-23T13:09:35,411343607-05:00"}`.
Local means the zone of the process running the humanizer.

The last stage of any pipeline, for reading only; its output feeds no
further filter ([objects-rank-above-numbers]).

[objects-rank-above-numbers]: ../discovered-constraints.kb/jq-compares-big-integers-exactly.md
