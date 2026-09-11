---
measured: 2026-09-10
session: f65fbdf3
---

# A transcript's mtime moves when the session is closed

Claude Code rewrites a transcript after its session ends, and typing
`/exit` into an idle session appends records. On 2026-09-10 the owner
closed nine stale sessions at 10:08; each file's mtime became that
minute, and `claude-inventory --days 1` listed thirty sessions of which
twelve had done any work that day. Recency must come from the newest
record timestamp, which holistics `members.py` already does by reading
the file's tail.
