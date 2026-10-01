# Where the jq view files live

Every question is `emitter | claude-jq PROGRAM`, so the views need a home
an agent can name from prose and `ls` to discover.

Ruled: a view is a `jq` module, one `.jq` file defining one filter of the
same name. Views are found by search path, user directory first, then the
package's defaults, and nothing is ever linked, synced, or written.
[!@bukzor] 2026-10-01. The three parts of the machinery share one name
because they change together:

- `$XDG_CONFIG_HOME/claude-code-archeology/jq/` holds the user's views; a
  file named like a default replaces it.
- `claude_code_archeology/jq/` in the package holds the defaults.
- `claude-jq` is `jq` with those two directories on its library path and
  every view already in scope, so a view is called by its bare name:
  `claude-jsonl-records | claude-jq 'sessions' -s`.

## Mechanism

[!DRAFT] 2026-10-01. Measured on jq 1.8.2 in session 32e41eca.

- `jq` has no option to prepend an `include`. Its only prelude is
  `$HOME/.jq`, one file under the real home directory, and it brings plain
  definitions into scope but not the names of anything it `include`s.
  `-L` takes only a directory: given a file, `jq` accepts it silently and
  defines nothing.
- `include` does not re-export: a module that includes others leaves their
  names undefined for whoever includes it, so one umbrella module cannot
  stand in for the directory.
- `claude-jq` therefore prepends one `include "<name>";` for each view
  name the program text mentions as a word, then `exec`s `jq -L <user>
  -L <package>`. Naming only the views a program mentions follows from
  `jq` compiling every module it includes: a half-written file in the
  user directory then fails only programs that name it. Not measured.
  The first directory holding a name wins. A user's
  `sessions.jq` replaces the default for a top-level call and for every
  default view that includes it.
- The program is `claude-jq`'s first argument and `jq` options follow it,
  so the wrapper never has to tell a program from an option's value.
- The prelude goes on its own line so columns in `jq` errors stay the
  program's; line numbers are one high.
- `ls` of the user directory shows only overrides, so `claude-jq` with no
  arguments lists every view: name, one-line summary, input form, and the
  directory it came from.
