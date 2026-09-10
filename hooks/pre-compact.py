#!/usr/bin/env python3
"""
Pre-Compact State Capture Hook

Fires before context compaction to:
1. Capture current state (active plan, current task, recent decisions)
   so post-compact-restore.py can surface it afterwards.
2. OPTIONALLY block compaction when an active plan is still DRAFT, to
   avoid losing mid-plan context before the user has approved it.
   Opt-in via CLAUDE_PRECOMPACT_BLOCK_ON_DRAFT=1 (default: off).

Blocking protocol: exit 2, with the reason on stderr. PreCompact can block,
and exit 2 blocks it regardless of what is printed; there is no documented
hookSpecificOutput schema for this event, so JSON alone would not be reliable.
Block fires at most once per DRAFT plan — the plan path is recorded in
state, and a subsequent compaction for the same plan proceeds normally.
Fail-open on any internal error.

Hook Event: PreCompact
Returns: exit 2 to block, exit 0 otherwise.
"""

from __future__ import annotations

import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime
import hashlib

# Colors for the exit-2 block path only (stderr, terminal-rendered). The
# normal-path message goes out as JSON (systemMessage) and must not carry
# ANSI escapes as literal noise — see format_compaction_message().
YELLOW = "\033[0;33m"
NC = "\033[0m"  # No color


