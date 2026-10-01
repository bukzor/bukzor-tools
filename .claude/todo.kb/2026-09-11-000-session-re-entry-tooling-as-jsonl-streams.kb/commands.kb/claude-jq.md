---
status: missing
effort-sweh: 0.5
---

# claude-jq

`jq` with the user and package view directories on its library path and
every view the program names already in scope, so a view is called by its
bare name:

```sh
claude-jsonl-records | claude-jq 'sessions' -s
```

The program is the first argument and `jq` options follow it. With no
arguments it lists every view: name, one-line summary, input form (`-s` or
a stream), and the directory it came from, each taken from a comment that
opens the view file. That listing is the `ls` of the views, since the user
directory holds only overrides.

Where the views live, how they are found, and why `claude-jq` generates
the `include` lines are in [home-for-jq-views]. Nothing exists yet; the
mechanism was exercised by hand against two scratch directories.

[home-for-jq-views]: ../open-questions.kb/home-for-jq-views.md
