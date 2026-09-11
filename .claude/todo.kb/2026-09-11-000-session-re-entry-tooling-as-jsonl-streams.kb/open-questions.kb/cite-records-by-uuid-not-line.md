# Whether uuid replaces the line number as the citation form

The holistics renders, the digests, and `claude-search` cite a record as
`<session>#L<n>`, the line in the raw JSONL. Two facts push the other
way: line numbers do not survive truncation, extraction, or compaction,
and under `rg --pre` they address the wrong stream
(`../discovered-constraints.kb/pre-line-numbers-count-preprocessor-output.md`).
Every talk record has a `uuid`. Candidates:

- `<session>#<uuid-prefix>`: stable across every rewrite; needs a
  resolver to open the record, which the records stream gives for free.
- Keep `#L<n>` and add `uuid` beside it: no sweep of existing citations;
  two address forms to maintain.
- Keep `#L<n>` only: nothing changes; the tagger cannot be used under
  `--pre`.

Agent recommendation, 2026-09-11: the first for new citations; whether
existing digests are swept is a separate, later call.
