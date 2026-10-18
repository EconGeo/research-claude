#!/usr/bin/env python3
"""wire_guard_hooks.py — add the script-guard and read-gate hooks to a project's settings.json.

    wire_guard_hooks.py <settings.json>

settings.json is project-owned and copy_seed never overwrites it, so a hook added to the seed
reaches new projects only. These two guards are enforcement, not taste: a guard that is linked
but unwired enforces nothing (hooks/README.md, "A hook that is installed but unwired is not a
dormant feature"). This adds the entries a project lacks and leaves every other key alone.
Idempotent: a hook already named anywhere in the file is not added twice. Also widens the protect-files matcher to cover Bash. Prints the number of
entries added or changed.
"""
import json, sys
from pathlib import Path

CMD = '"$CLAUDE_PROJECT_DIR"/.claude/run-hook.sh {}'
WANTED = [
    ("PreToolUse", "Write|Edit|Bash", "script-guard.py"),
    ("PreToolUse", "Write|Edit|Bash", "read-gate.py"),
    ("PreToolUse", "Write|Edit|Bash", "design-guard.py"),
    ("PostToolUse", "Read|Edit|Write", "read-gate.py"),
    ("UserPromptSubmit", None, "design-token.py"),
    ("SessionStart", None, "stale-stages.py"),
]


def check_wanted() -> None:
    if any(h.startswith("git/") for _, _, h in WANTED):
        raise ValueError("hooks/git/ holds git hooks, not Claude hooks")


check_wanted()


def wire(settings: dict) -> int:
    hooks = settings.setdefault("hooks", {})
    added = 0
    for event, matcher, hook in WANTED:
        groups = hooks.setdefault(event, [])
        already = any(hook in h.get("command", "") for g in groups for h in g.get("hooks", []))
        if already:
            continue
        group = next((g for g in groups if g.get("matcher") == matcher), None)
        if group is None:
            group = {"hooks": []} if matcher is None else {"matcher": matcher, "hooks": []}
            groups.append(group)
        group["hooks"].append({"type": "command", "command": CMD.format(hook), "timeout": 5})
        added += 1
    return added


def widen(settings: dict) -> int:
    """An `Edit|Write` group holding protect-files.sh becomes `Edit|Write|Bash` (shell writes)."""
    changed = 0
    for g in settings.get("hooks", {}).get("PreToolUse", []):
        if g.get("matcher") == "Edit|Write" and any(
                "protect-files.sh" in h.get("command", "") for h in g.get("hooks", [])):
            g["matcher"] = "Edit|Write|Bash"
            changed += 1
    return changed


if __name__ == "__main__":
    path = Path(sys.argv[1])
    data = json.loads(path.read_text())
    n = wire(data) + widen(data)
    if n:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(n)
