# Envelope shape for stream lines

`md-frontmatter` emits `{path, "@value": {...}}`; the transcript streams
as designed are flat objects with `kind` at top level. Two candidates:

- Flat everywhere: simplest `jq`, and `kind` plus the natural keys
  (`session`, `path`) are the join columns. Requires changing
  `md-frontmatter`'s output or wrapping it.
- Envelope for anything read from a file, flat for anything derived from
  records or git: keeps `md-frontmatter` as is and generalises to every
  kb tool, at the cost of `.["@value"]` in every frontmatter filter.

Agent recommendation, 2026-09-11: the second, because it is what exists
and the kb tooling already reads it.
