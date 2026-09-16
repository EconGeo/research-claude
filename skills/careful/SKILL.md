---
name: careful
description: Block destructive bash commands for this session. Prevents rm -rf, git reset --hard, git push --force, and similar dangerous operations. Activate with /careful, deactivate with /careful off.
user-invocable: true
---

# Careful -- Session-Scoped Destructive Command Guard

Blocks Bash commands matching destructive patterns. Use when working on critical branches, before a deadline, or whenever you want an extra safety net.

## Usage

```
/careful       # Activate destructive command blocking
/careful off   # Deactivate
```

## Blocked Patterns

When active, the following Bash command patterns are blocked. The list matches
`.claude/hooks/session-guard.py` exactly — if you change one, change the other.

| Pattern | What It Catches |
|---------|----------------|
| `rm -r` / `rm -f` / `rm -rf` / `rm -v -rf` / `rm --force` / `rm --recursive` | Recursive or force delete, including flags typed before the recursive one |
| `git reset --hard` | Discard all uncommitted changes |
| `git push ... --force` / `-f` / `--force-with-lease` | Force push, with or without a remote and refspec (`git push origin main --force`) |
| `git clean -f` (also `-xdf`, `-fd`) | Delete untracked files |
| `git checkout -- .` | Discard all working tree changes |
| `git branch -D` | Force delete branch. The lowercase `git branch -d` is **not** blocked — it refuses to delete an unmerged branch, so it is safe |
| `find ... -delete` | Bulk delete by find |
| `find ... -exec rm` | Same, via exec |
| `DROP TABLE` | SQL table deletion (case-insensitive) |
| `DROP DATABASE` | SQL database deletion (case-insensitive) |
| `chmod 777` | Overly permissive permissions |

Every pattern except the two SQL ones is case-**sensitive**.

## Activation

When the user invokes `/careful`, write the guard with Bash. The read-modify-write is what
preserves an active `freeze` guard — overwriting the file with a `careful`-only object
silently unfreezes the session:

```bash
python3 - <<'PY'
import json, pathlib, datetime
p = pathlib.Path(".claude/state/session-guards.json")
g = json.loads(p.read_text()) if p.exists() else {}
g["careful"] = {"active": True,
                "activated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "reason": "User invoked /careful"}
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(g, indent=2) + "\n")
PY
```

Confirm: "Careful mode active. Destructive bash commands are blocked. Run `/careful off` to deactivate."

## Deactivation

When the user invokes `/careful off`, again with Bash:

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path(".claude/state/session-guards.json")
g = json.loads(p.read_text()) if p.exists() else {}
g.setdefault("careful", {})["active"] = False
p.write_text(json.dumps(g, indent=2) + "\n")
PY
```

Confirm: "Careful mode deactivated."

## Gotchas

- **Not session-scoped.** The guard file persists on disk. A new session inherits an active
  careful guard; `/careful off` is what ends it.
- Only blocks Bash tool calls -- doesn't affect user's terminal
- A denied call is denied -- there is no override prompt. `/careful off` is the only way through.
- `rm` without a recursive or force flag is still allowed (single file deletion)
