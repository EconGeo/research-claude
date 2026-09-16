---
name: freeze
description: Block edits outside specified directories for this session. Protects files from accidental changes during focused work. Activate with /freeze [dirs], deactivate with /freeze off.
user-invocable: true
---

# Freeze -- Session-Scoped Edit Guard

Blocks Write and Edit operations on files outside the specified directories. Use when reviewing code (freeze everything except notes), when writing (freeze `explorations/`), or when editing data pipelines (freeze `data/raw/`).

## Usage

```
/freeze explorations/       # Only allow edits in explorations/
/freeze data/raw/ talks/    # Only allow edits in data/raw/ and talks/
/freeze off                 # Deactivate all freeze guards
```

## How It Works

1. Parse the directory arguments from the user's input
2. Write the guard configuration to `.claude/state/session-guards.json`
3. The `session-guard` PreToolUse hook reads this file and blocks Edit/Write operations on files outside the allowed directories
4. Report what's frozen and what's editable

## Activation

When the user invokes `/freeze [dirs]`:

**If no directories are given, stop and ask which directories should stay editable.** An empty
`allowed_paths` blocks every edit outside `.claude/`, which is almost never what the user meant.

Write the guard with Bash — never Edit or Write. The hook denies Edit/Write on the guard file
while freeze is active, and a read-modify-write is what preserves an active `careful` guard:

```bash
python3 - <<'PY'
import json, pathlib, datetime
p = pathlib.Path(".claude/state/session-guards.json")
g = json.loads(p.read_text()) if p.exists() else {}
g["freeze"] = {"active": True,
               "allowed_paths": ["explorations/"],
               "activated_at": datetime.datetime.now().isoformat(timespec="seconds"),
               "reason": "User invoked /freeze"}
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(g, indent=2) + "\n")
PY
```

Confirm: "Freeze active. Edits allowed only in: [dirs]. Run `/freeze off` to deactivate."

## Deactivation

When the user invokes `/freeze off`, again with Bash:

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path(".claude/state/session-guards.json")
g = json.loads(p.read_text()) if p.exists() else {}
g.setdefault("freeze", {})["active"] = False
p.write_text(json.dumps(g, indent=2) + "\n")
PY
```

Confirm: "Freeze deactivated. All paths editable."

## Gotchas

- **Not session-scoped.** The guard file persists on disk; the hook reads
  `.claude/state/session-guards.json` on every PreToolUse. A new session inherits an active
  freeze. `/freeze off` is what ends it.
- `.claude/` is editable **except** `.claude/state/session-guards.json` itself — otherwise a
  frozen session could unfreeze itself. This is why activation and deactivation use Bash.
- Paths are relative to the project root.
- `/freeze` with no directories would block every edit. The skill refuses instead.
