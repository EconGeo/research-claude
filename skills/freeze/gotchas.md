# Freeze Skill -- Gotchas

- Freeze paths are relative to project root. `/freeze explorations/` means `$PROJECT_ROOT/explorations/`.
- `.claude/` is editable regardless of freeze -- with one exception: `.claude/state/session-guards.json`, so a frozen session cannot unfreeze itself with an Edit. Use the Bash write documented in the skill.
- Freeze doesn't affect Read or Bash -- you can always read and run commands, just not edit files outside allowed paths.
- Multiple paths: `/freeze data/raw/ talks/` allows both directories.
- The guard persists on disk. It survives `/compact` **and** the end of the conversation; a new session inherits an active freeze. `/freeze off` is what ends it.