def get_session_dir() -> Path:
    """Get the session directory for storing state files."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return Path.home() / ".claude" / "sessions" / "default"

    project_hash = hashlib.md5(project_dir.encode()).hexdigest()[:8]
    session_dir = Path.home() / ".claude" / "sessions" / project_hash
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def find_active_plan(project_dir: str) -> dict | None:
    """Find the most recent non-completed plan."""
    plans_dir = Path(project_dir) / "quality_reports" / "plans"
    if not plans_dir.exists():
        return None

    plan_files = sorted(plans_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)

    for plan_file in plan_files[:3]:  # Check last 3 plans
        content = plan_file.read_text()

        # Skip completed plans
        if "COMPLETED" in content.upper():
            continue

        # Extract status
        status = "in_progress"
        if "APPROVED" in content.upper():
            status = "approved"
        elif "DRAFT" in content.upper():
            status = "draft"

        # Find current task (first unchecked item)
        current_task = None
        for line in content.split("\n"):
            if "- [ ]" in line:
                current_task = line.replace("- [ ]", "").strip()
                break

        return {
            "plan_path": str(plan_file),
            "plan_name": plan_file.name,
            "status": status,
            "current_task": current_task
        }

    return None


def find_session_report(project_dir: str) -> Path | None:
    """Locate SESSION_REPORT.md — root first, then `docs/`.

    See `find_session_report` in log-reminder.py for why both are checked.
    """
    for candidate in (
        Path(project_dir) / "SESSION_REPORT.md",
        Path(project_dir) / "docs" / "SESSION_REPORT.md",
    ):
        if candidate.is_file():
            return candidate
    return None


def extract_recent_decisions(project_dir: str, limit: int = 3) -> list[str]:
    """Extract decisions from the MOST RECENT SESSION_REPORT.md entry.

    `.claude/rules/logging.md` fixes the entry format, so this parses that format
    rather than pattern-hunting: entries open with `## YYYY-MM-DD HH:MM — Title`
    and a decision is a `- ` bullet under `**Decisions:**`. Scoping to the last
    entry is deliberate — a decision from a superseded entry is history, not
    current state, and restoring it after compaction would reassert something
    the session may have since reversed.

    The previous implementation scanned the last 50 lines of a session-log file
    for loose markers including a bare `•`, which matched any bullet at all.
    """
    report = find_session_report(project_dir)
    if report is None:
        return []

    try:
        content = report.read_text()
    except OSError:
        return []

    # Last entry = text after the final `## ` heading.
    entries = re.split(r"^## ", content, flags=re.MULTILINE)
    if len(entries) < 2:
        return []
    last = entries[-1]

    # The `**Decisions:**` block runs to the next `**Label:**` or end of entry.
    match = re.search(
        r"^\*\*Decisions?:\*\*\s*$(.*?)(?=^\*\*\w|\Z)",
        last,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []

    decisions = []
    for line in match.group(1).split("\n"):
        line = line.strip()
        if line.startswith("- ") and len(line) > 4:
            decisions.append(line[2:].strip()[:100])
            if len(decisions) >= limit:
                break
    return decisions


def save_state(state: dict) -> None:
    """Save state to the session directory."""
    state_file = get_session_dir() / "pre-compact-state.json"
    state["timestamp"] = datetime.now().isoformat()

    try:
        state_file.write_text(json.dumps(state, indent=2))
    except IOError as e:
        print(f"Warning: Could not save pre-compact state: {e}", file=sys.stderr)


def should_block_draft(plan_info: dict | None) -> tuple[bool, str]:
    """Return (should_block, reason). Opt-in via env var. Blocks at most
    once per DRAFT plan so the user can't get stuck in a loop.

    Failure modes (all fail-open — return (False, "")):
    - env var not set to "1"
    - no DRAFT plan active
    - sentinel file unreadable (corrupt JSON, OSError)
    - sentinel write fails (readonly filesystem, etc.)
    Rationale: a user who can't dismiss a block is worse off than one
    who loses a single compaction-blocking opportunity.

    The sentinel lives in its own file (`precompact-block-sentinel.json`)
    which is NOT touched by `post-compact-restore.py`. This is
    deliberate — `pre-compact-state.json` is wiped after each restore,
    which would make this guard fire again on every subsequent
    compaction of the same DRAFT plan.
    """
    if os.environ.get("CLAUDE_PRECOMPACT_BLOCK_ON_DRAFT", "0") != "1":
        return False, ""
    if not plan_info or plan_info.get("status") != "draft":
        return False, ""

    plan_path = plan_info.get("plan_path")
    if not plan_path:
        return False, ""

    sentinel_file = get_session_dir() / "precompact-block-sentinel.json"

    # Fail-open on read errors: if we can't tell whether this plan was
    # already blocked, don't block again. The guard's purpose is to warn
    # once, not to guarantee blocking under adverse conditions.
    try:
        if sentinel_file.exists():
            existing = json.loads(sentinel_file.read_text())
            if existing.get("last_blocked_plan") == plan_path:
                return False, ""
    except (OSError, json.JSONDecodeError):
        return False, ""

    # Only block if we successfully persist the sentinel. If the write
    # fails, fall through — blocking without a persisted sentinel would
    # cause repeat blocks on every subsequent compaction.
    try:
        sentinel_file.write_text(
            json.dumps({"last_blocked_plan": plan_path, "when": datetime.now().isoformat()})
        )
    except OSError as e:
        print(f"Warning: could not persist block sentinel; not blocking: {e}",
              file=sys.stderr)
        return False, ""

    reason = (
        f"Compaction blocked once: active plan "
        f"{plan_info.get('plan_name', '?')} is still DRAFT. "
        f"Either approve the plan (change its status line to APPROVED) "
        f"or, if you want to proceed without approval, re-run compaction "
        f"— this hook blocks at most once per DRAFT plan. To disable the "
        f"guard entirely, unset CLAUDE_PRECOMPACT_BLOCK_ON_DRAFT (or set "
        f"it to 0)."
    )
    return True, reason


def append_compaction_note(project_dir: str, trigger: str) -> None:
    """Append a compaction marker to SESSION_REPORT.md, in that file's format.

    `.claude/rules/logging.md` §Session Report mandates appending "at end of session or
    before context compression" — this is the second case, written by the hook
    so the marker exists even when compaction arrives unannounced.

    Never CREATES the file. An absent SESSION_REPORT.md means the project has
    not started one; conjuring a headerless file would leave `/checkpoint` to
    append its first real entry beneath no `# Session Report — [Project]`
    header, which is the one thing logging.md says to write first.
    """
    report = find_session_report(project_dir)
    if report is None:
        return

    try:
        with open(report, "a") as f:
            f.write(f"\n\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} — "
                    f"Context compaction ({trigger})\n\n")
            f.write("**Operations:**\n")
            f.write("- Context compacted. For current state read "
                    "`quality_reports/pipeline_state.json`, the active plan under "
                    "`quality_reports/plans/`, and `git status`.\n")
    except IOError:
        pass


def format_compaction_message(plan_info: dict | None, decisions: list[str]) -> str:
    """Format the pre-compaction message. Plain text — no ANSI escapes, since
    this now goes out as a JSON `systemMessage`, not a terminal print."""
    lines = []
    lines.append("⚡ Context compaction starting")
    lines.append("")

    if plan_info:
        lines.append("Current state saved:")
        lines.append(f"  Plan: {plan_info['plan_name']} ({plan_info['status']})")
        if plan_info.get("current_task"):
            lines.append(f"  Next task: {plan_info['current_task']}")

    if decisions:
        lines.append("")
        lines.append("Recent decisions captured:")
        for d in decisions:
            lines.append(f"  • {d[:80]}...")

    lines.append("")
    lines.append("State will be restored after compaction.")

    return "\n".join(lines)


def main() -> int:
    """Main hook entry point."""
    # Read hook input
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, IOError):
        hook_input = {}

    trigger = hook_input.get("trigger", "auto")
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")

    if not project_dir:
        return 0

    # Gather state
    plan_info = find_active_plan(project_dir)
    decisions = extract_recent_decisions(project_dir)

    # Build state object
    state = {
        "trigger": trigger,
        "plan_path": plan_info["plan_path"] if plan_info else None,
        "plan_status": plan_info["status"] if plan_info else None,
        "current_task": plan_info.get("current_task") if plan_info else None,
        "decisions": decisions
    }

    # DRAFT-plan guard: opt-in block to avoid losing mid-plan context
    # before the user has approved. Fires at most once per plan.
    block, reason = should_block_draft(plan_info)
    if block:
        # Exit 2, not exit 0 + JSON. The docs guarantee that on an event which
        # can block — PreCompact is one — "exit 2 blocks whether or not you
        # print JSON", but they publish no hookSpecificOutput schema for
        # PreCompact, so a JSON-only block rests on an undocumented shape. The
        # reason still goes to stderr, which is what the user and Claude see.
        print(f"\n{YELLOW}⚡ Compaction blocked{NC} (DRAFT plan detected)",
              file=sys.stderr)
        print(f"   {reason}\n", file=sys.stderr)
        return 2

    # Save state for restoration
    save_state(state)

    # Record the compaction in the append-only session history
    append_compaction_note(project_dir, trigger)

    # Emit on the documented JSON channel (systemMessage) instead of stderr,
    # whose format is undefined and which Claude does not see.
    print(json.dumps({"systemMessage": format_compaction_message(plan_info, decisions)}))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open — never block Claude due to a hook bug
        sys.exit(0)
