# sessions

One line per session, a reduce over [records] by `session`. Produced by
[session-reduction].

```
kind            "session"
session         string
cwd             string          last cwd seen; resuming elsewhere rewrites it
t_first         integer         epoch of the earliest record
t_last          integer         epoch of the latest record; the recency key
turns           integer         count of type=user-text
first_prompt    string          text of the first user-text record
last_prompt     string          text of the last user-text record
last_assistant  string          text of the last assistant-text record
title           string|null     latest type=title text
family          string          hash of first_prompt; equal for forks and retries
bytes           integer         raw transcript size, when known
models          [string]
```

`t_last` is the only recency a consumer should sort or filter by. File
mtime is not on this stream on purpose: closing a session rewrites the
file, so mtime reports change where there is none
([mtime-moves-on-exit]).

`family` groups sessions that opened with the same prompt. On 2026-09-10
two sessions shared their opening prompt verbatim; they were one thread.

[records]: ./records.md
[session-reduction]: ../stages.kb/session-reduction.md
[mtime-moves-on-exit]: ../discovered-constraints.kb/transcript-mtime-moves-on-exit.md
