#!/usr/bin/env python3
"""evallib.py — shared parsing for the eval checkers under tests/evals/.

A checker asserts mechanism over two inputs: the `claude -p --output-format stream-json`
transcript (tool_use / tool_result blocks, in order) and, for ZotPilot skills, the mock's
log (`CALL <tool> <args>` / `WRITE <tool> <args> -> <result>` lines). Nothing here judges
output quality. The three checkers that predate this file parse the transcript themselves and
are left as they are.
"""
from __future__ import annotations
import json, pathlib, re, sys

_MOCK = re.compile(r"^(CALL|WRITE) (\w+) (\{.*?\})(?: -> (\{.*\}))?$")


def _messages(path):
    for line in pathlib.Path(path).read_text().splitlines():
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = m.get("message") if isinstance(m, dict) else None
        if isinstance(msg, dict) and isinstance(msg.get("content"), list):
            yield msg["content"]


def tool_uses(path) -> list[tuple[str, dict, str]]:
    """(name, input, id) for every tool_use block, in transcript order."""
    out = []
    for content in _messages(path):
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                out.append((b.get("name") or "", b.get("input") or {}, b.get("id") or ""))
    return out


def tool_results(path) -> dict[str, tuple[str, bool]]:
    """tool_use_id -> (text, is_error) for every tool_result block."""
    out = {}
    for content in _messages(path):
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                c = b.get("content")
                if isinstance(c, list):
                    text = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                else:
                    text = str(c or "")
                out[b.get("tool_use_id") or ""] = (text, bool(b.get("is_error")))
    return out


def mock_calls(path) -> list[tuple[str, str, dict, dict | None]]:
    """(kind, tool, args, result) per mock log line; result is None on CALL lines."""
    out = []
    for line in pathlib.Path(path).read_text().splitlines():
        w = _MOCK.match(line.strip())
        if w:
            out.append((w.group(1), w.group(2), json.loads(w.group(3)),
                        json.loads(w.group(4)) if w.group(4) else None))
    return out


def first(uses, pred) -> int | None:
    """Index of the first tool_use for which pred(name, input) holds."""
    return next((i for i, (n, a, _) in enumerate(uses) if pred(n, a)), None)


def bash(uses) -> list[str]:
    return [a.get("command", "") for n, a, _ in uses if n == "Bash"]


def agent(uses, subagent_type) -> int | None:
    return first(uses, lambda n, a: n == "Agent" and a.get("subagent_type") == subagent_type)


def finish(name: str, fails: list[str], summary: str):
    print(summary)
    for f in fails:
        print(f"  FAIL {f}")
    print(f"{name}: " + ("PASS" if not fails else "FAIL"))
    sys.exit(1 if fails else 0)
