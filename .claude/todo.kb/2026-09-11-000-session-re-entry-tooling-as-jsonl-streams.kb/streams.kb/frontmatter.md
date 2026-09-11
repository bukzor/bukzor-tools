# frontmatter

One line per markdown file that carries YAML frontmatter. This is
`md-frontmatter`'s existing output, adopted unchanged; see
[frontmatter-extraction].

```
kind      "frontmatter"      to be added; absent from md-frontmatter today
path      string
@value    object             the parsed frontmatter
```

Consumers of note: `sessions.kb` entries expose `session.uuid` as an array,
which is the join key against [sessions]; `todo.kb` entries expose
`status` and `cost-benefit-sweh`, which the task listers and `wsjf-rank`
read.

The `{path, "@value"}` envelope is the shape under discussion in
[envelope-shape].

[frontmatter-extraction]: ../stages.kb/frontmatter-extraction.md
[sessions]: ./sessions.md
[envelope-shape]: ../open-questions.kb/envelope-shape.md
