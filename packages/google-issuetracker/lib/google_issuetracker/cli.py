"""Search Google's public issue trackers (Buganizer) anonymously.

One result per line -- "ISSUE-URL  MODIFIED  TITLE" -- newest first;
exit 1 when the search matched nothing (grep semantics).
"""

import argparse

from .buganizer import DEFAULT_HOST, format_row, search


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("query", nargs="+", help="search terms (Buganizer syntax)")
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help="also useful: issues.chromium.org"
    )
    parser.add_argument(
        "--tracker",
        default=None,
        help="tracker-view id, e.g. 157 = Chromium; default: all public trackers",
    )
    parser.add_argument("-n", "--count", type=int, default=25)
    args = parser.parse_args()

    issues = search(" ".join(args.query), args.host, args.tracker, args.count)
    for issue in issues:
        print(format_row(args.host, issue.id, issue.modified, issue.title))
    return 0 if issues else 1
