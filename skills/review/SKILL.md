---
name: review
description: All quality reviews — routes to appropriate critics based on target file type and flags. Replaces the old paper-excellence, proofread, econometrics-check, review-r and review-paper commands.
argument-hint: "[file path] Options: --peer [journal], --stress [journal], --methods, --theory [target], --proofread, --code [file], --replicate [language], --all"
allowed-tools: Read,Grep,Glob,Write,Bash,Agent
---

# Review

Unified review command that routes to the appropriate critic agents based on the target and flags.

**Input:** `$ARGUMENTS` — file path and/or flags.

---

## Routing Logic

### Auto-detect by target
- the declared manuscript (`python3 .claude/scripts/pipeline.py manuscript`) or no file → **Comprehensive review** (writer-critic + strategist-critic + verifier)
- a file under `scripts/acquire/` or `explorations/` (`.R`, `.py`, `.jl`, `.qmd`) → **Code review** (coder-critic standalone)
- `talks/*.qmd` → **Talk review** (storyteller-critic)

### Explicit flags (override auto-detect)
- `--peer` `[journal]` → **Full peer review** (editor desk review → referee dispatch → editorial decision)
- `--peer --r2` `[journal]` → **R&R second round** (same referees, same dispositions, memory of prior review)
- `--stress` `[journal]` → **Hostile stress test** (same flow, adversarial referee dispositions)
- `--methods` → **Causal audit** (strategist-critic standalone, 4-phase review)
- `--theory` `[target]` → **Proof audit** (theorist-critic standalone, 4-phase review — logical validity, assumption minimality, citations, linkage)
- `--proofread` → **Manuscript polish** (writer-critic standalone, 6 categories)
- `--code` `[file]` → **Code review** (coder-critic standalone, categories 5-16)
- `--replicate` `[language]` → **Cross-language replication** (Coder re-implements the manuscript's estimation chunks + coder-critic + comparison against tolerances)
- `--all` or no file → **Paper excellence** (all critics in parallel + weighted score — theorist-critic included when a theory section is present)

---

## Mode Details

### Comprehensive Review (default for the declared manuscript)
Dispatch in parallel:
1. **strategist-critic** — causal design audit (4 phases). Save report to `quality_reports/reviews/strategist-critic_<date>.md`. Record: `python3 .claude/scripts/pipeline.py state record-score strategy <score> --critic strategist-critic --deductions <total> --report quality_reports/reviews/strategist-critic_<date>.md`.
2. **writer-critic** — manuscript polish (6 categories). Save report to `quality_reports/reviews/writer-critic_<date>.md`. Record: `python3 .claude/scripts/pipeline.py state record-score manuscript <score> --critic writer-critic --deductions <total> --report quality_reports/reviews/writer-critic_<date>.md`.
3. **verifier** — standard checks 1–4c (`.claude/agents/verifier.md`). Save report to `quality_reports/verification_report.md`. Record: `python3 .claude/scripts/pipeline.py state record-score replication <score> --critic verifier --report quality_reports/verification_report.md`.
Compute weighted aggregate score from the recorded component scores.

**Save each report the moment its critic returns**, and record that score then — not after all
three. Critics are read-only and return their reports as text; this session writes them, so a
session that dies before the last critic finishes loses every report not yet on disk (observed:
strategist-critic done, report unsaved, run lost).

**Check the tree around the verifier.** Record `git status --porcelain` before dispatching it and
again when it returns. Put every tracked path that changed — other than the manuscript's rendered
outputs — in front of the user, and keep it out of any commit of the scores. Do not revert it
unasked. The verifier is told not to run a project's own gate scripts; this check is what notices
when one did anyway (observed: a project gate restamped two committed reports).

### Full Peer Review (`--peer [journal]`)

Simulates a realistic journal submission. Three phases, orchestrated sequentially.

#### Phase 1: Editor Desk Review
Dispatch the **editor** agent with the paper and target journal.

The editor:
1. Reads the paper (abstract, intro, contribution, identification, results)
2. Searches the literature via WebSearch to verify novelty claims
3. Decides: **DESK REJECT** or **SEND TO REFEREES**
4. If desk reject → report with reasons + suggested alternative journals. Done.
5. If send to referees → editor selects referee dispositions and pet peeves from the journal's **Referee pool** (see .claude/references/journal-profiles.md). The six dispositions are defined in `.claude/skills/review/templates/disposition-pool.md`; the peeve pools and sampling rules are in `.claude/agents/editor.md`.

#### Phase 2: Referee Reports
The editor's referee assignment specifies for each referee:
- **Disposition** (one of: STRUCTURAL, CREDIBILITY, MEASUREMENT, POLICY, THEORY, SKEPTIC)
- **Critical pet peeve** (one from the critical pool)
- **Constructive pet peeve** (one from the constructive pool)

Dispatch **domain-referee** and **methods-referee** in parallel, each receiving:
1. The paper manuscript
2. The target journal name (for .claude/references/journal-profiles.md calibration)
3. Their assigned disposition and pet peeves, injected into the prompt verbatim from
   `.claude/skills/review/templates/peer-review-prompts.md`

Both reviews are independent and blind — neither referee sees the other's report. Each
referee agent enforces its own "What would change my mind" requirement on every major
comment.

#### Phase 3: Editorial Decision
Dispatch the **editor** agent again with both referee reports.

The editor:
1. Classifies each concern as FATAL / ADDRESSABLE / TASTE
2. When referees disagree, takes a side and explains why
3. Produces a decision letter: Accept / Minor Revisions / Major Revisions / Reject
4. Lists MUST address, SHOULD address, and MAY push back items

Record: `python3 .claude/scripts/pipeline.py state record-score referees <score> --critic editor --report quality_reports/peer_review_<manuscript-stem>/editorial_decision.md`.

#### Save Reports
Save all outputs to `quality_reports/peer_review_<manuscript-stem>/`:
- `desk_review.md` (Phase 1)
- `referee_domain.md` (Phase 2)
- `referee_methods.md` (Phase 2)
- `editorial_decision.md` (Phase 3)

### R&R Second Round (`--peer --r2 [journal]`)

Continues the review cycle after the author has revised the paper.

1. **Load prior review state** — read the previous referee reports and editorial decision from
   `quality_reports/peer_review_<manuscript-stem>/`
2. **Dispatch with `--r2`** (or `--r3`). The editor and both referee agents own the rest: skip the
   desk review, reuse the round-1 dispositions and peeves, classify each prior concern as
   Resolved / Partially resolved / Not addressed, and narrow the decision options by round.
   Max 3 rounds — the editor's patience runs out, just like real life.
3. **Append the round prompt** from `.claude/skills/review/templates/peer-review-prompts.md`
4. **Save reports** with an `_r2` or `_r3` suffix to `quality_reports/peer_review_<manuscript-stem>/`
   (e.g. `editorial_decision_r2.md`)

### Hostile Stress Test (`--stress [journal]`)

Same three-phase flow as `--peer`, dispatched with `--stress`. The editor forces both referees to
SKEPTIC and doubles the critical peeves; append the hostile block from
`.claude/skills/review/templates/peer-review-prompts.md` to each referee prompt. Pre-submission
only — the score is advisory.

### Code Review (`--code` or auto-detect .R/.py/.jl/.qmd under `scripts/acquire/` or `explorations/`)

**Step 1: Mechanical lint** — run the grep-based linter first:
```bash
"$CLAUDE_PROJECT_DIR"/.claude/hooks/lint-scripts.sh [file]
```
Include the lint report in the coder-critic's input so it can skip already-flagged patterns and focus on judgment calls.

**Step 2: Judgment review** — dispatch **coder-critic** in standalone mode.

#### Code review checklist

The 16 categories are `.claude/skills/review/templates/code-review-16-categories.md`, which
coder-critic reads for itself. Categories 1–4 (strategic alignment) run only within the pipeline
or via `--methods`; standalone runs cover code quality only (categories 5–16).

Severity calibration for issues not already in a deduction table is in
`.claude/skills/review/config/scoring-rubrics.md` (Coder-Critic).

**Do NOT edit any source files.** Reports only; fixes come later, from the user or the Coder.

Save report to `quality_reports/reviews/coder-critic_<date>.md`

**When the target is the declared manuscript** (`--code <manuscript>` — the adoption route in
`.claude/skills/pipeline/references/adopt.md`), the full checklist applies. Categories 1–4 are
assessed against `quality_reports/strategy/<project>/strategy_memo.md` when it exists and against
the manuscript's own design section when it does not — the report says which. Record:
`python3 .claude/scripts/pipeline.py state record-score code <score> --critic coder-critic --deductions <total> --report quality_reports/reviews/coder-critic_<date>.md`.
A standalone review under `scripts/acquire/` or `explorations/` records nothing — `code` is the
manuscript's analysis, not acquisition or exploration code.

### Causal Audit (`--methods`)

Dispatch **strategist-critic** standalone for a full 4-phase causal inference review, per
`.claude/skills/review/templates/causal-audit-4-phases.md`.

The assessment label (SOUND / MINOR ISSUES / MAJOR ISSUES / CRITICAL ERRORS) is reported beside
the score, not instead of it. The score is 100 minus the fixed per-severity deductions in
`.claude/skills/review/config/scoring-rubrics.md` (Strategist-Critic).

Save report to `quality_reports/reviews/strategist-critic_<date>.md`

### Manuscript Polish (`--proofread`)
Dispatch **writer-critic** standalone:
- 6 categories: structure, claims-evidence, ID fidelity, writing, grammar, render
- Save report to `quality_reports/reviews/writer-critic_<date>.md`

### Cross-Language Replication (`--replicate [language]`)
Coder re-implements the manuscript's estimation chunks in `explorations/replicate_<language>.qmd`;
coder-critic reviews; compare against the tolerances and known divergence sources in
`.claude/skills/review/templates/replication-comparison.md`.

Never writes the manuscript. Save the replicated script and comparison report to
`quality_reports/reviews/replication_<language>_<date>.md`.

---

## Verifier Pass/Fail Definition
The definition is `.claude/agents/verifier.md`, and only there: standard checks 1–4c for the
declared manuscript (4c is the content invariants it treats as automatic FAIL), its scope note
for acquisition and exploration scripts, and submission checks 5–10 for a replication package.
It is deliberately not restated here. A restated copy once omitted 4c, and two papers passed
this file's version while failing the agent's.
Verifier score maps to 0 (FAIL) or 100 (PASS).

---

## Scoring

| Mode | Blocking? | Gate |
|------|-----------|------|
| Comprehensive | Yes | 80 commit, 90 PR |
| Peer Review | Yes | Editorial decision |
| Stress Test | Advisory | Reported, non-blocking |
| Code Review | Yes | 80 commit |
| Causal Audit | Yes | 80 commit |
| Proofread | Yes (paper), Advisory (talks) | 80 commit |

