# claude-code-slug

Claude Code names each session directory under `~/.claude/projects/` after
the working directory the session ran in, slugified: **every character that
is not ASCII alphanumeric becomes exactly one `-`**. No squeezing of runs,
no case folding, no exemption for `.` or `_`.

This package is that one fact, reverse-engineered and pinned by tests, so
that tools which have to agree about it can share an implementation instead
of each carrying a copy of the regex.

## Install

```bash
uv tool install claude-code-slug   # the commands
uv add claude-code-slug            # the library
```

## Use

```console
$ claude-path /home/you/src/my.project
-home-you-src-my-project
$ claude-slug "Notes: 2026-08-10"
Notes--2026-08-10
```

```python
>>> from claude_code_slug import path_slug, slug
>>> slug("prototype.chatfs/docs")
'prototype-chatfs-docs'
>>> path_slug("/home/you/src")
'-home-you-src'
```

`claude-slug` has no path semantics at all, which makes it safe on titles.
`claude-path` adds them: it makes the path absolute and normalizes it
*lexically* first — `realpath -Lm`, so symlinks are not resolved and the
path need not exist — because the scheme has no relative form. A directory
reached through a symlink encodes under the name you reached it by.

## The mapping is not invertible

`-` is the image of `/`, of `.`, and of itself, so `prototype.chatfs/docs`
and `prototype-chatfs-docs` produce the same name. To recover the directory
a session ran in, read the `cwd` field from its JSONL — never decode the
directory name that holds it.

## The encoding is frozen

Anything that has already named data with this function — session
directories, cache keys, relocated git stores — is orphaned by an
improvement to it, not fixed by one. If Claude Code's scheme changes, that
is a new function, not an edit to this one.
