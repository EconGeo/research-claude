---
name: checkpoint
description: >
  Session handoff — persists what happened in the current session to memory,
  SESSION_REPORT.md, and the research journal. Use when wrapping up a work session,
  before `/compact`, or when the user says "checkpoint", "save progress", "sync",
  "wrap up", "log this", or "handoff". Optionally pushes to Obsidian if the user
  has configured `.claude/state/obsidian-config.md`. Does NOT run briefings,
  calendar, or mail. Just gather, confirm, save.
argument-hint: "[--auto | --memory-only | --scaffold-only | --dry-run]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash
---

# Checkpoint: Session Handoff

Persists the session to three places, plus a gated fourth:

1. **Auto-memory** (`~/.claude/projects/.../memory/`) — learnings for future conversations
2. **`SESSION_REPORT.md`** — append-only log per `.claude/rules/logging.md`, at the repo root
   unless the project's `CLAUDE.md` moves it
3. **`quality_reports/research_journal.md`** — agent trail
4. **Obsidian vault** — optional, only when configured

Gather, write, report. **Never stop to ask "look right?"** — the user's own `CLAUDE.md` makes
every `/checkpoint` behave as `--auto`.

---

## Flow

### Step 1: Gather Context

Run in parallel (one message, several Bash calls):

```bash
basename "$(pwd)"
git log --oneline -10
git diff --stat
git diff --cached --stat
```

Then scan:
- `CLAUDE.md` header for the project name
- `quality_reports/plans/` for files modified today
- `SESSION_REPORT.md` (wherever the project's `CLAUDE.md` puts it) — the last entry, so the new
  one continues the history rather than repeating it
- `python3 .claude/scripts/pipeline.py state show` — what the staleness sweep in
  `.claude/rules/session-handoff.md` compares the plan's status claims against
- The conversation, for decisions, corrections and learnings that qualify for memory

### Step 2: Detect Obsidian Configuration

```bash
test -f .claude/state/obsidian-config.md && echo "OBSIDIAN: configured" || echo "OBSIDIAN: not configured"
```

If absent, Obsidian is inactive this session — proceed without it and do not offer to set it up.

### Step 3: Draft Updates

Compose the entries and go straight to Step 4. Under `--dry-run`, print them instead of saving.

### Step 4: Save Everything

Each section is independent — if one fails, the others still run.

#### 4a. Claude Code Auto-Memory

Memory is for **future conversations** — not what is useful only now, and not anything derivable
from the code or `git log`. The four entry types, when each qualifies, and the exclusion list are
in `.claude/skills/checkpoint/templates/memory-entry-types.md`. Update existing files rather than
duplicating, then update the `MEMORY.md` index.

**A `feedback` memory that corrects a pipeline skill, agent or rule** — rather than stating a
project preference — is also a ledger row and a Step 5 report line. Never edit the shared tree
and never prompt (`.claude/rules/meta-governance.md`, User corrections):

```bash
python3 .claude/scripts/ledger.py add --project "$(basename "$PWD")" \
  --target <shared file it would change> --note "<one generic sentence>"
```

The printed id goes on the report line. `/promote` reads the ledger and flags a target two
projects named.

#### 4b. SESSION_REPORT.md

Append-only; create with header `# Session Report — [Project Name]` if absent. Entry format:
`.claude/skills/checkpoint/templates/session-report-entry.md` (canonically
`.claude/rules/logging.md`).

#### 4c. quality_reports/research_journal.md

Append only if agent work happened this session. Entry format:
`.claude/skills/checkpoint/templates/research-journal-entry.md`.

#### 4d. Obsidian (only if `.claude/state/obsidian-config.md` exists)

Follow `.claude/skills/checkpoint/references/obsidian.md` (Sync).

### Step 4f. HANDOFF.md

If the project has one, regenerate from `.claude/templates/handoff.md` — never append
(`.claude/rules/session-handoff.md` R2).

### Step 5: Confirm

Run the three verifications the rules require. Each yields a **report line**, never a question:

- **Plan staleness sweep** — `.claude/rules/session-handoff.md` R1, mandatory every checkpoint.
  Re-read the active plan's status section against Step 1's state and **fix the plan in place**;
  do not record the drift elsewhere.
- **Handoff reference dry-run** — same rule, R3, when the project has a `HANDOFF.md`. Read the
  output; a file that legitimately lives outside the repo flags and is not suppressed.
- **`ai_use_log.md`** — `.claude/rules/ai-disclosure.md` Enforcement. Absent with no agent work
  is normal, not a failure.

Report what was saved:

```
Checkpoint saved:
- Memory: [updated/created N files | no changes]
- SESSION_REPORT.md: [entry added]
- research_journal.md: [entry added | skipped — no agent work]
- Obsidian: [entry added to Project Name | not configured]
- Plan staleness sweep: [none | fixed: <plan> | flagged: <plan>]
- Handoff reference dry-run: [clean | N unresolved | no HANDOFF.md]
- ai_use_log.md: [N entries | absent — no agent work this session]
- Pipeline improvement candidates: [none | N — <skill>: <one-line correction> (L-NNN)]
```

---

## Flags

| Flag | Effect |
|------|--------|
| `--auto` | Default behaviour, accepted for compatibility |
| `--memory-only` | Only update Claude Code memory |
| `--scaffold-only` | Update memory + SESSION_REPORT + research_journal, skip Obsidian |
| `--dry-run` | Show what would be saved, don't save |
| `--setup-obsidian` | Create `.claude/state/obsidian-config.md` from the example, per `.claude/skills/checkpoint/references/obsidian.md` (Setup) |

---

## Rules

- **Never invent progress.** Only log what actually happened — from git, the conversation, or
  the pipeline state.
- **Don't duplicate.** Check existing memory files and today's journal entry before writing.
- **`.claude/state/obsidian-config.md` is local-only** — user-specific paths, kept out of commits
  by `.gitignore`. Obsidian is opt-in; memory, SESSION_REPORT and the research journal work out of
  the box.
- **When Obsidian is active, its `Home.md` dashboard is the source of truth for project stages.**
  Don't contradict it.

Known failure points: `.claude/skills/checkpoint/gotchas.md`.
