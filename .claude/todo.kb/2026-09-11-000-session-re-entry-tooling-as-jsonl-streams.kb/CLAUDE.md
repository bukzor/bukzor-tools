# Parts of the jsonl-streams re-entry tooling

Elaborates the sibling task file of the same name. That file is the
overview and the requirements; this kb holds one file per part, so a
builder can pick up one part without re-reading the design.

## Collections

- `streams.kb/` -- the data contracts: one file per jsonl stream, stating
  its line shape and which stage produces it.
- `stages.kb/` -- the machinery: one file per process, each a map over
  files or a reduce over a stream. Frontmatter carries build status and
  effort, so `ls` plus `md-frontmatter` is the distance-to-done report.
- `commands.kb/` -- the ergonomics: one file per user-facing command, each
  a composition of stages. Same frontmatter as stages.
- `retirements.kb/` -- existing code the design supersedes, one file per
  artifact, naming what replaces it.
- `discovered-constraints.kb/` -- measured facts about `rg`, `jq`, and the
  transcript format that the design must work within. Facts, not choices.
- `open-questions.kb/` -- decisions left to the owner, with the candidates
  considered.

## What belongs here

A part of this one design: a stream, a stage, a command, a retirement, a
constraint, or an open question. Add a file when the design gains a part
or when building reveals a constraint the design did not know.

## What does not belong

Work on the archeology library that this design does not motivate; that
is the repo's own `todo.md`. Session narratives; those are `sessions.kb`
entries. A ruling on an open question closes the question in place rather
than adding a file.

## Status is data

`stages.kb/` and `commands.kb/` share `part-status.jsonschema.yaml`. When a
part lands, set its `status` and leave the file; the collection is the
record of what was planned as well as what was built.
