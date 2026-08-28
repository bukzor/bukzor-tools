"""Clear a subagent's stopped-by-user lock so SendMessage can resume it.

A user-stopped subagent is held down by `"stoppedByUser": true` in its
`agent-<id>.meta.json` -- that flag alone is what the SendMessage
refusal reads. This removes the flag (backing the meta.json up first)
and diagnoses the transcript tail, since a stop usually also leaves
poison there; a dirty tail wants `claude-jsonl-truncate` before resume.
See `Skill(claude-code-surgery)`.

Usage:
    claude-agent-unstop <agent-...jsonl | agent-...meta.json>
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from . import session as session_mod
from .truncate import dangling_tool_uses


def meta_path_for(path: Path) -> Path:
    """The meta.json for an agent transcript; a meta.json passes through.

    >>> meta_path_for(Path("subagents/agent-x.jsonl")).name
    'agent-x.meta.json'
    >>> meta_path_for(Path("subagents/agent-x.meta.json")).name
    'agent-x.meta.json'
    """
    if path.name.endswith(".meta.json"):
        return path
    assert path.suffix == ".jsonl", path
    return path.with_name(path.name.removesuffix(".jsonl") + ".meta.json")


def unstopped(meta: dict[str, object]) -> tuple[dict[str, object], bool]:
    """Pure: the meta without its stop flag, and whether anything changed.

    >>> unstopped({"stoppedByUser": True, "agentId": "x"})
    ({'agentId': 'x'}, True)
    >>> unstopped({"agentId": "x"})
    ({'agentId': 'x'}, False)
    """
    kept = {k: v for k, v in meta.items() if k != "stoppedByUser"}
    return kept, kept != meta


def report_tail(jsonl: Path) -> None:
    """Say whether the transcript tail would poison a resume."""
    if not jsonl.exists():
        print(
            f"no transcript beside it ({jsonl.name}); tail unchecked", file=sys.stderr
        )
        return
    sess = session_mod.load(jsonl)
    dangling = dangling_tool_uses(sess.nodes)
    if dangling:
        print(
            f"tail is dirty (dangling tool_use {sorted(dangling)});"
            " run claude-jsonl-truncate --in-place before resuming"
            " (the agent is bound to this file's id)",
            file=sys.stderr,
        )
    else:
        print("tail is clean", file=sys.stderr)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="agent transcript or its meta.json")
    args = p.parse_args()

    meta_path = meta_path_for(args.path)
    meta: dict[str, object] = json.loads(meta_path.read_text())
    assert isinstance(meta, dict), meta_path
    kept, changed = unstopped(meta)
    if not changed:
        print(f"not stopped: {meta_path} has no stoppedByUser flag", file=sys.stderr)
    else:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = meta_path.with_name(f"{meta_path.name}.pre-unstop.{stamp}")
        shutil.copy2(meta_path, backup)
        tmp = meta_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(kept, indent=2) + "\n")
        tmp.replace(meta_path)
        print(f"unstopped: {meta_path} (backup: {backup.name})", file=sys.stderr)

    report_tail(
        meta_path.with_name(meta_path.name.removesuffix(".meta.json") + ".jsonl")
    )
    return 0
