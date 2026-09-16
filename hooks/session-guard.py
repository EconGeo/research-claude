#!/usr/bin/env python3
"""
Session Guard Hook -- PreToolUse

Enforces session-scoped guards:
- freeze: blocks Edit/Write outside allowed directories
- careful: blocks destructive Bash commands

Reads guard configuration from .claude/state/session-guards.json.
If no guards are active or the file doesn't exist, passes through immediately.

Hook Event: PreToolUse
"""

import json
import os
import re
import sys
from pathlib import Path


def load_guards() -> dict:
    """Load active guards from session state."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return {}

    guards_file = Path(project_dir) / ".claude" / "state" / "session-guards.json"
    if not guards_file.exists():
        return {}

    try:
        return json.loads(guards_file.read_text())
    except (json.JSONDecodeError, IOError):
        return {}


def check_freeze(tool_name: str, tool_input: dict, guards: dict) -> tuple:
    """Check if the edit/write is allowed by freeze guard."""
    freeze = guards.get("freeze", {})
    if not freeze.get("active", False):
        return True, ""

    if tool_name not in ("Edit", "Write"):
        return True, ""

    file_path = tool_input.get("file_path", "")
    if not file_path:
        return True, ""

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")

    # .claude/ is editable EXCEPT its own guard state file — a blanket exemption
    # would let a frozen session edit session-guards.json and unfreeze itself.
    if "/.claude/" in file_path and not file_path.endswith("/.claude/state/session-guards.json"):
        return True, ""

    # Check against allowed paths
    allowed = freeze.get("allowed_paths", [])
    for allowed_path in allowed:
        # Resolve relative to project dir
        full_allowed = os.path.join(project_dir, allowed_path)
        if file_path.startswith(full_allowed):
            return True, ""

    return False, (
        f"FREEZE ACTIVE: Edit blocked. File '{os.path.basename(file_path)}' "
        f"is outside allowed paths: {allowed}. Ask the user to run /freeze off."
    )


# Compiled per pattern: only the SQL forms are case-insensitive. A global re.IGNORECASE
# made `git branch -d` (which refuses to delete an unmerged branch) as blocked as
# `git branch -D`, so the guard denied a safe command and taught the user to turn it off.
DESTRUCTIVE_PATTERNS = [
    (re.compile(r"\brm\s+(-\S+\s+)*(-[a-zA-Z]*[rf]|--force\b|--recursive\b)"),
     "rm with recursive/force flags"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "git reset --hard"),
    # The refspec form is the one people type. `\bgit\s+push\s+--force\b` matched only the
    # bare form and let `git push origin main --force` straight through.
    (re.compile(r"\bgit\s+push\b[^\n]*?(\s--force(-with-lease)?\b|\s-f\b)"), "git push --force"),
    (re.compile(r"\bgit\s+clean\s+-[a-z]*f"), "git clean -f"),
    (re.compile(r"\bgit\s+checkout\s+--\s+\."), "git checkout -- ."),
    (re.compile(r"\bgit\s+branch\s+-D\b"), "git branch -D"),
    (re.compile(r"\bfind\b[^\n]*\s-delete\b"), "find -delete"),
    (re.compile(r"\bfind\b[^\n]*-exec\s+rm\b"), "find -exec rm"),
    (re.compile(r"\bDROP\s+TABLE\b", re.I), "DROP TABLE"),
    (re.compile(r"\bDROP\s+DATABASE\b", re.I), "DROP DATABASE"),
    (re.compile(r"\bchmod\s+777\b"), "chmod 777"),
]


def check_careful(tool_name: str, tool_input: dict, guards: dict) -> tuple:
    """Check if the bash command is allowed by careful guard."""
    careful = guards.get("careful", {})
    if not careful.get("active", False):
        return True, ""

    if tool_name != "Bash":
        return True, ""

    command = tool_input.get("command", "")
    if not command:
        return True, ""

    for pattern, description in DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            return False, (
                f"CAREFUL MODE: Blocked '{description}'. "
                f"Ask the user to run /careful off if this command is intended."
            )

    return True, ""


def deny(message: str) -> None:
    """Refuse the tool call.

    PreToolUse honours `hookSpecificOutput.permissionDecision`. It does NOT
    honour a top-level {"decision": "block"} — that is the PostToolUse/Stop
    shape, and this hook emitted it for both guards, so the JSON was ignored,
    the hook exited 0, and the tool ran. /freeze and /careful reported that they
    were active while blocking nothing at all.
    See https://code.claude.com/docs/en/hooks.
    """
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        },
    }))


def main() -> int:
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, IOError):
        return 0  # Pass through on parse error

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    guards = load_guards()
    if not guards:
        return 0  # No guards active, pass through

    # Check freeze
    allowed, message = check_freeze(tool_name, tool_input, guards)
    if not allowed:
        deny(message)
        return 0

    # Check careful
    allowed, message = check_careful(tool_name, tool_input, guards)
    if not allowed:
        deny(message)
        return 0

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open — never block Claude due to a hook bug
        sys.exit(0)
