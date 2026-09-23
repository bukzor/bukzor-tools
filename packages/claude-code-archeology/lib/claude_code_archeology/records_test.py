"""What the doctests can't reach: behavior that spans records.

A decoder reads records one at a time, but two of its outputs depend on
records it saw earlier: the tool a result answers, and the time of a record
that carries none.
"""

from .records import records
from .session import Node, Record


def nodes(*recs: Record) -> list[Node]:
    return [Node(i, rec) for i, rec in enumerate(recs, 1)]


def talk(session: str, stamp: str, **fields: object) -> Record:
    return {"sessionId": session, "timestamp": stamp, **fields}


class DescribeRecords:
    def it_names_the_tool_a_result_answers(self):
        stream = nodes(
            talk(
                "s",
                "2026-09-10T15:30:37.005Z",
                type="assistant",
                message={"content": [{"type": "tool_use", "id": "t1", "name": "Bash"}]},
            ),
            talk(
                "s",
                "2026-09-10T15:30:38.000Z",
                type="user",
                message={
                    "content": [
                        {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}
                    ]
                },
            ),
        )
        assert [(r["type"], r["tool"]) for r in records(stream)] == [
            ("tool-use", "Bash"),
            ("tool-result", "Bash"),
        ]

    def it_gives_an_untimed_record_its_sessions_previous_time(self):
        stream = nodes(
            talk("s", "2026-09-10T15:30:37.005Z", type="system", subtype="x"),
            {"sessionId": "s", "type": "ai-title", "aiTitle": "a title"},
        )
        assert [r["time_ns"] for r in records(stream)] == [
            1789_054_237_005_000_000,
            1789_054_237_005_000_000,
        ]

    def it_gives_a_leading_untimed_record_its_sessions_next_time(self):
        stream = nodes(
            {"sessionId": "s", "type": "custom-title", "customTitle": "named"},
            talk("s", "2026-09-10T15:30:37.005Z", type="system", subtype="x"),
        )
        assert [(r["type"], r["time_ns"]) for r in records(stream)] == [
            ("title", 1789_054_237_005_000_000),
            ("system", 1789_054_237_005_000_000),
        ]

    def it_never_lends_one_sessions_time_to_another(self):
        """Concatenated transcripts arrive back to back on one stdin."""
        stream = nodes(
            talk("a", "2026-09-10T15:30:37.005Z", type="system", subtype="x"),
            {"sessionId": "b", "type": "ai-title", "aiTitle": "b's title"},
            talk("b", "2026-09-11T00:00:00.000Z", type="system", subtype="x"),
        )
        assert [(r["session"], r["time_ns"]) for r in records(stream)] == [
            ("a", 1789_054_237_005_000_000),
            ("b", 1789_084_800_000_000_000),
            ("b", 1789_084_800_000_000_000),
        ]

    def it_drops_a_session_that_never_says_when(self):
        stream = nodes({"sessionId": "s", "type": "ai-title", "aiTitle": "orphan"})
        assert list(records(stream)) == []
