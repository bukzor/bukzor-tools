# bukzor-tools

## bukzor-tmpwatch

Two rulings the owner has not made. Both were raised in the 2026-08-28..31
session and are recorded there: `~/.claude/sessions.kb/penguin.kb/bukzor-tmpwatch-scratch-gc.md`.

- [ ] Should an unreadable root abort the sweep, or be skipped with a warning?
      Today one `PermissionError` ends the run across every root. Aborting is
      loud and never hides a problem; skipping keeps an unattended nightly job
      useful when a single directory goes bad. Raised three times, no ruling.
- [ ] Add a `--porcelain` flat-path output mode? The grouped report states the
      action and root once and indents the names, so reassembling a full path
      needs the root line. The previous one-full-path-per-line form was
      pipeline-shaped. Offered, not ruled on.
