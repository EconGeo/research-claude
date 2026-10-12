#!/usr/bin/env python3
"""wire_guard_hooks.py — add the script-guard and read-gate hooks to a project's settings.json.

    wire_guard_hooks.py <settings.json>

settings.json is project-owned and copy_seed never overwrites it, so a hook added to the seed
reaches new projects only. These two guards are enforcement, not taste: a guard that is linked
but unwired enforces nothing (hooks/README.md, "A hook that is installed but unwired is not a
dormant feature"). This adds the entries a project lacks and leaves every other key alone.
Idempotent: a hook already named anywhere in the file is not added twice. Prints the number of
entries added.
"""
import json, sys
from pathlib import Path

CMD = '"$CLAUDE_PROJECT_DIR"/.claude/run-hook.sh {}'
WANTED = [
    ("PreToolUse", "Write|Edit|Bash", "script-guard.py"),
    ("PreToolUse", "Write|Edit|Bash", "read-gate.py"),
    ("PostToolUse", "Read|Edit|Write", "read-gate.py"),
]


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
            group = {"matcher": matcher, "hooks": []}
            groups.append(group)
        group["hooks"].append({"type": "command", "command": CMD.format(hook), "timeout": 5})
        added += 1
    return added


if __name__ == "__main__":
    path = Path(sys.argv[1])
    data = json.loads(path.read_text())
    n = wire(data)
    if n:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(n)
