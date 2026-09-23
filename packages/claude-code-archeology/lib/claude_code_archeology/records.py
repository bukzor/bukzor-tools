"""The records stream: one flat JSON line per transcript record.

The one place the transcript format is understood; every other question is a
`jq` filter over this stream. The raw record kinds collapse to nine
`type`s, text arrives decoded and joined, and time is an integer of
nanoseconds since the epoch in `time_ns`, which `jq` compares exactly where
it cannot parse a zoned date string.

Usage:
    claude-jsonl-records < TRANSCRIPT.jsonl...
    rg --json --pre claude-jsonl-records '^' -- TRANSCRIPT.jsonl...
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .format_short import content_blocks, result_text
from .provenance import USER, message_text, strip_harness_spans, typed
from .session import JsonValue, Node, Record, parse_jsonl

Line = dict[str, JsonValue]

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

TITLE_KEYS = {
    "custom-title": "customTitle",
    "agent-name": "agentName",
    "ai-title": "aiTitle",
}

DROPPED = frozenset(
    {
        "agent-color",
        "agent-setting",
        "atis-latch",
        "bridge-session",
        "cost-state",
        "file-history-delta",
        "file-history-snapshot",
        "fork-context-ref",
        "last-prompt",
        "mode",
        "permission-mode",
        "queue-operation",
    }
)
"""Raw kinds that carry no session content. `last-prompt` repeats a user
record; `queue-operation` repeats the `queued_command` attachment."""


COMMAND = re.compile(
    r"\A\s*(?=<command-(?:name|message)>).*?"
    r"<command-name>(?P<name>.*?)</command-name>"
    r"(?:.*?<command-args>(?P<args>.*?)</command-args>)?",
    re.DOTALL,
)
"""A slash command as the harness wraps it: the wrapper is the harness's,
the name and arguments are what the person typed."""


@dataclass(frozen=True)
class Decoded:
    type: str
    text: str
    tool: str | None = None


def time_ns_of(stamp: str) -> int:
    """A record's ISO timestamp as integer nanoseconds since the epoch.

    Exact: no float passes through, so equal instants compare equal.

    >>> time_ns_of("2026-09-10T15:30:37.005Z")
    1789054237005000000
    """
    return (datetime.fromisoformat(stamp) - EPOCH) // timedelta(microseconds=1) * 1000


def block_text(block: Record) -> str:
    """The text a person would read or search for in one content block.

    >>> block_text({"type": "text", "text": "answer"})
    'answer'
    >>> block_text({"type": "thinking", "thinking": "hmm"})
    'hmm'
    >>> block_text({"type": "tool_use", "name": "Bash", "input": {"command": "ls é"}})
    '{"command": "ls é"}'
    >>> block_text({"type": "tool_result", "content": "out"})
    'out'
    >>> block_text({"type": "image"})
    ''
    """
    match block.get("type"):
        case "text":
            return block.get("text") or ""
        case "thinking":
            return block.get("thinking") or ""
        case "tool_use":
            return json.dumps(block.get("input") or {}, ensure_ascii=False)
        case "tool_result":
            return result_text(block)
        case _:
            return ""


def joined_text(blocks: Iterable[Record]) -> str:
    return "\n".join(text for block in blocks if (text := block_text(block)))


def typed_command(text: str) -> str | None:
    """The slash command a harness wrapper records, as it was typed.

    >>> typed_command("<command-name>/model</command-name>"
    ...     "<command-message>model</command-message>"
    ...     "<command-args>opus</command-args>")
    '/model opus'
    >>> print(typed_command("mention <command-name>/x</command-name> later"))
    None
    """
    found = COMMAND.match(text)
    return f"{found['name']} {found['args'] or ''}".strip() if found else None


def decode_user(node: Node, tool_names: Mapping[str, str]) -> Decoded:
    """Tool output, a composed message, or text the harness injected.

    A composed message counts as user text when the person typed it, or,
    inside a subagent, when its caller did. A peer's relayed message in the
    main chain is injected: somebody composed it, but not this session's user.

    >>> decode_user(Node(0, {"type": "user", "message": {"content": [
    ...     {"type": "tool_result", "tool_use_id": "t1", "content": "out"},
    ... ]}}), {"t1": "Bash"})
    Decoded(type='tool-result', text='out', tool='Bash')
    >>> decode_user(Node(0, {"type": "user", "message": {"content":
    ...     "do it<system-reminder>be careful</system-reminder>"}}), {})
    Decoded(type='user-text', text='do it', tool=None)
    >>> decode_user(Node(0, {"type": "user", "message": {"content":
    ...     "<command-message>session-start</command-message>\\n"
    ...     "<command-name>/session-start</command-name>\\n"
    ...     "<command-args>focus: x.md</command-args>"}}), {})
    Decoded(type='user-text', text='/session-start focus: x.md', tool=None)
    >>> decode_user(Node(0, {"type": "user", "isSidechain": True,
    ...     "message": {"content": "You are a subagent."}}), {})
    Decoded(type='user-text', text='You are a subagent.', tool=None)
    >>> decode_user(Node(0, {"type": "user", "isCompactSummary": True,
    ...     "message": {"content": "This session is being continued"}}), {})
    Decoded(type='injected', text='This session is being continued', tool=None)
    >>> decode_user(Node(0, {"type": "user", "message": {"content":
    ...     '<cross-session-message from="x">ship it</cross-session-message>'}}), {})
    Decoded(type='injected', text='<cross-session-message from="x">ship it</cross-session-message>', tool=None)
    """
    blocks = content_blocks(node.record)
    first: Record = blocks[0] if blocks else {}
    if first.get("type") == "tool_result":
        return Decoded(
            "tool-result",
            joined_text(blocks),
            tool_names.get(first.get("tool_use_id", "")),
        )
    command = typed_command(message_text(node))
    if command and not node.record.get("isMeta"):
        return Decoded("user-text", command)
    composed = typed(node)
    if composed and (composed.author == USER or node.record.get("isSidechain")):
        return Decoded("user-text", composed.text)
    else:
        return Decoded("injected", message_text(node))


def decode_assistant(record: Record) -> Decoded:
    """Typed by the first content block; text joins every block.

    >>> decode_assistant({"message": {"content": [{"type": "text", "text": "hi"}]}})
    Decoded(type='assistant-text', text='hi', tool=None)
    >>> decode_assistant({"message": {"content": [
    ...     {"type": "thinking", "thinking": "hmm"},
    ...     {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
    ... ]}})
    Decoded(type='thinking', text='hmm\\n{"command": "ls"}', tool='Bash')
    >>> decode_assistant({"message": {"content": [
    ...     {"type": "tool_use", "name": "Read", "input": {}},
    ... ]}})
    Decoded(type='tool-use', text='{}', tool='Read')
    """
    blocks = content_blocks(record)
    first = blocks[0].get("type") if blocks else None
    tool = next((b.get("name") for b in blocks if b.get("type") == "tool_use"), None)
    match first:
        case "text" | None:
            kind = "assistant-text"
        case "thinking":
            kind = "thinking"
        case "tool_use":
            kind = "tool-use"
        case _:
            raise AssertionError(first)
    return Decoded(kind, joined_text(blocks), tool)


def decode_attachment(record: Record) -> Decoded | None:
    """Only a queued command carries session content.

    A prompt typed while the agent was busy is stored nowhere else: no user
    record repeats it.

    >>> decode_attachment({"attachment": {"type": "queued_command",
    ...     "commandMode": "prompt", "prompt": "also do this"}})
    Decoded(type='user-text', text='also do this', tool=None)
    >>> decode_attachment({"attachment": {"type": "queued_command",
    ...     "commandMode": "prompt", "prompt": [
    ...         {"type": "text", "text": "see this"}, {"type": "image"}]}})
    Decoded(type='user-text', text='see this', tool=None)
    >>> decode_attachment({"attachment": {"type": "queued_command",
    ...     "commandMode": "task-notification", "prompt": "<task-notification/>"}})
    Decoded(type='injected', text='<task-notification/>', tool=None)
    >>> print(decode_attachment({"attachment": {"type": "hook_success"}}))
    None
    """
    attachment: Record = record["attachment"]
    if attachment.get("type") != "queued_command":
        return None
    blocks = content_blocks({"message": {"content": attachment["prompt"]}})
    prompt = joined_text(b for b in blocks if b.get("type") == "text")
    if attachment.get("commandMode") == "prompt" and not attachment.get("isMeta"):
        return Decoded("user-text", strip_harness_spans(prompt))
    else:
        return Decoded("injected", prompt)


def decode_system(record: Record) -> Decoded:
    """A compaction boundary, a slash command the CLI ran, or a notice.

    >>> decode_system({"subtype": "compact_boundary",
    ...     "content": "Conversation compacted"})
    Decoded(type='compact', text='Conversation compacted', tool=None)
    >>> decode_system({"subtype": "local_command", "content":
    ...     "<command-name>/status</command-name>\\n"
    ...     "<command-message>status</command-message>\\n"
    ...     "<command-args></command-args>"})
    Decoded(type='user-text', text='/status', tool=None)
    >>> decode_system({"subtype": "away_summary", "content": "Goal: ship it"})
    Decoded(type='system', text='Goal: ship it', tool=None)
    >>> decode_system({"subtype": "turn_duration"})
    Decoded(type='system', text='', tool=None)
    """
    content = record.get("content")
    text = content if isinstance(content, str) else ""
    if record.get("subtype") == "compact_boundary":
        return Decoded("compact", text)
    elif (command := typed_command(text)) and not record.get("isMeta"):
        return Decoded("user-text", command)
    else:
        return Decoded("system", text)


def decode(node: Node, tool_names: Mapping[str, str]) -> Decoded | None:
    """The record's collapsed type and decoded text, or None if it has none.

    >>> decode(Node(0, {"type": "relocated", "relocatedCwd": "/x"}), {})
    Decoded(type='system', text='/x', tool=None)
    >>> decode(Node(0, {"type": "agent-name", "agentName": "cc-thing"}), {})
    Decoded(type='title', text='cc-thing', tool=None)
    >>> print(decode(Node(0, {"type": "mode", "mode": "normal"}), {}))
    None

    A kind this table has not met is dropped with a warning, not raised:
    Claude Code adds kinds often, and one should not blind every consumer.
    """
    record = node.record
    match node.type:
        case "user":
            return decode_user(node, tool_names)
        case "assistant":
            return decode_assistant(record)
        case "system":
            return decode_system(record)
        case "attachment":
            return decode_attachment(record)
        case "relocated":
            return Decoded("system", record["relocatedCwd"])
        case raw if raw in TITLE_KEYS:
            return Decoded("title", record[TITLE_KEYS[raw]])
        case raw if raw in DROPPED:
            return None
        case raw:
            warnings.warn(f"unknown transcript record type {raw!r}, dropped")
            return None


def line(record: Record, decoded: Decoded, time_ns: int) -> Line:
    """One records-stream line.

    >>> line({"sessionId": "s", "uuid": "u", "parentUuid": "p", "cwd": "/x",
    ...     "agentId": "a1", "isSidechain": True,
    ...     "message": {"model": "claude-opus-5"}}, Decoded("thinking", "hmm"), 7)
    {'kind': 'record', 'session': 's', 'uuid': 'u', 'parent': 'p', 'time_ns': 7, 'type': 'thinking', 'text': 'hmm', 'cwd': '/x', 'sidechain': True, 'agent': 'a1', 'model': 'claude-opus-5', 'tool': None}
    >>> line({"sessionId": "s", "relocatedCwd": "/y"}, Decoded("system", "/y"), 7)["cwd"]
    '/y'
    """
    message: Record | None = record.get("message")
    return {
        "kind": "record",
        "session": record["sessionId"],
        "uuid": record.get("uuid"),
        "parent": record.get("parentUuid"),
        "time_ns": time_ns,
        "type": decoded.type,
        "text": decoded.text,
        "cwd": record.get("cwd") or record.get("relocatedCwd"),
        "sidechain": bool(record.get("isSidechain")),
        "agent": record.get("agentId"),
        "model": message.get("model") if isinstance(message, Mapping) else None,
        "tool": decoded.tool,
    }


def tool_uses(record: Record) -> Iterator[tuple[str, str]]:
    for block in content_blocks(record):
        if block.get("type") == "tool_use":
            yield block["id"], block["name"]


def records(nodes: Iterable[Node]) -> Iterator[Line]:
    """Decode records in file order.

    A record with no timestamp takes its session's previous `time_ns`, or
    its next when none came before; a session that never has one is dropped.
    """
    tool_names: dict[str, str] = {}
    last_ns: dict[str, int] = {}
    untimed: defaultdict[str, list[tuple[Record, Decoded]]] = defaultdict(list)
    for node in nodes:
        tool_names.update(tool_uses(node.record))
        decoded = decode(node, tool_names)
        if decoded is None:
            continue
        session: str = node.record["sessionId"]
        if node.timestamp:
            last_ns[session] = time_ns_of(node.timestamp)
        elif session not in last_ns:
            untimed[session].append((node.record, decoded))
            continue
        for record, early in untimed.pop(session, []):
            yield line(record, early, last_ns[session])
        yield line(node.record, decoded, last_ns[session])


def main() -> None:
    """Reads stdin only. Arguments are ignored rather than parsed: `rg --pre`
    passes the path with the same file on stdin, and every path under
    `~/.claude/projects` begins with a dash."""
    for out in records(parse_jsonl(enumerate(sys.stdin, 1))):
        print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
