# Where the stream contracts live once the task closes

The field lists in `streams.kb/` and the rule that every stage takes files
or a stream are what anyone writing a `jq` filter needs every time. They
sit in a task kb, and `todo clear` deletes completed `todo.kb/` files.
Candidates:

- The package's `CLAUDE.md` (or README) in `claude-code-archeology`,
  written as each emitter lands: stream shapes, the selection rule, and the
  `claude-jq` listing. The kb keeps the design and the measurements.
- Leave them in the kb and exempt it from `todo clear`: nothing moves, and
  a kb under `todo.kb/` goes on meaning "work not yet done".
- Emit them from the code, e.g. `claude-jsonl-records --schema`: cannot
  drift, but needs a schema to maintain beside the decoder and says
  nothing about the rule.

The records contract is the first to exist, so the first candidate can
start there at no cost.

Agent recommendation, 2026-10-01: the first. [!DRAFT]
