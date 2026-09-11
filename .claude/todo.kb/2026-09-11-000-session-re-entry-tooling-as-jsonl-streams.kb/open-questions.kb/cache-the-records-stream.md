# Whether to cache the records stream per transcript

Decoding is fast enough that a day needs no cache (a full day tagged and
decoded in under half a second), and a month is on the order of a minute.
Candidates:

- No cache: every question re-decodes; pure filters, nothing to
  invalidate.
- Cache beside each transcript, invalidated by size and tail timestamp,
  the pattern holistics `pending.py` uses for renders; makes the
  month-scale search interactive at the cost of a stateful stage.
- A memoising wrapper around the selection-to-records leg, generic over
  any map stage.

Agent recommendation, 2026-09-11: start without one and measure the
first month-scale query before deciding.
