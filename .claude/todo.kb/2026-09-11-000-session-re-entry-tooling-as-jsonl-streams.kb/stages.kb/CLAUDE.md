# Stages

One file per process in the machinery layer. A stage is either a map
(takes file paths, emits a stream) or a reduce (takes a stream on stdin,
emits a stream). No stage does both, and no stage chooses its own inputs.

## What belongs here

The stage's input and output, its status and effort in frontmatter
(schema: `../stages.jsonschema.yaml`), what existing code it grows from,
and the constraints it must respect, linked into
`../discovered-constraints.kb/`. Name the command line where one is
settled; keep it to a line or two.

## What does not belong

User-facing commands; those compose stages and live in `../commands.kb/`.
Stream field definitions; those are in `../streams.kb/`. Implementation
code; a stage file names a runnable path once one exists.

## When to add

When the design needs a process that no existing stage provides. When a
stage lands, update `status` to `built` and name the commit; do not delete
the file.
