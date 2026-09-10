---
name: submit
description: Submission pipeline — journal targeting, replication package, audit, and final gate. Replaces the old target-journal, audit-replication and data-deposit commands.
argument-hint: "[mode: target | package | audit | final] [journal name (optional)]"
allowed-tools: Read,Grep,Glob,Write,Bash,Agent
---

# Submit

Submission pipeline with four modes covering journal selection through final verification.

**Input:** `$ARGUMENTS` — mode keyword, optionally followed by journal name.

---

## Modes

### `/submit target` — Journal Targeting
Get ranked journal recommendations.

**Performed by this skill** (no agent): read `.claude/references/journal-profiles.md` and `.claude/references/discipline-cards.md`, rank three journals.

Considers: contribution fit, methodology fit, audience fit, recent publications, desk rejection risk.

Output: Ranked list of 3 target journals with rationale.
Save to `quality_reports/journal_recommendations_[date].md`

### `/submit package` — Build Replication Package
Assemble AEA-compliant replication package.

**Agents:** coder → coder-critic

Produces:
- the declared manuscript, `references.bib`, `templates/`, `data/raw/data_manifest.md`, `scripts/acquire/`, `renv.lock`, README (`.claude/skills/submit/templates/replication-readme.md`) — assembled under `replication/`
Save to `replication/`

### `/submit audit` — Audit Replication Package
Verify replication package completeness.

**Agent:** Verifier (submission mode — 10 checks, full text in `.claude/agents/verifier.md`)

Checks:
1. Render
2. Chunks execute
3. References resolve
4. Fresh
4b. Prose numbers computed
5. Package inventory
6. Dependencies
7. Data provenance
8. Execution
9. Cross-reference
10. README

### `/submit final [journal]` — Final Submission Gate
Full verification + score enforcement + submission checklist.

Workflow:
1. Run comprehensive review if not done recently
2. Run replication audit
2.5. **AI Disclosure Audit** — read `ai_use_log.md` and the manuscript AI Use Statement:
   - If `ai_use_log.md` missing or empty: **STOP** — "AI disclosure log missing. Run agents or manually populate ai_use_log.md before submission. See .claude/rules/ai-disclosure.md."
   - Read the `## AI Use Statement {.unnumbered}` section in `manuscript_<project>.qmd`
   - If the statement is missing or still contains placeholder text: **STOP** — "AI Use Statement not populated. Populate from ai_use_log.md using the Wiley/COPE-aligned template before submission."
   - If a journal is specified via `$ARGUMENTS`: check that the disclosure location matches that journal's `**AI disclosure:**` field in `.claude/references/journal-profiles.md`
   - If all checks pass: report "AI disclosure audit: [N] log entries found, statement populated ✓"
3. Check score gate: `python3 .claude/scripts/pipeline.py score --gate submission`
4. Save gate summary to `quality_reports/quality_gate_[date].md`
5. If PASS: generate cover letter draft (`.claude/skills/submit/templates/cover-letter.qmd`) + submission checklist (`.claude/skills/submit/templates/submission-checklist.md`)
6. If FAIL: list blocking issues and stop

---

## Bundled Resources (Level 3)

| Resource | Path | When |
|----------|------|------|
| Submission checklist | `.claude/skills/submit/templates/submission-checklist.md` | `/submit final` — pre-submission verification |
| Cover letter | `.claude/skills/submit/templates/cover-letter.qmd` | `/submit final` — draft cover letter |
| Replication README | `.claude/skills/submit/templates/replication-readme.md` | `/submit package` — AEA-compliant README |
| Audit checklist | `.claude/skills/submit/templates/audit-10-checks.md` | `/submit audit` — verifier submission mode |
| Gotchas | `.claude/skills/submit/gotchas.md` | Always — known failure points |

---

## Principles
- **Score >= 95 + all components >= 80. No exceptions.**
- **AI disclosure must be populated before submission.** `ai_use_log.md` must exist and have entries; the AI Use Statement must not be a placeholder. No exceptions.
- **Don't skip verification.** Even if reports exist, check they're recent.
- **If it fails, stop.** Don't generate materials for a failing paper.
- **Cover letter is a draft.** User must review before sending.
