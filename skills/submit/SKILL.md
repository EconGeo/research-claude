---
name: submit
description: Submission pipeline — journal targeting, replication package, audit, and final gate. Replaces /submit, /target-journal, /audit-replication, /data-deposit.
argument-hint: "[mode: target | package | audit | final] [journal name (optional)]"
allowed-tools: Read,Grep,Glob,Write,Bash,Task
---

# Submit

Submission pipeline with four modes covering journal selection through final verification.

**Input:** `$ARGUMENTS` — mode keyword, optionally followed by journal name.

---

## Modes

### `/submit target` — Journal Targeting
Get ranked journal recommendations.

**Agent:** Orchestrator (journal selection function)

Considers: contribution fit, methodology fit, audience fit, recent publications, desk rejection risk. Consults .claude/references/domain-profile.md for journal tiers.

Output: Ranked list of 3 target journals with rationale.
Save to `quality_reports/journal_recommendations_[date].md`

### `/submit package` — Build Replication Package
Assemble AEA-compliant replication package.

**Agents:** Coder + Verifier

Produces:
- Master script that runs all analyses end-to-end
- README with data sources, computational requirements, instructions
- Data documentation and codebook
- Organized file structure per AEA standards
Save to `paper/replication/`

### `/submit audit` — Audit Replication Package
Verify replication package completeness.

**Agent:** Verifier (submission mode — 10 checks)

Checks:
1. Master script exists and runs
2. All tables reproduce
3. All figures reproduce
4. README complete
5. Data documentation present
6. Numbered script order
7. Dependencies listed
8. Runtime documented
9. Output paths match paper references
10. No hardcoded paths

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
3. Check score gate: aggregate >= 95, all components >= 80
4. Save gate summary to `quality_reports/quality_gate_[date].md`
5. Generate HTML quality gate report and refresh dashboard:
```bash
python3 scripts/generate_html_report.py quality-gate quality_reports/quality_gate_[date].md
python3 scripts/generate_dashboard.py
```
6. If PASS: generate cover letter draft + submission checklist
7. If FAIL: list blocking issues and stop

---

## Bundled Resources (Level 3)

| Resource | Path | When |
|----------|------|------|
| Submission checklist | `templates/submission-checklist.md` | `/submit final` — pre-submission verification |
| Cover letter | `templates/cover-letter.tex` | `/submit final` — draft cover letter |
| Replication README | `templates/replication-readme.md` | `/submit package` — AEA-compliant README |
| Audit checklist | `templates/audit-10-checks.md` | `/submit audit` — verifier submission mode |
| Gotchas | `gotchas.md` | Always — known failure points |

---

## Principles
- **Score >= 95 + all components >= 80. No exceptions.**
- **AI disclosure must be populated before submission.** `ai_use_log.md` must exist and have entries; the AI Use Statement must not be a placeholder. No exceptions.
- **Don't skip verification.** Even if reports exist, check they're recent.
- **If it fails, stop.** Don't generate materials for a failing paper.
- **Cover letter is a draft.** User must review before sending.
