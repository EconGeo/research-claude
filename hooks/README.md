# Hooks

These hooks are linked into every project but fire only if the project's
`.claude/settings.json` references them. `settings.json` stays project-owned and
is never linked, so wiring is per-project by construction.

**New projects get a baseline.** `apply.sh` seeds `seeds/settings.json` into
`<project>/.claude/settings.json`, which wires the six hooks two projects had
independently converged on. It is a seed, not a link: `copy_seed` never
overwrites, so editing it is safe and an existing file is left alone.

**Existing projects were left as they were**, except for `session-guard.py` —
see below. Turning six hooks on across six repos at once is a behavior change
that should be a decision, not a side effect.

## A hook that is installed but unwired is not a dormant feature

It is a **broken promise**, because the skill that depends on it still says it
works. `/freeze` and `/careful` write `.claude/state/session-guards.json` and
document that "the `session-guard` PreToolUse hook reads this file and blocks
Edit/Write operations" — and that hook was wired in none of the six projects, so
both skills reported themselves active while enforcing nothing. It has now been
wired everywhere. It is inert until a guard file exists, so wiring it changes
nothing until you actually run `/freeze` or `/careful`.

Before shipping a skill that depends on a hook, check that the hook is wired.

| Hook | Event | What it does |
|---|---|---|
| `session-guard.py` | SessionStart | Session state checks |
| `pre-compact.py` | PreCompact | Reminds you to persist plan / memory / journal before compaction |
| `post-compact-restore.py` | PostCompact | Restores context pointers after compaction |
| `post-edit-lint.sh` | PostToolUse (Edit/Write) | Advisory lint on edited scripts |
| `lint-scripts.sh` | manual / PostToolUse | Lints analysis scripts against INV-14..19 |
| `protect-files.sh` | PreToolUse | Blocks edits to protected paths |
| `post-merge.sh` | git post-merge | Post-merge housekeeping |
| `context-monitor.py` | PostToolUse | Progressive, de-duplicated nudges as context fills (40/55/65%, then 80%) |
| `log-reminder.py` | Stop | Counts responses since the session log was last touched and nudges via stderr. Never blocks |
| `verify-reminder.py` | PostToolUse (Write/Edit) | Reminds you to render before calling a task done, on `.qmd`/`.R` edits |
| `notify.sh` | Notification | Cross-platform desktop notification when Claude needs attention. Fails open without `jq` |

## Getting the contract right

Hook input arrives as **JSON on stdin**, never in the environment — there are no
`CLAUDE_TOOL_ARG_*` variables, and a hook that reads one silently does nothing.
The blocking contract differs per event, and using the wrong one fails silently
too, because an ignored decision just looks like a hook that chose not to act:

| Event | To block |
|---|---|
| `PreToolUse` | `hookSpecificOutput.permissionDecision: "deny"` + `permissionDecisionReason`. A top-level `{"decision":"block"}` is **not** honoured here. Exit 2 also blocks. |
| `PreCompact`, `Stop` | Exit 2, reason on stderr. Exit 2 blocks whether or not JSON is printed. |
| `PostToolUse` | Cannot block — the tool already ran. Use `systemMessage` (user-visible) and `hookSpecificOutput.additionalContext` (Claude-visible). |
| `SessionStart` | Cannot block. Match on `source` (`startup`, `resume`, `clear`, `compact`, `fork`) — not `type`. |

Three shipped hooks got this wrong and did nothing at all until 2026-09-08:
`post-edit-lint.sh` read `$CLAUDE_TOOL_ARG_FILE_PATH` and exited on line one;
`session-guard.py` emitted the PostToolUse block shape from a PreToolUse hook;
`pre-compact.py` relied on an undocumented PreCompact JSON schema. Two more had
been fixed days earlier for the same class of reason. **A hook that fails this
way leaves no trace** — no error, no log line, just nothing happening — so test
one by piping it a payload rather than trusting that it is installed:

```bash
echo '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/x.R"}}' \
  | .claude/hooks/post-edit-lint.sh; echo "exit=$?"
```

**Note.** `lint-scripts.sh` and `post-edit-lint.sh` predate the Quarto-native
pipeline, where analysis lives in `.qmd` chunks rather than `scripts/R/*.R`. <!-- residue:prohibition -->
They still work on the acquisition scripts under `scripts/acquire/`. Enable them
with that scope in mind.
