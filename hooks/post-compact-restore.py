#!/usr/bin/env python3
"""
Post-Compact Context Restoration Hook

Fires after compaction (SessionStart with source="compact") to restore context.
Reads saved state from the session directory and prints it so Claude knows
where it left off.

Hook Event: SessionStart (matcher: "compact|resume")
Returns: Exit code 0 (output to stdout)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# SessionStart stdout is injected into Claude's context, so this hook emits a
# clean, ANSI-free message via the hookSpecificOutput.additionalContext contract
# (raw ANSI escape codes here would be literal noise + wasted tokens in context).
# See https://code.claude.com/docs/en/hooks.


def get_session_dir() -> Path:
    """Get the session directory for storing state files."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return Path.home() / ".claude" / "sessions" / "default"

    # Use a hash of the project dir for the session subdir
    import hashlib
    project_hash = hashlib.md5(project_dir.encode()).hexdigest()[:8]
    session_dir = Path.home() / ".claude" / "sessions" / project_hash
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def read_pre_compact_state() -> dict | None:
    """Read and delete the pre-compact state file."""
    session_dir = get_session_dir()
    state_file = session_dir / "pre-compact-state.json"

    if not state_file.exists():
        return None

    try:
        state = json.loads(state_file.read_text())
        state_file.unlink()  # Clean up after restore
        return state
    except (json.JSONDecodeError, IOError):
        return None


def find_pipeline_state(project_dir: str) -> dict | None:
    """Read quality_reports/pipeline_state.json and extract a short summary.

    Field names below (`overall`, `blocked_by`, `updated`) are the state file's own
    top-level keys — see .claude/scripts/pipeline.py's `empty_state`/`save_state`. There is
    no top-level "last component" field in the state file itself, so it is derived
    here: the key of `components` whose `at` timestamp is lexicographically greatest.
    `now()` in .claude/scripts/pipeline.py documents that its ISO-8601 timestamps are fixed
    width with a constant UTC offset specifically so lexicographic order ==
    chronological order, which is what makes that derivation valid.
    """
    state_file = Path(project_dir) / "quality_reports" / "pipeline_state.json"
    if not state_file.exists():
        return None

    try:
        state = json.loads(state_file.read_text())
    except (json.JSONDecodeError, IOError):
        return None

    if not isinstance(state, dict):
        return None

    components = state.get("components")
    last_component = None
    if isinstance(components, dict) and components:
        scored = [
            (c, e.get("at")) for c, e in components.items()
            if isinstance(e, dict) and e.get("at")
        ]
        if scored:
            last_component = max(scored, key=lambda ce: ce[1])[0]

    return {
        "path": str(state_file),
        "overall": state.get("overall"),
        "blocked_by": state.get("blocked_by"),
        "last_component": last_component,
        "updated": state.get("updated"),
    }


def find_active_plan(project_dir: str) -> dict | None:
    """Find the most recent plan file and extract its status."""
    plans_dir = Path(project_dir) / "quality_reports" / "plans"
    if not plans_dir.exists():
        return None

    # Get most recent plan file
    plan_files = sorted(plans_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not plan_files:
        return None

    latest_plan = plan_files[0]
    content = latest_plan.read_text()

    # Extract status from plan content
    status = "unknown"
    if "COMPLETED" in content.upper():
        status = "completed"
    elif "APPROVED" in content.upper():
        status = "in_progress"
    elif "DRAFT" in content.upper():
        status = "draft"

    # Extract current task if present
    current_task = None
    for line in content.split("\n"):
        if "- [ ]" in line:  # First unchecked task
            current_task = line.replace("- [ ]", "").strip()
            break

    return {
        "plan_path": str(latest_plan),
        "plan_name": latest_plan.name,
        "status": status,
        "current_task": current_task
    }


def find_recent_session_log(project_dir: str) -> dict | None:
    """Find the most recent session log."""
    logs_dir = Path(project_dir) / "quality_reports" / "session_logs"
    if not logs_dir.exists():
        return None

    log_files = sorted(logs_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not log_files:
        return None

    return {
        "log_path": str(log_files[0]),
        "log_name": log_files[0].name
    }


def format_restoration_message(
    pipeline_state: dict | None,
    pre_compact_state: dict | None,
    plan_info: dict | None,
    session_log: dict | None
) -> str:
    """Format the (ANSI-free) context restoration message for Claude."""
    lines = ["[Context Restored After Compaction]", ""]

    if pipeline_state:
        lines.append("Pipeline State:")
        lines.append(f"  File: {pipeline_state['path']}")
        lines.append(f"  Overall: {pipeline_state['overall'] if pipeline_state['overall'] is not None else 'n/a'}")
        if pipeline_state.get("blocked_by"):
            lines.append(f"  Blocked by: {pipeline_state['blocked_by']}")
        if pipeline_state.get("last_component"):
            lines.append(f"  Last component scored: {pipeline_state['last_component']}")
        if pipeline_state.get("updated"):
            lines.append(f"  Updated: {pipeline_state['updated']}")
        lines.append("")

    if pre_compact_state:
        lines.append("Pre-Compaction State:")
        if pre_compact_state.get("plan_path"):
            lines.append(f"  Plan: {pre_compact_state['plan_path']}")
        if pre_compact_state.get("current_task"):
            lines.append(f"  Task: {pre_compact_state['current_task']}")
        if pre_compact_state.get("decisions"):
            lines.append("  Recent decisions:")
            for decision in pre_compact_state["decisions"][-3:]:
                lines.append(f"    - {decision}")
        lines.append("")

    if plan_info:
        lines.append("Active Plan:")
        lines.append(f"  File: {plan_info['plan_name']}")
        lines.append(f"  Status: {plan_info['status']}")
        if plan_info.get("current_task"):
            lines.append(f"  Next task: {plan_info['current_task']}")
        lines.append("")

    if session_log:
        lines.append("Session Log:")
        lines.append(f"  {session_log['log_name']}")
        lines.append("")

    lines.append("Recovery Actions:")
    lines.append("  1. Read quality_reports/pipeline_state.json (python3 .claude/scripts/pipeline.py state show), then the active plan")
    lines.append("  2. Check git status/diff for uncommitted changes")
    lines.append("  3. Continue from where you left off")

    return "\n".join(lines)


def main() -> int:
    """Main hook entry point."""
    # Read hook input (not strictly needed but good practice)
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, IOError):
        hook_input = {}

    # Only run on compact/resume sessions
    session_source = hook_input.get("source", "")
    if session_source not in ("compact", "resume"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return 0

    # Gather context
    pipeline_state = find_pipeline_state(project_dir)
    pre_compact_state = read_pre_compact_state()
    plan_info = find_active_plan(project_dir)
    session_log = find_recent_session_log(project_dir)

    # If we have any context to restore, inject it via the SessionStart contract
    # (clean additionalContext — not raw stdout carrying ANSI escape noise).
    if pipeline_state or pre_compact_state or plan_info or session_log:
        message = format_restoration_message(pipeline_state, pre_compact_state, plan_info, session_log)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": message,
            }
        }))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open — never block Claude due to a hook bug
        sys.exit(0)
