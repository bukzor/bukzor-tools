"""dmesg -H-style timestamps for a run of chronologically-ordered rows.

An absolute, dated, zoned anchor whenever the display-minute changes from
the previous row; otherwise a compact signed delta (seconds, millisecond
precision) from that previous row. Compact most of the time, but never
more than a display-minute away from an unambiguous stamp -- and clustered
rows (five files a power outage cut off within two seconds of each other)
show up as a run of near-zero deltas instead of requiring the reader to
diff two absolute stamps by hand.

A header-only zone note does not survive being excerpted: piping
`claude-jsonl-display` through `tail` silently drops everything but its
last line, and the same fate awaits a "# times: local, ..." header cut off
a `claude-branch-list` tail. So the zone repeats on every anchor, not just
once at the top.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, tzinfo

INNER_WIDTH = len("Aug09 23:59 -0500")


@dataclass
class Clock:
    """Stateful: call `.stamp(epoch_ns)` once per row, in chronological order.

    Rows need not be increasing -- `claude-inventory` lists newest first,
    so its deltas are negative, which is itself the signal: a run of
    near-zero negative deltas is a cluster, not two unrelated sessions
    that happen to share a minute.

    Bracketed, like `dmesg -H`'s own `[Aug09 23:59]` / `[  +0.221957]` --
    a fixed-width delimiter a reader's eye locks onto once and then just
    scans down, rather than re-parsing "is this text or a timestamp" on
    every row.

    >>> from datetime import timezone, timedelta
    >>> tz = timezone(timedelta(hours=-5))
    >>> c = Clock(tz)
    >>> c.stamp(1786337960_368723587)
    '[Aug09 23:59 -0500]'
    >>> c.stamp(1786337960_589723587)
    '[           +0.221]'
    >>> c.stamp(1786337960_368723587 + 9 * 3600 * 1_000_000_000)
    '[Aug10 08:59 -0500]'
    """

    tz: tzinfo
    _last_minute: str | None = field(default=None, repr=False, compare=False)
    _last_ns: int | None = field(default=None, repr=False, compare=False)

    def stamp(self, epoch_ns: int) -> str:
        dt = datetime.fromtimestamp(epoch_ns / 1_000_000_000, self.tz)
        minute = dt.strftime("%Y-%m-%d %H:%M")
        if minute != self._last_minute:
            out = dt.strftime("%b%d %H:%M %z")
        else:
            assert self._last_ns is not None
            delta_ms = round((epoch_ns - self._last_ns) / 1_000_000)
            sign = "-" if delta_ms < 0 else "+"
            out = f"{sign}{abs(delta_ms) / 1000:.3f}"
        self._last_minute = minute
        self._last_ns = epoch_ns
        return f"[{out:>{INNER_WIDTH}}]"
