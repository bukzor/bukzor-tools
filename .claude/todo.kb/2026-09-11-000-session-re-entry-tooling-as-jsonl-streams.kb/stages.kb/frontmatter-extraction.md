---
status: exists
effort-sweh: 0.5
---

# frontmatter-extraction

Map: markdown paths in, [frontmatter] lines out. `md-frontmatter FILES`
does this today and is the model the other streams copy; the only change
is adding `kind` to its output.

It is a path consumer, not a stdin filter: a front block is delimited by
position in its file, so a concatenation of files cannot be split back
([frontmatter-needs-boundaries]). `xargs md-frontmatter` keeps selection
separate all the same. A stream form does exist for the block alone,
`rg -U --json '\A---\n[\s\S]*?\n---\n'`, which yields each block as one
match with its path; the YAML parse still happens outside `jq`.

[frontmatter]: ../streams.kb/frontmatter.md
[frontmatter-needs-boundaries]: ../discovered-constraints.kb/frontmatter-needs-file-boundaries.md
