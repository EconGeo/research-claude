---
name: tools
description: Utility commands — commit (with blocking quality/number/structure gates), render, validate-bib, lint, journal, learn. Replaces individual utility skills.
argument-hint: "[subcommand: commit | render | validate-bib | lint | journal | learn] [args] [--yes]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent
---

# Tools

Utility subcommands for project maintenance and infrastructure.

**Input:** `$ARGUMENTS` — subcommand followed by any arguments.

---

## Subcommands

### `/tools commit [message] [--yes]` — Git Commit

Stage changes, **verify the blocking gates**, confirm, commit, confirm again, open a PR, and
merge. Two confirmation gates (A before the commit, B before the PR and merge) wait for the
user; `--yes` answers both with their default so `/pipeline` and the live fixture tier do not
stall. **`--yes` never skips Step 0** — those are blocking safety gates, not waits, and only
an explicit "commit anyway" with a stated reason overrides them (R-42, R-132).

#### Step 0 — Quality gate (blocking, runs before branching)

**If the declared manuscript is among the changed files, run both
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
Then, **only if the project ships one**, run its own rubric scorer. This is
project-owned — `quality_score.py` at the project root in the projects that have it —
and is **not** part of research-claude, so test for it before calling it rather than
assuming it exists.

- **Score below 80 on any file: halt and report.** The user must fix, or override
  explicitly ("commit anyway", "skip quality gate"). Record any override *and its stated
  reason* in the commit message. A project without a scorer still runs the two gates above.

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
   `.env`, `.claude/state/`, or anything holding a secret.
   **Gate A — confirm the commit.** Show the branch, `git diff --cached --stat`, the Step 0
   results, and the exact commit message, then **wait**: `commit` / `edit the message` /
   `abort`. Under `--yes`, proceed as if `commit`.
4. `git commit`. If `$ARGUMENTS` is given use it verbatim; otherwise write a message that
   explains *why*, not *what*.
   **Gate B — confirm publication.** A push, a PR and a merge are outward-facing and hard to
   undo. Show the base branch, the PR title, and what will merge, then **wait**:
   `PR and merge` / `PR only` / `push only` / `stop here` (the commit stays local). Under
   `--yes`, proceed as if `PR and merge`.
5. Push, `gh pr create`.
6. `gh pr merge --merge --delete-branch` (not squash or rebase unless asked).
7. Report the PR URL and what merged (or, after `stop here` / `push only`, where the commit
   is and what remains).

**Never skip Step 0.** If the user insists, the override reason goes in the commit message.
`--yes` is not that insistence: it answers Gates A and B only.

### `/tools render [file]` — Quarto Render
Single-step render. There is no separate LaTeX build.

For the manuscript — resolve the declared name; never guess it:
```bash
MS=$(python3 .claude/scripts/pipeline.py manuscript) && quarto render "$MS"
```
`pipeline.py manuscript` refuses when `CLAUDE.md` declares no manuscript or more than one.

For talks (not the declared manuscript):
```bash
quarto render talks/[file]
```

Pass: exit 0, output artifact newer than the source, and the rendered page checked:
```bash
python3 .claude/scripts/check_render.py "${MS%.qmd}.pdf" --expect "<mandated phrases>"
```
That is write-gate item 4 (`.claude/rules/quarto-empirical.md`): unresolved `?@` refs, literal
`\commands`/`*markup*`/`<tags>`, doubled exhibit numbers, missing phrases, dropped columns
(`--columns "Table N: a,b,c"`). A clean render says nothing about hardcoded prose numbers —
that is `prose_number_check.py` (INV-11). Do not invoke xelatex or pandoc by hand unless
debugging a render failure — `quarto render` is the only build step.

### `/tools validate-bib` — Bibliography Validation
Cross-reference every citation key in the manuscript and `talks/*.qmd` against the project's
`.bib` (the file the manuscript YAML's `bibliography:` field declares — the script reads that
field rather than assuming a name).

```bash
python3 .claude/scripts/validate_bib.py
```

Quarto cross-reference prefixes (`@fig-`, `@tbl-`, `@eq-`, `@sec-`, …) are excluded — they
are not citations. **Output:** MISSING, UNUSED and DUPLICATE lists, reported to the user.
**Pass:** exit 0 — MISSING and DUPLICATE are both empty. UNUSED is informational, not a
defect: Zotero is the source of truth for what has been read
(`.claude/skills/lit-position/SKILL.md`), and the `.bib` is exported from it, so an entry the
manuscript does not yet cite is normal mid-draft. Never delete entries here.

### `/tools lint [file|dir]` — Mechanical Code Linting
Run grep-based checks on R/Python/Julia scripts against the coding standards' prohibited patterns. Catches mechanical violations before the coder-critic's judgment review.

```bash
"$CLAUDE_PROJECT_DIR"/.claude/hooks/lint-scripts.sh [target]
```

- **Single file:** `/tools lint scripts/acquire/01_download.py`
- **Directory:** `/tools lint scripts/acquire/` (recursive)
- **Default:** `/tools lint` (lints `scripts/acquire/` only — `.claude/hooks/lint-scripts.sh`'s one default target)
- **Explorations:** `/tools lint explorations/` — not covered by the default; run it separately
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
| `source()` inside a chunk (INV-19) | x | | | HIGH |
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
Bring `quality_reports/research_journal.md` up to date with the state file. The journal is
append-only, one entry per agent completion (`.claude/rules/logging.md`), and is written
**from** `quality_reports/pipeline_state.json` and `quality_reports/agent_dispatch.jsonl` —
never the reverse. It never decides where the pipeline starts; `pipeline.py next` does.

```bash
python3 .claude/scripts/pipeline.py state show          # components: score, critic, report, at
tail -20 quality_reports/agent_dispatch.jsonl            # completions: agent, timestamp
grep -n '^### ' quality_reports/research_journal.md      # entries already written
```

For every recorded component score and every logged completion with no journal entry naming
its report (or its agent and timestamp), append one entry in the format of
`.claude/skills/checkpoint/templates/research-journal-entry.md`. Do not edit or reorder
existing entries. **Pass:** every `report` path in `pipeline_state.json` appears in the journal.

### `/tools learn` — Extract Learnings
Extract a reusable multi-step workflow from the current session and propose it as a skill.

A **correction** to a pipeline skill, agent or rule is not handled here and is never applied
silently. It follows `.claude/rules/meta-governance.md` (User corrections): ask once at the
moment of the correction and land on yes with `/promote`; `/checkpoint` records every
candidate in the shared ledger (`.claude/scripts/ledger.py add`), and `/promote` flags a
target two projects named.

---

## Principles
- **Each subcommand is lightweight.** No multi-agent orchestration needed.
- **Render is one step.** `quarto render` handles citations and cross-references; there is no multi-pass build to manage.
- **validate-bib catches drift.** Run before commits to catch broken citations.
