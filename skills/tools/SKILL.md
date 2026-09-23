---
name: tools
description: Utility commands — commit (with blocking quality/number/structure gates), render, validate-bib, lint, journal, context-status, learn. Replaces individual utility skills.
argument-hint: "[subcommand: commit | render | validate-bib | lint | journal | context | learn] [args]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent
---

# Tools

Utility subcommands for project maintenance and infrastructure.

**Input:** `$ARGUMENTS` — subcommand followed by any arguments.

---

## Subcommands

### `/tools commit [message]` — Git Commit

Stage changes, **verify the blocking gates**, commit, open a PR, and merge.

#### Step 0 — Quality gate (blocking, runs before branching)

For every changed `.qmd`, `.tex` or `.R` file with a rubric:

```bash
python3 scripts/quality_score.py <changed-file-paths>
```

**If the declared manuscript is among the changed files, also run the
single-source-of-truth gates. These are blocking, not advisory:**

```bash
python3 .claude/scripts/prose_number_check.py <manuscript>       # INV-11
python3 .claude/scripts/quarto_structure_check.py <manuscript>   # INV-13/INV-25
```

- `prose_number_check.py` non-zero = a numeric literal in prose is neither derived
  from code nor explained. Bind it to an inline `` `r ` `` expression, or add a row to
  `quality_reports/prose_number_allowlist.csv` **with a reason**. Do not override.
- `quarto_structure_check.py` non-zero = the document is not native Quarto — a table or
  figure chunk is mislabelled, an exhibit is referenced by typed number instead of `@ref`,
  a caption is set in R instead of `#| tbl-cap:`, or a cross-reference does not resolve.
- **Score below 80 on any file: halt and report.** The user must fix, or override
  explicitly ("commit anyway", "skip quality gate"). Record any override *and its stated
  reason* in the commit message.

**Why these are blocking.** A clean render proves nothing about either class of defect:
a render cannot fail on a literal, because a literal is not an expression, and it cannot
fail on a typed "Table 4", because typed text is valid prose. A manuscript once scored
100/100 EXCELLENCE with zero issues while shipping a sentence that stated the opposite
sign of its own table, and four provably wrong numbers reached a manuscript through
exactly this gap. The quality score checks hardcoded *paths*, not *numbers* or *structure*.

Then spawn the **verifier** agent (`Agent`, `subagent_type=verifier`) for render and
cross-reference checks. Report pass/fail before committing.

#### Steps 1–7

1. `git status`, `git diff --stat`, `git log --oneline -5`.
2. Create a branch — **never commit directly to main**.
3. Stage named files. Never `git add -A`; never stage `.claude/settings.local.json`,
   `.env`, or anything holding a secret.
4. Commit. If `$ARGUMENTS` is given use it verbatim; otherwise write a message that
   explains *why*, not *what*.
5. Push, `gh pr create`.
6. `gh pr merge --merge --delete-branch` (not squash or rebase unless asked).
7. Report the PR URL and what merged.

**Never skip Step 0.** If the user insists, the override reason goes in the commit message.

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
Extract a reusable multi-step workflow from the current session and propose it as a skill.

A **correction** to a pipeline skill, agent or rule is not handled here and is never applied
silently. It follows `.claude/rules/meta-governance.md`: `/checkpoint` names it as an improvement
candidate, it must hold across 3+ projects, and `/promote` is the only thing that lands it.

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
