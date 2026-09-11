---
measured: 2026-09-11
session: 01f46623
---

# A front block is delimited by file position, not content

YAML frontmatter is the block between the first line `---` and the next;
`---` is also a horizontal rule in markdown. A concatenation of files
cannot be split back into blocks, so frontmatter extraction is a path
consumer. The block alone can be pulled as a stream with
`rg -U --json '\A---\n[\s\S]*?\n---\n'`, verified on a `sessions.kb`
entry; `\A` anchors to the file start, which is what makes it safe.
