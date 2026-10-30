# Hooks

These hooks are linked into every project but fire only if the project's
`.claude/settings.json` references them. `settings.json` stays project-owned and
is never linked, so wiring is per-project by construction.

**New projects get a baseline.** `apply.sh` seeds `seeds/settings.json` into
`<project>/.claude/settings.json`, which wires every hook in the table below. It is a seed, not a link: `copy_seed` never
overwrites, so editing it is safe and an existing file is left alone.

**Existing projects were left as they were.** Turning hooks on across six repos at once is a behavior change
that should be a decision, not a side effect.

## Hooks run through `.claude/run-hook.sh` (fresh git worktrees)

`.claude/hooks/` is untracked symlinks; `.claude/settings.json` is tracked. A git worktree
(the desktop app makes one per session) therefore gets settings naming hooks that do not
exist, and a failing PreToolUse hook blocks every tool call — including the repair.
Every seeded hook command is `"$CLAUDE_PROJECT_DIR"/.claude/run-hook.sh <hook-file>`. That
launcher (seeds, run-hook.sh) is a real, tracked file: it runs the hook from the project, else
from the main checkout, else warns and exits 0. `apply.sh` refreshes it and rewrites existing
`settings.json` commands once (idempotent). To give a worktree the
full pipeline (agents, skills, rules), run `apply.sh --project-dir <worktree> --link`.
Tests: test_run_hook.py.

## A hook that is installed but unwired is not a dormant feature

It is a **broken promise** when a skill still says the hook enforces something. Ten hooks
that no project wired (session guards, compaction capture, reminders, lint, notifications)
were deleted on 2026-10-29 rather than left installed and inert.

Before shipping a skill that depends on a hook, check that the hook is wired.

| Hook | Event | What it does |
|---|---|---|
| `protect-files.sh` | PreToolUse | Blocks Edit of, and Write over, protected paths (generated evidence, state, settings, the design lock and record files), and shell writes to them (redirect, `tee`, `sed -i`, `cp`, `mv`, `rm`); a Write that creates one is allowed — critics return text and the session saves it |
| `dispatch-log.py` | SubagentStop | Appends every subagent completion to `quality_reports/agent_dispatch.jsonl` — the log `pipeline.py`'s `critic-ran` predicate reads |
| `critic-pairing.py` | Stop | Surfaces a creator that ran without its critic; blocks once per session per creator, then advisory |
| `script-guard.py` | PreToolUse (Write/Bash) | Refuses creating a new R/Python/Julia script outside `explorations/`, `scripts/acquire/` and `.claude/` in a project that declares `manuscript:` (.claude/rules/quarto-empirical.md). Blocking |
| `read-gate.py` | PostToolUse (Read/Edit/Write) + PreToolUse (Edit/Write/Bash) | Records which manuscript lines each agent has read; refuses an edit to the declared manuscript until that agent has read every line since the file last changed. Blocking |
| `design-guard.py` | PreToolUse (Write/Edit/Bash) | Refuses an edit that changes a signed `design:` block, a Bash write to the manuscript while signed, `pipeline.py design sign\|unlock` without the author's fresh token, any write to the lock, token and record files, and a Bash `claude … approve design` (a nested session never submits an approval line). Blocking; fails open on internal error |
| `design-token.py` | UserPromptSubmit | Turns the author's chat approval line into a one-time token for `pipeline.py design sign` or `unlock`; revokes an unused token on the next message. Never blocks |
| `stale-stages.py` | SessionStart | Prints the strategy, manuscript or referee scores a re-estimation or design change made stale; silent otherwise |

## Getting the contract right

Hook input arrives as **JSON on stdin**, never in the environment — there are no
`CLAUDE_TOOL_ARG_*` variables, and a hook that reads one silently does nothing.
The blocking contract differs per event, and using the wrong one fails silently
too, because an ignored decision just looks like a hook that chose not to act:

| Event | To block |
|---|---|
| `PreToolUse` | `hookSpecificOutput.permissionDecision: "deny"` + `permissionDecisionReason`. A top-level `{"decision":"block"}` is **not** honoured here. Exit 2 also blocks. |
| `PreCompact`, `Stop` | Exit 2, reason on stderr. `Stop` **also** honours a top-level `{"decision":"block","reason":…}` — which is what `critic-pairing.py` emits; exit 2 blocks whether or not JSON is printed. |
| `PostToolUse` | Cannot block — the tool already ran. Use `systemMessage` (user-visible) and `hookSpecificOutput.additionalContext` (Claude-visible). |
| `SessionStart` | Cannot block. Match on `source` (`startup`, `resume`, `clear`, `compact`, `fork`) — not `type`. |

**A hook that fails this way leaves no trace** — no error, no log line, just nothing
happening — so test one by piping it a payload rather than trusting that it is installed:

```bash
echo '{"hook_event_name":"Stop","session_id":"t"}' \
  | .claude/hooks/critic-pairing.py; echo "exit=$?"
```

## Git hooks

The `git/` subdirectory holds **git** hooks, not Claude hooks. They are not in the table above, carry no
`Hook Event:` line, and are never wired in `settings.json` (`check_install.sh` `hooks-wired` fails if
a settings command names a file under it). `apply.sh --link` links the directory as one link
(`.claude/hooks/git`) and sets `core.hooksPath = .claude/hooks/git` in the project repo; it leaves an
existing `core.hooksPath` or hand-made `.git/hooks` alone and says so. `check_install.sh`
`git-hooks-path` fails where the gate is not installed — notably a fresh worktree, which has the
config but not the links (run `apply.sh --project-dir <worktree> --link`).

- `git/pre-commit` runs `pipeline.py commit-check`: design lock, prose numbers, Quarto structure,
  cold render after a model-chunk (`estimate-*`/`robustness-*`) code change, manuscript staleness
  (the commit that lands the re-estimation passes with a warning), and the amendment table. Every
  manuscript check reads the STAGED bytes, so a hunk-wise `git add -p` commit is checked on what it
  commits. The hook exits 0 with a notice when the git client's PATH has no `python3`. Never
  bypass it with `--no-verify`.
  In a paper whose manuscript has no `design:` block (NOT-RETROFITTED) the prose check and the
  cold-render receipt only WARN: they turn on at the retrofit. Design state, structure, staging
  and staleness hold for every paper.
- `git/post-commit` runs `pipeline.py ledger settle`, closing ledger rows fixed during a stale window.

Both exit 0 when the project does not link `pipeline.py`.
