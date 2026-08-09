"""Which watched issue threads moved since I last acknowledged them.

State maps issue URL -> the activity timestamp already seen, ISO-8601
UTC. That is GitHub's `updated_at` format verbatim, and Buganizer's
epoch seconds are converted into it, so the two compare as plain
strings.
"""

import re
import subprocess
import time
from collections.abc import Iterable, Mapping
from typing import NamedTuple

from google_issuetracker.buganizer import search

GITHUB = re.compile(r"https://github\.com/([^/]+)/([^/]+)/issues/(\d+)")
BUGANIZER = re.compile(
    r"https://(issuetracker\.google\.com|issues\.chromium\.org)/issues/(\d+)"
)


class Sighting(NamedTuple):
    url: str
    updated: str


class Triage(NamedTuple):
    seeded: list[Sighting]  # first sighting -- record it, don't nag about it
    news: list[Sighting]


def read_urls(text: str) -> list[str]:
    lines = (line.partition("#")[0].strip() for line in text.splitlines())
    return [line for line in lines if line]


def add_url(text: str, url: str) -> str:
    if url in read_urls(text):
        return text
    else:
        return text + ("" if text.endswith("\n") or not text else "\n") + url + "\n"


def triage(state: Mapping[str, str], sightings: Iterable[Sighting]) -> Triage:
    seeded: list[Sighting] = []
    news: list[Sighting] = []
    for sighting in sightings:
        acked = state.get(sighting.url)
        if acked is None:
            seeded.append(sighting)
        elif sighting.updated > acked:
            news.append(sighting)
    return Triage(seeded, news)


def acknowledged(
    state: Mapping[str, str], sightings: Iterable[Sighting]
) -> dict[str, str]:
    return dict(state) | {sighting.url: sighting.updated for sighting in sightings}


def fetch_github_updated(owner: str, repo: str, number: str) -> str:
    process = subprocess.run(
        ["gh", "api", f"repos/{owner}/{repo}/issues/{number}", "-q", ".updated_at"],
        check=True,
        capture_output=True,
        text=True,
    )
    return process.stdout.strip()


def fetch_buganizer_updated(host: str, issue_id: str) -> str:
    issues = search(f"id:{issue_id}", host, count=2)
    matches = [issue for issue in issues if str(issue.id) == issue_id]
    assert matches, (issue_id, issues)
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(matches[0].modified))


def fetch_updated(url: str) -> str:
    if match := GITHUB.match(url):
        owner, repo, number = match.groups()
        return fetch_github_updated(owner, repo, number)
    elif match := BUGANIZER.match(url):
        host, issue_id = match.groups()
        return fetch_buganizer_updated(host, issue_id)
    else:
        raise SystemExit(f"unsupported issue URL: {url}")
