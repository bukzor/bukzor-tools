# Where the jq view files live

Every command is `emitter | jq -f VIEW`, so the views need a home an
agent can name from prose and `ls` to discover. Candidates:

- `~/.claude/jq/`, beside the other agent-facing configuration; on no
  `PATH` but a fixed address.
- Inside the `claude-code-archeology` package, shipped and versioned with
  the emitters; needs a lookup helper to be reachable from a shell line.
- One `jq` module file per stream with named functions, imported with
  `-L`; fewest files, least discoverable.

Agent recommendation, 2026-09-11: the first for views over any stream,
the second only for views the package's own console scripts call.
