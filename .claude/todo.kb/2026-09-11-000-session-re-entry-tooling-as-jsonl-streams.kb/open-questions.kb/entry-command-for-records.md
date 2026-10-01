# Whether one command yields the records for a time span

Every question over transcripts starts with the same three stages:

```sh
find ~/.claude/projects -name '*.jsonl' -newermt DATE -print0 |
  xargs -0 cat | claude-jsonl-records | claude-jq ...
```

Candidates:

- `claude-records [--since T]`: selection and decoding in one command, so
  a question reads `claude-records --since 05:00 | claude-jq sessions -s`.
  Several named commands shrink to a line.
- No entry command: each command and each agent assembles the prefix.
  Nothing new to build; every question repeats three stages.

A file's mtime only moves forward, and closing a session moves it further
([mtime-moves-on-exit]), so `-newermt` cannot miss a session that has a
record after the cut; it can only over-include. The exact cut stays a
`jq` filter on `last_time_ns`. Measured: 41 files touched since 2026-09-22
decode in 1.8 s; the whole corpus, 901 files, takes 22 s.

This amends [selection], which says a time cut is never a `find -mtime`:
under the first candidate the mtime is a prefilter and the cut stays in
`jq`.

Agent recommendation, 2026-10-01: the first. [!DRAFT]

[mtime-moves-on-exit]: ../discovered-constraints.kb/transcript-mtime-moves-on-exit.md
[selection]: ../stages.kb/selection.md
