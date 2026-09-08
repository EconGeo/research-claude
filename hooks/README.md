# Hooks

These hooks are linked into every project but fire only if the project's
`.claude/settings.json` references them. Wiring is deliberately **opt-in**:
enabling seven hooks across six repos at once is a silent behavior change, and
`settings.json` stays project-owned and is never linked.

To enable one, add it to the project's own `settings.json`.

| Hook | Event | What it does |
|---|---|---|
| `session-guard.py` | SessionStart | Session state checks |
| `pre-compact.py` | PreCompact | Reminds you to persist plan / memory / journal before compaction |
| `post-compact-restore.py` | PostCompact | Restores context pointers after compaction |
| `post-edit-lint.sh` | PostToolUse (Edit/Write) | Advisory lint on edited scripts |
| `lint-scripts.sh` | manual / PostToolUse | Lints analysis scripts against INV-14..19 |
| `protect-files.sh` | PreToolUse | Blocks edits to protected paths |
| `post-merge.sh` | git post-merge | Post-merge housekeeping |

**Note.** `lint-scripts.sh` and `post-edit-lint.sh` predate the Quarto-native
pipeline, where analysis lives in `.qmd` chunks rather than `scripts/R/*.R`.
They still work on the acquisition scripts under `scripts/acquire/`. Enable them
with that scope in mind.
