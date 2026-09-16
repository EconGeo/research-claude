# Careful Skill -- Gotchas

- `git push --force-with-lease` is blocked too. It is safer than `--force` but still rewrites remote history.
- `rm file.txt` (no recursive or force flag) is allowed. Only recursive/force patterns are blocked.
- Pattern matching is case-sensitive except for `DROP TABLE` / `DROP DATABASE`. `git branch -d` is deliberately allowed; only `-D` is blocked.
- The guard doesn't prevent the user from running commands in their own terminal -- it only blocks Claude's Bash tool calls.
- Careful mode is independent of freeze mode -- you can activate both simultaneously. That is why `/careful` read-modify-writes `session-guards.json` instead of overwriting it.
- The guard persists on disk. A new session inherits it; `/careful off` is what ends it.
