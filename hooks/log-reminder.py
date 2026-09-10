#!/usr/bin/env python3
"""
Session Log Reminder Hook for Claude Code

A Stop hook that tracks how many responses have passed since
SESSION_REPORT.md was last updated, and nudges Claude to append to it.
**Never blocks** — always exits 0 without writing a `decision` to stdout.
Two advisory triggers (fired at most once per session each):
  1. No SESSION_REPORT.md exists at all.
  2. THRESHOLD responses have passed without it being touched.

Why SESSION_REPORT.md and not a session-log directory: `.claude/rules/logging.md`
defines exactly four artifacts, and a session-log directory under
`quality_reports/` is not among them — an earlier version of this hook nudged
sessions to create one, which meant compaction recovery read a directory
nothing had authority to write. `.claude/rules/session-handoff.md` settles the
direction of the fix: session continuity "is already designed" around
SESSION_REPORT.md and the research journal, and "the fix is not another
document." logging.md §Session Report already mandates appending "at end
of session or before context compression" — exactly this nudge.

Design rationale: a previous version of this hook emitted
{"decision": "block"} to stop Claude mid-turn. That was effective but
disrupted autonomous flows. Reminders are now advisory only — the user
remains responsible for deciding when to write the log.

Output contract (Stop, exit 0): the advisory is JSON on stdout —
`systemMessage` (shown to the user) and `hookSpecificOutput.additionalContext`
(injected into Claude's context). Plain stderr would reach the user but not
Claude, and the format would be undefined. See https://code.claude.com/docs/en/hooks.

Adapted from: https://gist.github.com/michaelewens/9a1bc5a97f3f9bbb79453e5b682df462

Hook Event: Stop

Usage (in .claude/settings.json):
    "Stop": [{ "hooks": [{ "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/log-reminder.py" }] }]
"""

from __future__ import annotations

import json
import sys
import hashlib
from pathlib import Path

THRESHOLD = 50


def get_state_dir() -> Path:
    """Get state directory under ~/.claude/sessions/ keyed by project."""
    import os
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        state_dir = Path.home() / ".claude" / "sessions" / "default"
    else:
        project_hash = hashlib.md5(project_dir.encode()).hexdigest()[:8]
        state_dir = Path.home() / ".claude" / "sessions" / project_hash
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def get_project_dir():
    """Get project directory from stdin JSON or environment."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    # If stop_hook_active, Claude is already continuing from a previous
    # Stop hook block — let it stop this time to avoid infinite loops.
    if hook_input.get("stop_hook_active", False):
        sys.exit(0)

    return hook_input.get("cwd", ""), hook_input


def get_state_path() -> Path:
    """Return the state file path for the current project."""
    return get_state_dir() / "log-reminder-state.json"


def load_state(state_path: Path) -> dict:
    """Load persisted state, or return defaults."""
    try:
        return json.loads(state_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"counter": 0, "last_mtime": 0.0, "reminded": False, "no_log_reminded": False}


def save_state(state_path: Path, state: dict):
    """Persist state to disk."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state))


def find_session_report(project_dir: str) -> tuple[Path | None, float]:
    """Locate SESSION_REPORT.md and return (path, mtime).

    Root first, then `docs/` — research-claude's own CLAUDE.md relocates the
    file to `docs/SESSION_REPORT.md` and gitignores a root copy as a backstop,
    so a root-only lookup would nag forever in the one repo that ships this
    hook. Paper projects keep it at the root and hit the first branch.
    """
    for candidate in (
        Path(project_dir) / "SESSION_REPORT.md",
        Path(project_dir) / "docs" / "SESSION_REPORT.md",
    ):
        if candidate.is_file():
            return candidate, candidate.stat().st_mtime
    return None, 0.0


def main():
    project_dir, hook_input = get_project_dir()
    if not project_dir:
        sys.exit(0)

    state_path = get_state_path()
    state = load_state(state_path)

    latest_log, current_mtime = find_session_report(project_dir)

    # Case 1: No SESSION_REPORT.md exists — advisory reminder on the
    # documented JSON channel, never blocks.
    if latest_log is None:
        if not state.get("no_log_reminded", False):
            state["no_log_reminded"] = True
            save_state(state_path, state)
            msg = (
                "[session-log] No SESSION_REPORT.md yet. Consider creating it "
                "with the header .claude/rules/logging.md specifies "
                "(`# Session Report — [Project Name]`) and appending this "
                "session's operations, decisions and results."
            )
            print(json.dumps({
                "hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": msg},
                "systemMessage": msg,
            }))
        sys.exit(0)

    # Case 2: Log was updated since last check — reset everything
    if current_mtime != state["last_mtime"]:
        state = {"counter": 0, "last_mtime": current_mtime, "reminded": False, "no_log_reminded": False}
        save_state(state_path, state)
        sys.exit(0)

    # Case 3: Log not updated — increment counter
    state["counter"] += 1

    if state["counter"] >= THRESHOLD and not state["reminded"]:
        state["reminded"] = True
        save_state(state_path, state)
        msg = (
            f"[session-log] {state['counter']} responses without appending to "
            f"{latest_log.name}. Consider recording recent progress."
        )
        print(json.dumps({
            "hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": msg},
            "systemMessage": msg,
        }))
        sys.exit(0)

    save_state(state_path, state)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail open — never block Claude due to a hook bug
        sys.exit(0)
