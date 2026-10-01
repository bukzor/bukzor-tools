# Where the jq view files live

Every command is `emitter | jq -f VIEW`, so the views need a home an
agent can name from prose and `ls` to discover.

Ruled: views live under `$XDG_CONFIG_HOME/claude-code-archeology/views/`,
and the package's default views appear there as symlinks. The set of views
is computed, the directory is made to match it, and then what is literally
on disk is used: new defaults get a link, a real file is an override and is
never replaced, dead links are removed. [!@bukzor] 2026-10-01. One
directory serves both readers -- shell lines name plain paths, `ls -l` shows
defaults as links and overrides as files -- and no install step can fall
behind the package.

## Reconciling the directory

Refinements to the ruling. [!DRAFT] 2026-10-01.

- Ownership is by target, not by file type: a link is the package's when
  its target path ends in `claude_code_archeology/views/<name>`. An
  override may itself be a symlink (into a dotfiles repo, say), and a
  foreign link is never touched, dead or alive.
- An owned link is re-pointed when it does not aim at the current default,
  and removed when its name is no longer a default. A dead-link rule alone
  misses a link into an old install location that still exists.
- The package's user-facing commands reconcile before running, and one
  command does it alone for bare `jq -f` use. Stages never do: under
  `rg --pre` the decoder runs once per file.
- A link that already exists counts as success, so concurrent commands do
  not race.
