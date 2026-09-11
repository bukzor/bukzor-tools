# Retirements

One file per existing artifact the design supersedes: a script, a module,
or a function that duplicates a stage or a view. Each names the artifact,
what it does today, and the part that replaces it.

## What belongs here

Code that exists on 2026-09-11 and would be deleted or reduced to a call
once its replacement lands. Frontmatter (schema:
`../retirements.jsonschema.yaml`) carries the path and the replacing
parts, so the sweep of what remains to retire is `md-frontmatter`.

## What does not belong

Code that survives as the implementation of a stage; that is named in the
stage's file. Code unrelated to this design, however duplicated.

## When to add

When a stage or command file's `replaces:` names a path with no file here.
When the retirement is done, say so in the body and keep the file.
