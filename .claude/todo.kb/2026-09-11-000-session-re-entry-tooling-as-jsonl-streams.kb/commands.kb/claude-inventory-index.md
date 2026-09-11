---
status: partial
effort-sweh: 1
replaces:
  - ~/.local/bin/claude-inventory
---

# claude-inventory --index

The existing `claude-inventory`, re-based on [sessions]: [selection] over
`~/.claude/projects`, [record-decoding], [session-reduction], then a row
view. Gains `--since` as a timestamp, first prompt, last exchange, turn
count, local-time span, and family grouping; loses nothing the current
rows show.

The one behavioural change that matters: recency comes from `t_last`, so
sessions closed with `i/exit` no longer float to the top. On 2026-09-10 the
current tool listed thirty sessions of which twelve were real
([mtime-moves-on-exit]).

`--sh` keeps emitting resume commands; that view reads `cwd` and `session`
from the same stream.

[sessions]: ../streams.kb/sessions.md
[selection]: ../stages.kb/selection.md
[record-decoding]: ../stages.kb/record-decoding.md
[session-reduction]: ../stages.kb/session-reduction.md
[mtime-moves-on-exit]: ../discovered-constraints.kb/transcript-mtime-moves-on-exit.md
