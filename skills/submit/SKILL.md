---
name: submit
description: Submission pipeline — journal targeting, replication package, audit, archive deposit, and final gate. Replaces the old target-journal, audit-replication and data-deposit commands.
argument-hint: "[mode: target | package | audit | deposit | final] [journal name (optional)] [--yes]"
allowed-tools: Read,Grep,Glob,Write,Bash,Agent
---

# Submit

Submission pipeline with five modes covering journal selection through final verification.

**Input:** `$ARGUMENTS` — mode keyword, optionally followed by journal name.

---

## Modes

### `/submit target` — Journal Targeting
Get ranked journal recommendations.

Dispatch **journal-scout** (`.claude/agents/journal-scout.md`; `Agent`,
`subagent_type=journal-scout`) with the manuscript path, the paper type and the field. It
reads `.claude/references/journal-profiles.md` (long — that read is the scout's, not this
context's) and `.claude/references/discipline-cards.md`, and returns a ranked table of 5–10
journals — columns *contribution fit*, *methodology fit*, *audience*, *desk-reject risk*,
*AI-disclosure field* (from the profile) — with a one-line rationale for rank 1.

**Option gate** (`.claude/rules/option-gates.md`): present that table and wait (`--yes` takes
rank 1). Neither this skill nor the scout has a web tool; "recent publications" is judged
from the profile's stated scope, not a search.

Save the full table to `quality_reports/journal_recommendations_[date].md` with the pick
marked. `/review --peer`, `/review --stress` and `/submit final` read the pick from that file
when no journal is given on the command line.

### `/submit package` — Build Replication Package
Assemble AEA-compliant replication package.

**Agents:** coder, then coder-critic (paired per `.claude/rules/registry.yaml`)

Produces:
- the declared manuscript, `references.bib`, `templates/`, `data/raw/data_manifest.md`, `scripts/acquire/`, `renv.lock`, README (`.claude/skills/submit/templates/replication-readme.md`) — assembled under `replication/`
Save to `replication/`

coder-critic returns its report as text; session saves it to `quality_reports/reviews/coder-critic_<date>.md` first, then records: `python3 .claude/scripts/pipeline.py state record-score code <score> --critic coder-critic --deductions <total> --report quality_reports/reviews/coder-critic_<date>.md`.

### `/submit audit` — Audit Replication Package
Verify replication package completeness.

**Agent:** Verifier (submission mode — 10 checks). `.claude/agents/verifier.md` is the only
definition; the list below is an index into it, not a restatement. (A separate
`audit-10-checks.md` copy used to sit beside this skill; it drifted from the verifier twice and
was deleted on 2026-09-24.)

Checks:
1. Render
2. Chunks execute
3. References resolve
4. Fresh
4b. Prose numbers computed
4c. Content invariants
5. Package inventory
6. Dependencies
7. Data provenance
8. Execution
9. Cross-reference
10. README

Save the report to `quality_reports/verification_report.md`. Record: `python3 .claude/scripts/pipeline.py state record-score replication <score> --critic verifier --report quality_reports/verification_report.md`.

### `/submit deposit [journal]` — Deposit the Replication Package
Prepare the replication package for deposit at a public archive and record that it was deposited.

**Performed by this skill** (no agent). Depositing to an external repository mints a permanent,
public, often DOI-bearing record — an irreversible action this skill does not perform on its own.
It prepares everything the repository needs and records the result once the user confirms the
upload happened on the repository's own site.

**Preconditions:** `/submit package` has assembled `replication/`, and `/submit audit` has
recorded a `replication` score — refuse and name whichever is missing.

Workflow:
1. **Identify the repository.** If `[journal]` is given, read its entry in
   `.claude/references/journal-profiles.md` for the named archive (openICPSR, Dataverse, Zenodo,
   AEA Data and Code Repository, …) and any policy language (e.g. "deposit mandatory before
   acceptance"). If no journal is given or its profile names none, ask the user which repository
   to target.
2. **Check package completeness** against `.claude/skills/submit/templates/replication-readme.md`'s
   sections (Data Availability, Computational Requirements, Description of Programs, Instructions
   for Replication) — every `[bracketed placeholder]` must be filled in `replication/README.md`.
3. **Write the deposit manifest** to `quality_reports/deposit_manifest_[date].md`: repository
   name, license, embargo (if any), the file list under `replication/` to upload, and a step-by-step
   checklist of the manual actions the user performs on the repository's site (create the
   deposit, upload the files, set metadata, reserve/mint the DOI).
4. **Stop and wait.** Present the manifest and checklist; do not proceed until the user confirms
   the upload is complete and reports the resulting URL/DOI.
5. **Record it:** `python3 .claude/scripts/pipeline.py state record-deposit --repository <name> --url <url> --report quality_reports/deposit_manifest_[date].md`.

### `/submit final [journal]` — Final Submission Gate
Full verification + score enforcement + submission checklist.

Workflow — run the steps in order. Only an explicit **STOP** ends the run early; a blocker
you can already see in `state show` or `score` does not skip Steps 1–2, and a static reading of
the state never stands in for them.
1. **Comprehensive review.** Run `python3 .claude/scripts/pipeline.py state show`. If every
   scored component's `at` is within the last 7 days, the review is current — say so and
   continue. Otherwise run `/review` first.
2. **Replication audit — unconditional.** Dispatch the Verifier (`Agent`,
   `subagent_type=verifier`) in submission mode exactly as `/submit audit` above does, save its
   report to `quality_reports/verification_report.md`, and run `record-score replication`. An
   existing verification report does not substitute (Principles: *Don't skip verification*).
2.5. **AI Disclosure Audit** — read `ai_use_log.md` and the manuscript AI Use Statement:
   - If `ai_use_log.md` missing or empty: **STOP** — "AI disclosure log missing. Run agents or manually populate ai_use_log.md before submission. See .claude/rules/ai-disclosure.md."
   - Read the `## AI Use Statement {.unnumbered}` section in `manuscript_<project>.qmd`
   - If the statement is missing or still contains placeholder text: **STOP** — "AI Use Statement not populated. Populate from ai_use_log.md using the Wiley/COPE-aligned template before submission."
   - If a journal is specified via `$ARGUMENTS`: check that the disclosure location matches that journal's `**AI disclosure:**` field in `.claude/references/journal-profiles.md`
   - If all checks pass: report "AI disclosure audit: [N] log entries found, statement populated ✓"
2.6. **Hallucination check (CoVe).** Run `/verify-claims` (ai-audit, vendored) against the
   declared manuscript. Save its report to `quality_reports/verify_claims_[date].md`, then record
   the result: `python3 .claude/scripts/pipeline.py state record-verify-claims --report <path>
   --result pass|fail`. The `submission` gate below refuses without this — a scored 95 says
   nothing about a hallucinated citation or number, which is exactly what CoVe checks and nothing
   else does.
3. Check score gate: `python3 .claude/scripts/pipeline.py score --gate submission` — FAILs on a
   missing, failing, or since-deleted `verify_claims` result even at a qualifying score.
3.5. **Coverage check (R-133).** `pipeline.py score` weights only components that carry a
   score, so a PASS can rest on one scored component out of eight. Run
   `python3 .claude/scripts/pipeline.py state show` and list every component the paper
   actually has. If any of them is unscored, report it by name and treat the gate as
   **not met** — an unscored component is not counted at all, it does not fail.
4. Save gate summary to `quality_reports/quality_gate_[date].md`
5. If PASS: generate cover letter draft (`.claude/skills/submit/templates/cover-letter.qmd`) + submission checklist (`.claude/skills/submit/templates/submission-checklist.md`)
6. If FAIL: list blocking issues and stop

Before reporting PASS or FAIL, read `.claude/skills/submit/gotchas.md` — the coverage trap in
Step 3.5 and the cold-cache render are both there.

---

## Bundled Resources (Level 3)

| Resource | Path | When |
|----------|------|------|
| Submission checklist | `.claude/skills/submit/templates/submission-checklist.md` | `/submit final` — pre-submission verification |
| Cover letter | `.claude/skills/submit/templates/cover-letter.qmd` | `/submit final` — draft cover letter |
| Replication README | `.claude/skills/submit/templates/replication-readme.md` | `/submit package` — AEA-compliant README |
| Gotchas | `.claude/skills/submit/gotchas.md` | Always — known failure points |

---

## Principles
- **Score >= 95 + every SCORED component >= 80. No exceptions.**
  `pipeline.py score` weights only components that carry a score, so a component nothing ever scored does not hold the gate closed — it silently is not in it. Run `pipeline.py state show` and confirm every component the paper actually has is present before treating a PASS as a submission decision.
- **AI disclosure must be populated before submission.** `ai_use_log.md` must exist and have entries; the AI Use Statement must not be a placeholder. No exceptions.
- **`/verify-claims` must have recorded a passing result.** The `submission` gate refuses without a `verify_claims` entry whose report still exists on disk — a stale or deleted report reopens it.
- **Don't skip verification.** Even if reports exist, check they're recent.
- **If it fails, stop.** Don't generate materials for a failing paper.
- **Cover letter is a draft.** User must review before sending.
