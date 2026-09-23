---
measured: 2026-09-23
session: 32e41eca
---

# jq's date parsing drops UTC offsets

In jq 1.8.2, `fromdateiso8601` rejects `2026-09-23T13:09:35-05:00`
outright; it accepts only a trailing `Z`. `strptime("%Y-%m-%dT%H:%M:%S%z")
| mktime` accepts it and silently ignores the offset: it returns
1790168975, which is the wall-clock time read as if it were UTC, not
1790186975. A stream whose times are offset-bearing strings leaves every
time computation to a hand-written parse; streams carry integers instead.
