"""Nag about activity on upstream issue threads I reported to.

Watches the URLs in ~/.config/upstream-replies.txt (one per line, `#`
comments allowed); remembers what has been acknowledged in
~/.local/state/upstream-replies.json. A URL's first sighting is recorded
silently. Prints one line per thread with newer activity; exits 1 when
there is none (grep semantics).

A plain run acknowledges what it prints. `--rc` (for shell startup) does
NOT acknowledge, and rechecks at most every 6 hours, so a reply keeps
nagging until a by-hand run acknowledges it -- missing one printed nag
costs nothing.
"""

import argparse
import json
import sys
import time
from collections.abc import Iterable, Mapping
from pathlib import Path

from .watch import Sighting, acknowledged, add_url, fetch_updated, read_urls, triage

CONFIG = Path.home() / ".config/upstream-replies.txt"
STATE = Path.home() / ".local/state/upstream-replies.json"
RC_INTERVAL_SEC = 6 * 3600


def read_config() -> str:
    return CONFIG.read_text() if CONFIG.exists() else ""


def read_state() -> dict[str, str]:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def write_state(state: dict[str, str]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n")


def checked_recently() -> bool:
    """Whether the state file was touched inside the --rc throttle window."""
    return STATE.exists() and time.time() - STATE.stat().st_mtime < RC_INTERVAL_SEC


def format_news(
    news: Iterable[Sighting], state: Mapping[str, str], rc_mode: bool
) -> str:
    """The nag block for stdout: one line per thread, blank-line terminated so
    it can't run into the next shell prompt. In --rc mode -- where a run
    doesn't self-acknowledge -- adds a line naming the command that will.
    """
    lines = [
        f"UPSTREAM REPLY? {sighting.url}"
        f" -- activity {sighting.updated}, acked {state[sighting.url]}"
        for sighting in news
    ]
    if not lines:
        return ""
    if rc_mode:
        lines.append("(ack: run `upstream-replies` without --rc)")
    return "".join(f"{line}\n" for line in lines) + "\n"


def proc_add(url: str) -> int:
    _ = fetch_updated(url)  # reject unwatchable URLs before writing them down
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(add_url(read_config(), url))
    print(f"watching {url}")
    return 0


def proc_check(rc_mode: bool) -> int:
    if rc_mode and checked_recently():
        return 1

    state = read_state()
    sightings = [Sighting(url, fetch_updated(url)) for url in read_urls(read_config())]
    seeded, news = triage(state, sightings)
    for sighting in seeded:
        print(f"watching {sighting.url} (as of {sighting.updated})", file=sys.stderr)
    print(format_news(news, state, rc_mode), end="")
    # Writing unconditionally also refreshes the mtime the throttle reads.
    write_state(acknowledged(state, seeded if rc_mode else seeded + news))
    return 0 if news else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--rc",
        action="store_true",
        help="shell-startup mode: 6h-throttled, and does not acknowledge",
    )
    subcommands = parser.add_subparsers(dest="command")
    watch = subcommands.add_parser("add", help="watch another issue thread")
    watch.add_argument("url")
    args = parser.parse_args()

    if args.command == "add":
        return proc_add(args.url)
    else:
        return proc_check(args.rc)
