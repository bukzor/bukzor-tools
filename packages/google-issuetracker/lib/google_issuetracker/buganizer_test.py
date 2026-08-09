import json

import pytest

from .buganizer import build_request, format_row, parse_response

JSON_PREFIX = ")]}'"


def wire(*rows: object) -> str:
    """A server response carrying these issue rows, framed as the real one is."""
    return JSON_PREFIX + json.dumps([[0, 1, 2, 3, 4, 5, [list(rows) or None]]])


def row(issue_id: int, modified: int, title: str) -> list[object]:
    return [None, issue_id, [None, None, None, None, None, title], None, [modified, 0]]


class DescribeBuildRequest:
    def it_puts_the_query_and_count_in_slot_six(self):
        assert build_request("out of puff", None, 50)[6] == ["out of puff", None, 50]

    def it_omits_the_tracker_filter_by_default(self):
        assert build_request("q", None, 25)[5] is None

    def it_filters_to_one_tracker_view_when_asked(self):
        assert build_request("q", "157", 25)[5] == ["157"]


class DescribeParseResponse:
    def it_reads_id_modified_and_title_from_each_row(self):
        raw = wire(row(544148694, 1786000000, "balloon squeezes Crostini guest"))
        assert parse_response(raw) == [
            (544148694, 1786000000, "balloon squeezes Crostini guest")
        ]

    def it_returns_nothing_when_the_search_matched_nothing(self):
        assert parse_response(wire()) == []

    def it_raises_on_a_server_error_rather_than_looking_empty(self):
        """A conversion error parses as valid JSON; silence here reads as no matches."""
        error = JSON_PREFIX + json.dumps({"message": "Trouble converting POST body"})
        with pytest.raises(SystemExit, match="Trouble converting POST body"):
            _ = parse_response(error)

    def it_rejects_a_response_missing_the_anti_xssi_prefix(self):
        with pytest.raises(AssertionError):
            _ = parse_response("[[]]")


class DescribeFormatRow:
    def it_renders_url_date_and_title(self):
        assert format_row("issuetracker.google.com", 544148694, 1786000000, "t") == (
            "https://issuetracker.google.com/issues/544148694  2026-08-06  t"
        )
