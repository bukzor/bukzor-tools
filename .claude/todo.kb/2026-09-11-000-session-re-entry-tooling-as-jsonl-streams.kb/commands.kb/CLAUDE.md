# Commands

One file per user-facing command in the ergonomics layer. A command is a
composition of stages and `jq` views, thin enough to read as a shell line;
it owns no parsing.

## What belongs here

The command's name and flags, the stages and view it composes, its status
and effort in frontmatter (schema: `../commands.jsonschema.yaml`), and
what it replaces. Where a view file is settled, name it.

## What does not belong

The stages themselves (`../stages.kb/`) or stream shapes
(`../streams.kb/`). Commands that exist today and are untouched by this
design; only name one here when the design changes or composes it.

## When to add

When the user story in `../commands.md` gains a step, or an agent finds
itself writing the same `jq` filter a third time. When a command lands,
set `status: built` and name the commit.
