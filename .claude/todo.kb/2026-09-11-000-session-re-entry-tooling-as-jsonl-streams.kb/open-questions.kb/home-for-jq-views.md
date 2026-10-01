# Where the jq view files live

Every command is `emitter | jq -f VIEW`, so the views need a home an
agent can name from prose and `ls` to discover.

Ruled: views live under `$XDG_CONFIG_HOME/claude-code-archeology/views/`,
and the package's default views appear there as if symlinked in, literally
or conceptually. [!@bukzor] 2026-10-01. One directory serves both readers:
the user's own and edited views sit beside the defaults, under the
configuration root every other tool already uses.

## Open: literal links or a lookup

Candidates:

- Literal: an idempotent `claude-code-archeology-install` links each
  default into the directory, never replacing a regular file (that is a
  user override) and removing links whose target is gone. Shell lines
  name a plain path; `ls -l` shows defaults as links and overrides as
  files; the editable install makes an edited default live at once. A
  default added later appears only after a re-run.
  `bukzor-tmpwatch-install` already links package files into
  `$XDG_CONFIG_HOME` this way.
- Conceptual: a resolver searches the user directory, then the package's
  defaults. No install step and new defaults appear at once, but every
  shell line goes through the resolver, and `ls` of the directory shows
  only overrides.

Agent recommendation, 2026-10-01: literal. The ruling's point is a
directory to `ls` and name in a shell line, and only literal links keep
both; one directory also serves as a single `jq -L` root, if views come to
share a module.
