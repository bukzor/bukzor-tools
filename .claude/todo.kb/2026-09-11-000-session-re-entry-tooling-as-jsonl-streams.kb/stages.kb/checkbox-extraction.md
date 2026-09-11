---
status: missing
effort-sweh: 0.5
replaces:
  - ~/bin/claude-open-tasks
  - ~/bin/claude-open-tasks-list
---

# checkbox-extraction

Map: markdown paths in, [checkboxes] lines out. The [tagging] stage with a
checkbox pattern and a short `jq` reshaping of the submatch:

```
rg --json '^ *- \[(.)\]' -- FILES | jq -c 'select(.type=="match") | ...'
```

Verified 2026-09-11 against a `sessions.kb` entry: one object per item
with path, line, and the bracket character. The regex that both `~/bin`
task listers carry today is this pattern; they become consumers.

[checkboxes]: ../streams.kb/checkboxes.md
[tagging]: ./tagging.md
