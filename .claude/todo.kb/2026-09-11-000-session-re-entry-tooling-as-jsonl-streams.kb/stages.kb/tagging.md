---
status: exists
effort-sweh: 0
---

# tagging

Map: takes file paths, emits one JSON object per line of each file with
the file's path and line number attached. This is what lets a map stage's
output be concatenated without losing origin, and it is `rg --json '^'`
with no code to write.

```
rg --json '^' -- FILES | jq -c 'select(.type=="match")
  | {file:.data.path.text, line:.data.line_number}
  + (.data.lines.text // (.data.lines.bytes|@base64d) | fromjson)'
```

Measured 2026-09-11: a full day of transcripts, nine files and twelve
megabytes, tagged and decoded in under half a second; output is grouped
per file, never interleaved ([rg-json-groups]). Three constraints bind the
command as written: the pattern must be `^` and never the empty string
([empty-pattern]), `--` must precede the files ([dash-slugs]), and a
non-UTF-8 line arrives as `bytes` ([bytes-fallback]).

For markdown the same stage with a different pattern is
[checkbox-extraction], and with `-U` it hands [frontmatter-extraction] its
block.

[rg-json-groups]: ../discovered-constraints.kb/rg-json-groups-output-per-file.md
[empty-pattern]: ../discovered-constraints.kb/empty-pattern-matches-every-byte.md
[dash-slugs]: ../discovered-constraints.kb/project-slugs-begin-with-a-dash.md
[bytes-fallback]: ../discovered-constraints.kb/non-utf8-lines-arrive-as-bytes.md
[checkbox-extraction]: ./checkbox-extraction.md
[frontmatter-extraction]: ./frontmatter-extraction.md
