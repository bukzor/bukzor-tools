# bukzor-tools

## bukzor-tmpwatch

Rulings the owner has not made. The first two were raised in the 2026-08-28..31
session, the rest in the 2026-09-01 simplifying pass; both are recorded in
`~/.claude/sessions.kb/penguin.kb/bukzor-tmpwatch-scratch-gc.md`.

- [ ] Should an unreadable root abort the sweep, or be skipped with a warning?
      Today one `PermissionError` ends the run across every root. Aborting is
      loud and never hides a problem; skipping keeps an unattended nightly job
      useful when a single directory goes bad. Raised three times, no ruling.
- [ ] Add a `--porcelain` flat-path output mode? The grouped report states the
      action and root once and indents the names, so reassembling a full path
      needs the root line. The previous one-full-path-per-line form was
      pipeline-shaped. Offered, not ruled on.
- [ ] Veto check, agent-authored and already landed (2026-09-01): the seven
      `DEFAULT_*` constants moved out of `config.py` into `config_test.py`.
      The code holds no defaults by design -- a setting with no file is an
      error, never a guess -- so a defaults table in the shipped module
      contradicted its own docstring. The drift test survives, but now pins
      the templates to the tests rather than to the code, which amends the
      wording this session recorded for a future `bukzor-confdir` spec.
      One commit to revert.

Simplifications found in the same pass and deliberately left in place. Each is
a subtraction the owner may or may not want; none is a defect.

- [ ] Drop `read_values`' `MissingSettings` guard? Unreachable through
      `load_config`, which validates every file first; only a TOCTOU race
      reaches it. Removing it swaps a named error for `FileNotFoundError`.
- [ ] Drop `expand_keep`'s laziness? Three lines so that a host without
      `/proc/stat` stays configurable -- a host that cannot run this
      systemd-timer tool at all. The weakest surviving mechanism.
- [ ] Drop `DescribeIsRendezvous` and `DescribeHasRecentWrite`, 8 tests?
      Both helpers are fully covered through `idle_entries` and the
      acceptance tests. Kept because they localize a failure to the helper,
      which an acceptance failure cannot.
- [ ] `cli_test.py`'s `CONFIG = replace(DEFAULTS, quarantine_dir=...)` is a
      no-op: `DEFAULTS` already holds that value, so the `replace` reads as
      an override that overrides nothing. Cosmetic.
- [ ] Is `entry_count` worth its cost? It walks a whole batch with `rglob`
      just to print `(N entries)`, against a quarantine last measured at
      3.8G. A feature question, not a simplification.

## claude-code-archeology

- [ ] [todo.kb/2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.md](todo.kb/2026-09-11-000-session-re-entry-tooling-as-jsonl-streams.md)
      -- five jsonl emitters plus jq views replace four transcript decoders
      and two task listers; parts enumerated in the sibling `.kb/`
- [ ] `claude-inventory` can't answer "which sessions did the crash kill,
      and which are worth resuming" -- the 2026-09-23 tmux-crash triage
      (session `452afeb3`) needed an ad-hoc script for three things it lacks
      (`2026-05-19--task-archeology/trash/crash-triage-2026-09-23.py`):
  - [ ] Mark live sessions: `~/.claude/sessions/<pid>.json` maps a pid to a
        `sessionId`, and `/proc/<pid>` says whether it still runs. Without
        this, `--sh` hands back already-resumed sessions as resume commands.
  - [ ] Show resume cost: context at the tip, i.e. the last assistant
        record's `input_tokens` + both `cache_*_input_tokens` on the tip
        chain. It ranged 26k-465k across that one cohort.
  - [ ] Flag an unanswered tip (the last genuine user prompt has no reply),
        filtering task notifications and peer messages. Two of the 26 dead
        sessions held one; neither showed in the label column.
