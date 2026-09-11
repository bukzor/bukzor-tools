# Discovered constraints

Measured facts about `rg`, `jq`, git, and the transcript format that bound
the design. Facts, not choices: each was observed by running a command,
and the frontmatter names the transcript where the run can be re-read.

## What belongs here

A behaviour the design must respect or may rely on, with the command that
showed it and the number it produced. Enabling facts belong as much as
gotchas; "every talk record carries its session id" is what licenses
concatenation.

## What does not belong

Decisions made in light of a constraint; those are stage or open-question
files. Beliefs not yet measured; write the measurement first.

## When to add

When building a part reveals a behaviour the design did not know, or when
a stated constraint turns out wrong, in which case correct the file and
its name in the same pass.
