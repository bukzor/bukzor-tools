"""Who authored a user record: a person, another agent, or the harness.

`is_user_text` separates a user message from a tool result. That is not
enough to answer "what did someone actually say", because Claude Code also
speaks in `type: user` records -- compaction summaries, skill preambles,
slash-command wrappers, interrupt notices -- and it splices spans into
otherwise-typed prompts.

The distinction that matters is *composed message* versus *machine output*.
A subagent's opening prompt, a message relayed from a peer session, and a
person's prompt are all composed messages; tool results, command output and
harness notices are not. Authorship is then a separate question, and the
answer is `user` or `agent` -- an agent briefing a subagent is typing, just
not with hands.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .format_short import content_blocks
from .session import Node, is_user_text

RELAYED_SPANS = re.compile(
    r"<cross-session-message\b[^>]*>(.*?)</cross-session-message>"
    r"|<task-notification\b[^>]*>.*?<result>(.*?)</result>",
    re.DOTALL,
)
"""Message content another agent composed, arriving inside a harness envelope.

A peer session's `SendMessage` body and a finished subagent's `<result>` are
both somebody's writing; the envelopes around them -- task ids, socket paths,
status fields -- are not.
"""

HARNESS_SPANS = re.compile(
    r"<(system-reminder|local-command-caveat|local-command-stdout"
    r"|local-command-stderr|command-name|command-message|command-args"
    r"|command-contents|user-prompt-submit-hook|task-notification"
    r"|bash-stdout|bash-stderr)"
    r"\b[^>]*>.*?</\1>",
    re.DOTALL,
)
"""Spans the CLI splices around, or instead of, composed text."""

UNWRAPPED_SPANS = re.compile(r"<(bash-input)\b[^>]*>(.*?)</\1>", re.DOTALL)
"""Spans whose tags are the CLI's but whose contents were typed.

`!ls` in the prompt box is stored as `<bash-input>ls</bash-input>` beside a
`<bash-stdout>` sibling: the command is the person's, the output is not.
"""

HARNESS_OPENERS = (
    "[Request interrupted",
    "Caveat: The messages below",
    "This session is being continued",
    "Base directory for this skill:",
    "CLAUDE.md defines your task",
    "Your task is to create a detailed summary",
)
"""Openers of whole user records that nobody composed as a message.

Kept as prefixes rather than exact strings because each continues into
session-specific text. `isMeta` and `isCompactSummary` already mark most
injected records; these are the ones carrying neither flag.
"""

USER = "user"
AGENT = "agent"


@dataclass(frozen=True)
class Typed:
    """Composed message text, and which kind of author composed it."""

    author: str
    text: str


def message_text(node: Node) -> str:
    """The text blocks of a record, joined -- no thinking, tools or results.

    >>> message_text(Node(0, {"type": "user", "message": {"content": "hi"}}))
    'hi'
    >>> message_text(Node(0, {"type": "user", "message": {"content": [
    ...     {"type": "text", "text": "a"}, {"type": "text", "text": "b"},
    ... ]}}))
    'a\\nb'
    >>> message_text(Node(0, {"type": "user", "message": {"content": [
    ...     {"type": "tool_result", "content": "out"},
    ... ]}}))
    ''
    """
    return "\n".join(
        text
        for block in content_blocks(node.record)
        if block.get("type") == "text"
        if isinstance(text := block.get("text"), str)
        if text
    )


def relayed_text(text: str) -> str:
    """What another agent composed, unwrapped from its harness envelope.

    >>> relayed_text('a<cross-session-message from="x">hello</cross-session-message>')
    'hello'
    >>> relayed_text("<task-notification><id>7</id><result>done</result></task-notification>")
    'done'
    >>> relayed_text("just my own words")
    ''
    """
    found = (
        match.group(1) or match.group(2) or "" for match in RELAYED_SPANS.finditer(text)
    )
    return "\n".join(part for match in found if (part := match.strip()))


def strip_harness_spans(text: str) -> str:
    """Remove the CLI's spliced-in spans, leaving what was composed around them.

    >>> strip_harness_spans("do it<system-reminder>be careful</system-reminder>")
    'do it'
    >>> strip_harness_spans("<command-name>/model</command-name> use opus")
    'use opus'
    >>> strip_harness_spans("<bash-input>ls</bash-input><bash-stdout>a b</bash-stdout>")
    'ls'
    >>> strip_harness_spans("nothing to strip")
    'nothing to strip'
    """
    return UNWRAPPED_SPANS.sub(r"\2", HARNESS_SPANS.sub("", text)).strip()


def typed(node: Node) -> Typed | None:
    """The composed message in this record, with its author, else None.

    A prompt that arrived with a system-reminder attached still counts --
    minus the reminder. A record that is nothing but harness output does not.

    Sidechain records are agent-authored: a subagent's opening message is the
    prompt its caller wrote, and a peer's relayed message is that peer's
    writing. Both are messages somebody composed, so both count; only the
    author differs.

    >>> typed(Node(0, {"type": "user", "message": {"content": "do it"}}))
    Typed(author='user', text='do it')
    >>> typed(Node(0, {"type": "user", "isSidechain": True,
    ...     "message": {"content": "You are a subagent. Do X."}}))
    Typed(author='agent', text='You are a subagent. Do X.')
    >>> typed(Node(0, {"type": "user", "message": {"content":
    ...     'Another Claude session sent a message:'
    ...     '<cross-session-message from="x">ship it</cross-session-message>'}}))
    Typed(author='agent', text='ship it')
    >>> typed(Node(0, {"type": "user", "message": {"content":
    ...     "do it<system-reminder>be careful</system-reminder>"}}))
    Typed(author='user', text='do it')
    >>> typed(Node(0, {"type": "user", "isMeta": True,
    ...     "message": {"content": "# project instructions"}})) is None
    True
    >>> typed(Node(0, {"type": "user", "message":
    ...     {"content": "[Request interrupted by user]"}})) is None
    True
    >>> typed(Node(0, {"type": "user", "message": {"content": [
    ...     {"type": "tool_result", "content": "out"},
    ... ]}})) is None
    True
    >>> typed(Node(0, {"type": "assistant",
    ...     "message": {"content": "sure"}})) is None
    True
    """
    if not is_user_text(node):
        return None
    if node.record.get("isMeta") or node.record.get("isCompactSummary"):
        return None

    raw = message_text(node)
    if relayed := relayed_text(raw):
        return Typed(AGENT, relayed)

    text = strip_harness_spans(raw)
    if not text or text.startswith(HARNESS_OPENERS):
        return None
    return Typed(AGENT if node.record.get("isSidechain") else USER, text)
