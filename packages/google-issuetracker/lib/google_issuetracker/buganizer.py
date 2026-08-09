"""Anonymous read access to Google's public issue trackers (Buganizer).

issuetracker.google.com and issues.chromium.org are the same backend
behind different tracker views. The official API is partner-allowlist
only; this endpoint needs no auth at all.

Wire format is positional JSPB, reverse-engineered 2026-08-09 from a
DevTools capture: request slot 5 is an optional tracker-view filter,
slot 6 is [query, page_token, count]. Named-JSON bodies are rejected by
the server, so the positional shape is the only shape.
"""

import datetime
import json
import urllib.request
from typing import NamedTuple

JSON_PREFIX = ")]}'"  # anti-XSSI armor on every response
DEFAULT_HOST = "issuetracker.google.com"


class Issue(NamedTuple):
    id: int
    modified: int  # unix seconds
    title: str


def build_request(query: str, tracker: str | None, count: int) -> list[object]:
    return [
        None,
        None,
        None,
        None,
        None,
        [tracker] if tracker else None,
        [query, None, count],
    ]


def parse_response(raw: str) -> list[Issue]:
    """Issues in the server's order (newest first); empty when none matched."""
    assert raw.startswith(JSON_PREFIX), raw[:80]
    data = json.loads(raw.removeprefix(JSON_PREFIX))
    if isinstance(data, dict):
        # Server-side validation errors arrive as a JSON object and would
        # otherwise parse cleanly into zero results -- silent wrong answers.
        raise SystemExit(f"tracker error: {data}")
    rows = data[0][6][0]
    if rows is None:
        return []
    else:
        return [Issue(row[1], row[4][0], row[2][5]) for row in rows]


def format_row(host: str, issue_id: int, modified: int, title: str) -> str:
    when = datetime.date.fromtimestamp(modified).isoformat()
    return f"https://{host}/issues/{issue_id}  {when}  {title}"


def fetch(host: str, body: list[object]) -> str:
    request = urllib.request.Request(
        f"https://{host}/action/issues/list",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (google-issuetracker)",
        },
    )
    with urllib.request.urlopen(request) as response:
        return response.read().decode()


def search(
    query: str,
    host: str = DEFAULT_HOST,
    tracker: str | None = None,
    count: int = 25,
) -> list[Issue]:
    return parse_response(fetch(host, build_request(query, tracker, count)))
