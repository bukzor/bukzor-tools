# Commands: the user story they compose

Persona: the owner at end of day, energy spent, a dozen concurrent
sessions behind them. Goal: intent, outcome, and residue per thread in
under ten minutes, without opening a transcript.

```sh
# 1. what ran today, by record time, with intent and handoff state
claude-inventory --since 05:00 --index

# 2. ground truth for what landed, and what is dirty, across every repo
git-fleet log --since '2026-09-09 18:00'
git-fleet status --dirty

# 3. what the sessions recorded about themselves, and which recorded nothing
llm-sessions ls --since 2026-09-09
llm-sessions uncovered --since 05:00

# 4. open tasks near today's threads
claude-open-tasks-list --touched-since 2026-09-09

# 5. only if a thread is still ambiguous: its closing exchanges
claude-jsonl-peek FILE --tail 3

# 6. only if that is not enough: a digest, delegated
claude-code-holistics catchup --since 2026-09-10
```

Steps one and two answer "done" by intent and by fact. Step three answers
"open" for recorded threads and names the unrecorded ones, which on
2026-09-10 were the riskiest. Step four joins residue to threads by path.
Five and six are escalation. "What next" stays a conversation; no command
here changes that.

Every step is `selection | stage | jq -f view`, and the views share two
join keys: session id and path. Nothing here is a pipeline of its own.
