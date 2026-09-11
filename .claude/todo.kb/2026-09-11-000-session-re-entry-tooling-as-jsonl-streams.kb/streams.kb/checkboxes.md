# checkboxes

One line per `- [<mark>]` item in a markdown file. Produced by
[checkbox-extraction].

```
kind      "checkbox"
path      string
line      integer
mark      string       the character inside the brackets: " ", "x", "~", ...
checked   boolean      mark != " "
indent    integer      leading spaces; nesting depth is indent / 2
text      string       the line after the bracket, trimmed
```

`mark` is kept raw because the status vocabulary is open-ended in
practice (`[~]` in progress, others appear); `checked` is the common case
precomputed. Joined with [frontmatter] on `path`, this gives the open-task
list without a second parser.

[checkbox-extraction]: ../stages.kb/checkbox-extraction.md
[frontmatter]: ./frontmatter.md
