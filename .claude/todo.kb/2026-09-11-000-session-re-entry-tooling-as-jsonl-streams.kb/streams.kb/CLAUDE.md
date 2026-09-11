# Streams

One file per jsonl stream: the contract between the stage that emits it
and every `jq` filter that reads it.

## What belongs here

A stream's line shape (field names, types, which are required), the `kind`
value its lines carry, the stage that produces it, and the invariants a
consumer may rely on. State fields in a fenced block, one per line, with
the type and a short note.

## What does not belong

How the stream is produced (that is the stage's file) or consumed (that is
the command's file). Prose about why the design uses streams at all; the
overview task file has that.

## When to add

When a stage emits lines of a new shape. Two stages emitting the same shape
share one stream file.
