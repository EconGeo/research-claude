---
name: tools
description: Utility commands — commit, render, validate-bib, lint, journal, context-status, learn. Replaces individual utility skills.
argument-hint: "[subcommand: commit | render | validate-bib | lint | journal | context | learn] [args]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent
---

# Tools

Utility subcommands for project maintenance and infrastructure.

**Input:** `$ARGUMENTS` — subcommand followed by any arguments.

---

## Subcommands

### `/tools commit [message]` — Git Commit
Stage changes, create commit, optionally create PR and merge.
- Run git status to identify changes
- Stage relevant files (never stage .env or credentials)
- Create commit with descriptive message
- If quality score available and >= 80, note in commit

### `/tools render [file]` — Quarto Render
Single-step render. There is no separate LaTeX build.

For the manuscript:
```bash
quarto render manuscript_<project>.qmd
```

For talks:
```bash
quarto render talks/[file]
```

Pass: exit 0, output artifact newer than the source. Then grep the render log
for `ERROR`/`WARNING` and the output for unresolved cross-references (`?@fig-`,
`?@tbl-`). A clean render says nothing about hardcoded prose numbers — that is
`prose_number_check.py` (INV-11).

### `/tools validate-bib` — Bibliography Validation
Cross-reference all `@key` citations in the manuscript and talk `.qmd` files against the project `.bib`.
Report: missing entries, unused entries, duplicate keys.

### `/tools lint [file|dir]` — Mechanical Code Linting
Run grep-based checks on R/Python/Julia scripts against the coding standards' prohibited patterns. Catches mechanical violations before the coder-critic's judgment review.

```bash
"$CLAUDE_PROJECT_DIR"/.claude/hooks/lint-scripts.sh [target]
```

- **Single file:** `/tools lint scripts/acquire/01_download.py`
- **Directory:** `/tools lint scripts/acquire/` (recursive)
- **Default:** `/tools lint` (lints `scripts/acquire/` and `explorations/`)
- **`.qmd` file:** also lints the R chunks of a `.qmd` (`.claude/scripts/qmd_chunks.py`)

**What it checks (drawn from `.claude/references/coding-standards-*.md`):**

| Check | R | Python | Julia | Severity |
|-------|---|--------|-------|----------|
| Absolute paths | x | x | x | HIGH |
| `setwd()` / `os.chdir()` / `cd()` | x | x | x | HIGH |
| Missing seed (stochastic code) | x | x | x | HIGH |
| `install.packages()` / `pip install` | x | x | | HIGH |
| `rm(list = ls())` | x | | | MEDIUM |
| `T`/`F` literals | x | | | MEDIUM |
| `sapply()` | x | | | MEDIUM |
| `attach()`/`detach()` | x | | | MEDIUM |
| `<<-` global assignment | x | | | MEDIUM |
| `stargazer` / `plyr` | x | | | MEDIUM |
| `set.seed()` position (after line 30) | x | | | MEDIUM |
| Wildcard imports | | x | | MEDIUM |
| `np.random.seed()` global state | | x | | MEDIUM |
| Bare `except:` | | x | | MEDIUM |
| `eval`/`@eval` runtime | | | x | MEDIUM |
| Late `library()`/`import`/`using` | x | x | x | LOW |
| `print()` for status | x | | | LOW |
| `require()` | x | | | LOW |
| `1:n` patterns | x | | | LOW |

**Output:** Findings by file with severity, line number, and fix suggestion. Always advisory (exit 0).

**When to use:**
- Before `/review --code` — catches mechanical violations instantly
- Before commits — quick sanity check
- The coder-critic focuses on judgment (strategy alignment, numerical plausibility, design); this catches the grep-able stuff

### `/tools journal` — Research Journal
Regenerate the research journal timeline from quality reports and git history.
Shows chronological record of agent actions, phase transitions, scores, decisions.

### `/tools context` — Context Status
Show current context status and session health.
Check context usage, whether auto-compact is approaching, what state will be preserved.

### `/tools learn` — Extract Learnings
Extract reusable knowledge from the current session. Auto-memory handles corrections automatically; this is for multi-step workflows worth turning into a full skill.

---

## Bundled Resources (Level 3)

| Resource | Path | When |
|----------|------|------|
| Gotchas | `gotchas.md` | Always — known failure points |

---

## Principles
- **Each subcommand is lightweight.** No multi-agent orchestration needed.
- **Render is one step.** `quarto render` handles citations and cross-references; there is no multi-pass build to manage.
- **validate-bib catches drift.** Run before commits to catch broken citations.
