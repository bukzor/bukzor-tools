---
managed-by: Skill(llm-subtask)
status: open
suggested-reading:
  - ~/.claude/projects/-home-bukzor--claude-projects/f65fbdf3-2597-44a8-b099-ee0e9d546ed2.jsonl
  - ~/.claude/projects/-home-bukzor--claude-projects/01f46623-f8f4-45d2-bd30-72201775320a.jsonl
  - ~/.claude/skills/claude-code-archeology/SKILL.md
  - ~/claude/homedir-archeology/claude-code-holistics/CLAUDE.md
cost-benefit-sweh:
  timebox:
    "@value": 8
    rationale: |
      The stage estimates in the parts kb sum to about ten hours, but the
      payoff is front-loaded: the records stream, the sessions reduce, and
      two views (inventory, uncovered) deliver the user story. Retiring the
      duplicate decoders and the two task listers can trail without cost.
    confidence: tentative
  benefit-2w:
    "@value": 2
    rationale: |
      One end-of-day re-entry on 2026-09-10 cost roughly forty tool calls
      and four throwaway scripts, each of which is a jq filter once the
      streams exist. Re-entry recurs weekly at least; the same streams also
      shorten every archeology question that today starts from raw JSONL.
    confidence: tentative
---

# Session re-entry tooling as jsonl streams

**Priority:** Medium **Complexity:** Medium (five small emitters and a
directory of jq files; no new pipeline) **Context:** Two sittings on
2026-09-10 and 2026-09-11 reconstructed a day of twelve concurrent Claude
Code sessions, then designed the tooling that would have made the
reconstruction a ten-minute shell session. The parts are enumerated in
[the parts kb]; this file is the overview.

## Problem Statement

End-of-day re-entry means answering, per thread of work: what did I set out
to do, what actually landed, and what was left open. The evidence is spread
over transcripts under `~/.claude/projects`, commits across dozens of
repos, `sessions.kb` entries, and todo files. No tool today answers any of
the three questions directly, so each sitting rebuilds the same index by
hand.

The 2026-09-10 sitting needed four ad hoc scripts: a per-session index
(span, cwd, turn count, first prompt, last exchange), a cross-repo commit
sweep, a last-N-exchanges view, and a record-type census. Each one
re-parsed the transcript format from scratch.

## Current Situation

Four decoders of the same transcript record exist in two repos:
`claude_code_archeology.format_short`, holistics `render.py`,
`claude_code_archeology.search`, and holistics `usage-mix.py`. Two task
listers in `~/bin` carry their own regex frontmatter parser while
`md-frontmatter` already emits `{path, "@value"}` jsonl. Three per-session
summaries compute recency two different ways, and the mtime-based one
listed thirty sessions on 2026-09-10 when twelve were real.

The one pattern already done right is `md-frontmatter`: a process that
emits one JSON object per input, so every consumer is `jq`.

## Proposed Solution

Agent-proposed, 2026-09-11, open to veto. Requirements first; the
mechanism follows from them.

Requirements:

- Every question in the user story is a `jq` filter over one or more
  streams, so an agent can compose an unplanned question without writing a
  parser.
- Which files feed a stream is a separate concern from what the stream
  contains: selection is `find` or `rg --files`, tagging is `rg --json`,
  and a process never opens a file it was not handed.
- Every stream line carries a `kind` field, so heterogeneous streams can be
  concatenated and joined in one `jq` pass.
- Time is an integer of nanoseconds since the Unix epoch, in a key ending
  `time_ns` (underscore, because `jq` reads `.time-ns` as subtraction).
  Streams carry only the integer; a humanizer annotates it in place as
  `{"@value": 1790186975411343607, "s": "2026-09-23T13:09:35,411343607-05:00"}`.
  [!@bukzor] 2026-09-23. `jq` parses no offset-bearing date string
  correctly ([jq-drops-offsets]) but compares these integers exactly
  ([jq-big-integers]).
- The humanizer runs last, for reading only: `jq` ranks every object above
  every number, so a time filter over annotated lines passes all of them.
  [!DRAFT] 2026-09-23.
- Records are cited by `uuid` prefix, not by line number, because line
  numbers do not survive truncation, extraction, or compaction.

Mechanism, in one rule: map stages take files, reduce stages take a stream.
`rg --json '^'` is the origin tagger that lets a map stage feed a reduce;
`rg --pre` lets a per-file decoder run under `rg`'s parallelism. The
measured behaviour that makes this work, and the four gotchas that
constrain it, are in the parts kb under `discovered-constraints.kb/`.

## Implementation Steps

Outcomes, not procedure. Each links to the part that specifies it.

- [ ] A records stream exists: one decoded line per transcript record,
      flat, with `kind`, `session`, `uuid`, `time_ns`, collapsed `type`,
      and `text` ([records], [record-decoding])
- [ ] A sessions stream is a `jq` reduce over records, and
      `claude-inventory` renders it with first prompt, last exchange, turn
      count, and record-time recency ([sessions], [claude-inventory-index])
- [ ] `llm-sessions uncovered` anti-joins sessions against `sessions.kb`
      frontmatter and names the sessions with no entry
      ([llm-sessions-uncovered])
- [ ] `git-fleet` emits commits and dirty paths across every repo under
      the home directory, grouped by repo ([git-fleet-emission])
- [ ] The two `~/bin` task listers read the frontmatter and checkbox
      streams instead of their own regexes ([checkbox-extraction],
      [claude-open-tasks-list-touched-since])
- [ ] The four duplicate decoders and the duplicate recency rule are
      retired ([retirements])
- [ ] The homedir survey's Python prune list becomes an `rg`
      `--ignore-file` ([selection])

## Open Questions

Four, each in [open-questions]: the envelope shape for stream lines, where
the `jq` view files live, whether the records stream is cached per file,
and whether `uuid` replaces `# L<n>` as the citation form in the holistics
renders.

## Success Criteria

- [ ] The user story in [commands] runs end to end in under ten minutes of
      wall time with no transcript opened by hand
- [ ] `claude-inventory --since 05:00` on 2026-09-10's corpus lists twelve
      sessions, not thirty
- [ ] Each of the four ad hoc scripts from the 2026-09-10 sitting is
      reproduced as a `jq` file of under thirty lines

## Notes

The two source sessions are named in `suggested-reading`. The first is the
re-entry itself, where the missing tools were noticed; the second is the
design and every measurement recorded in the constraints collection. The
holistics pipeline already has the right shape for the escalation path
(per-session digests by dispatched agents) and is left unchanged; the
records stream should become its deterministic front half rather than a
parallel implementation.

[the parts kb]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/CLAUDE.md
[records]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/streams.kb/records.md
[sessions]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/streams.kb/sessions.md
[record-decoding]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/stages.kb/record-decoding.md
[jq-drops-offsets]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/discovered-constraints.kb/jq-date-parsing-drops-utc-offsets.md
[jq-big-integers]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/discovered-constraints.kb/jq-compares-big-integers-exactly.md
[selection]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/stages.kb/selection.md
[checkbox-extraction]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/stages.kb/checkbox-extraction.md
[git-fleet-emission]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/stages.kb/git-fleet-emission.md
[claude-inventory-index]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/commands.kb/claude-inventory-index.md
[llm-sessions-uncovered]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/commands.kb/llm-sessions-uncovered.md
[claude-open-tasks-list-touched-since]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/commands.kb/claude-open-tasks-list-touched-since.md
[commands]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/commands.kb/CLAUDE.md
[retirements]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/retirements.kb/CLAUDE.md
[open-questions]: ./2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.kb/open-questions.kb/CLAUDE.md
