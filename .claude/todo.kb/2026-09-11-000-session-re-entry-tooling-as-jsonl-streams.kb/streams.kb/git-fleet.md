# git-fleet

Two line shapes from one emitter, [git-fleet-emission], distinguished by
`kind`.

```
kind      "commit"
repo      string        path of the repo root (~ allowed)
sha       string
t         integer       author epoch
subject   string
files     [string]      paths touched, repo-relative

kind      "dirty"
repo      string
path      string        repo-relative
status    string        the two-column porcelain code, e.g. " M", "??", "A "
```

Ground truth for "what landed" and "what is at risk". On 2026-09-10 the
commit sweep across every repo was the only source that distinguished
work that shipped from work that was only described in a transcript, and
the dirty sweep was what surfaced the previous day's uncommitted holistics
ledgers.

[git-fleet-emission]: ../stages.kb/git-fleet-emission.md
