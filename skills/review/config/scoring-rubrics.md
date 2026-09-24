# Scoring Rubrics -- All Critics

Consolidated deduction tables from all critic agents. Each critic starts at 100 and deducts for issues found. Floor at 0.

**Report the deduction total as well as the score** — `**Score:** 0 · **Deductions:** 185` — and
record both: `pipeline.py state record-score <component> <score> --deductions <total> …`. A floor
erases the ranking: deductions of 185 and 817 both score 0, and only the total says which paper
is closer to 80. An issue is deducted once, under the row that fits it best, however many phases
or categories it surfaces in.

---

## Writer-Critic (Manuscript Review)

### Critical (blocking)

| Issue | Deduction |
|-------|-----------|
| Manuscript does not render | -20 |
| Causal language without identification (INV-8) | -20 |
| Claim CONTRADICTED by its evidence (Claim–Evidence Table) | -25 per |
| Claim UNSUPPORTED (no evidence in the manuscript) | -15 per |
| Claim OVERSTATED | -10 per |
| Claim UNVERIFIABLE | -5 per |
| Numbers in text don't match tables (INV-11) | -10 per, max -30 |
| Strategy section misrepresents the actual design | -15 |
| Missing table notes on any table (INV-1) | -5 per, max -15 |
| Missing figure notes on any figure (INV-2) | -5 per, max -15 |

### Major (quality)

| Issue | Deduction |
|-------|-----------|
| Voice tone mismatch (when style guide exists) | -10 |
| AI vocabulary (3+ instances) | -2 per, max -10 |
| Missing JEL codes or keywords (INV-6) | -5 |
| Sentence length median off by >5 words | -5 |
| Format block violates `quarto-pdf.md`/`quarto-word.md` | -5 |
| Uniform sentence length (no variation) | -5 |

### Minor (polish)

| Issue | Deduction |
|-------|-----------|
| Filler phrases | -2 per, max -6 |
| Announcements | -2 per, max -6 |
| Em dash overuse | -3 |
| Rule of three | -3 |
| Paragraph openings don't match style guide | -3 per, max -9 |
| Unresolved references | -3 per |
| Render warnings | -1 per, max -5 |

---

## Coder-Critic (Manuscript Chunks)

Starts at 100. The blocking table is `.claude/rules/quarto-empirical.md` "What the Coder-Critic
Checks" — it is not restated here; cite it by row. Additional rows:

### Critical (strategic)
| Issue | Deduction |
|---|---|
| Domain-specific bugs (clustering, estimand) | -30 |
| Chunks do not implement the strategy memo | -25 |
| Render fails on any chunk | -25 |
| Sign of main result implausible | -20 |
| Missing robustness checks from memo | -15 |
| Wrong clustering level | -15 |
| Optimizer did not converge (structural) | -15 |
| Naming map absent from the setup chunk | -10 |

### Major (numerical discipline)
| Issue | Deduction |
|---|---|
| Float comparison with `==` | -10 |
| No CDF clamping / no inverse-link guards | -10 |
| Magnitude implausible (10× literature) | -10 |
| Growing vectors in loops (INV-17) | -5 |
| Missing `stopifnot()` preconditions on setup-chunk helpers | -5 |

### Minor
| Issue | Deduction |
|---|---|
| Stale cache (`fresh` predicate fails after a raw-file change) | -5 |
| Chunk label not in the documented DAG | -3 |
| Console output in a chunk (`print()` for status) | -3 |
| Inconsistent naming | -2 |
| Prohibited patterns (LOW severity) | -1 per |

### Severity calibration (classification examples)

Which severity an issue takes when it is not already a row above. Moved here from
`.claude/skills/review/SKILL.md`, where it loaded on every `/review` invocation although only
the coder-critic ever used it.

| Example | Severity |
|---------|----------|
| Missing `set.seed()` in stochastic script | **Major** |
| Hardcoded absolute path (`/Users/name/...`) | **Major** |
| No error handling on data load | **Major** |
| Missing figure axis labels | **Major** |
| No package loading section at top of script | **Major** |
| Missing comment on complex transformation | **Minor** |
| Inconsistent naming convention | **Minor** |
| Dead code left in script | **Minor** |
| Using `print()` for debugging left in production | **Minor** |

---

## Strategist-Critic (Causal Audit)

Each issue is classified by severity, and each severity carries a fixed deduction. Use these
values and no others: before they existed, two critics invented different weightings for the
same scale and scored two papers 41 and 48 on numbers that were not comparable.

| Severity | Definition | Deduction |
|----------|-----------|-----------|
| **CRITICAL** | Identification is wrong or unsupported. Fatal design flaw. | -25 per |
| **MAJOR** | Missing important check or wrong inference. Should fix before publication. | -5 per |
| **MINOR** | Could strengthen but paper works without it. Nice to have. | -1 per |

**Why these values.** One CRITICAL alone leaves 75 — below the commit gate by itself, because a
wrong identifying argument is not offset by everything else being sound. Four MAJORs reach 80; a
fifth fails. No severity is capped: the total is recorded with `--deductions`, so a paper floored
at 0 still ranks.

The overall assessment label below is reported beside the score, never instead of it.

**Overall assessment scale:**
- **SOUND** -- Design is valid, implementation is correct
- **MINOR ISSUES** -- Fixable concerns, none threatening core results
- **MAJOR ISSUES** -- Significant concerns that could change conclusions
- **CRITICAL ERRORS** -- Fundamental design flaw or incorrect implementation

**Proportional criticism principle:** A working paper missing Oster bounds is MINOR. A paper with violated parallel trends is CRITICAL.

---

## Theorist-Critic (Theory Review)

| Category | Issue | Deduction |
|----------|-------|-----------|
| **Proof validity** | Step does not follow / gap in logic | -20 per gap |
| | Circular argument | -25 |
| | Unjustified limit/expectation interchange | -10 per instance |
| | Uniform convergence claim without Donsker / VC / bracketing argument | -10 |
| | Taylor remainder not shown to be $o_p/O_p$ at claimed rate | -10 per instance |
| | Rate arithmetic wrong | -15 |
| **Identification** | Substitution from counterfactual to observable is unjustified | -20 |
| | Design invariant invoked without being stated (parallel trends / exclusion / monotonicity / continuity) | -15 |
| **Statements** | Over-claim (conclusion exceeds what proof supports) | -15 |
| | Under-claim (proof supports strictly more) | -3 |
| | Pointwise vs. uniform conflation | -10 |
| **Assumptions** | Assumption never used in the proof | -5 per assumption |
| | Assumption not interpreted (no plain-language gloss) | -3 per assumption |
| | High-level condition with no primitive counterpart and no justification | -5 |
| | Non-minimal (strictly stronger than needed, with no rationale) | -5 |
| **Notation (INV-7)** | Symbol used with two meanings | -5 per symbol |
| | Symbol used before definition | -3 per instance |
| | Inconsistency with paper's empirical sections or domain-profile notation | -5 |
| **Citations** | Cited result doesn't apply (wrong version, wrong assumptions) | -10 per instance |
| | Wrong journal/year for a named result | -3 per instance |
| | Missing citation for a named result that was invoked | -5 per instance |
| **Linkage** | Orphan theorem (not used elsewhere) | -3 |
| | Orphan claim (stated in paper, not supported by any theorem) | -10 |
| **Exposition** | Proof strategy missing | -3 |
| | Appendix reference broken | -2 |
| | Theorem environment is not a Quarto `::: {#thm-…}` block | -2 |

---

## Editor (Peer Review Synthesis)

The `referees` component (weight 25) is recorded from the editor's `editorial_decision.md`,
which must carry an explicit **Overall score** line. Its source is fixed so that two editors
reading the same referee reports produce the same number:

1. **Start from the mean** of Referee A's and Referee B's scores (each referee's report ends
   in a score out of 100).
2. **Clamp to the decision's band.** The verdict is the editor's judgment; the band is what
   keeps the number honest to it.

| Decision | Band |
|---|---|
| Accept | 90–100 |
| Minor revision | 80–89 |
| Major revision | 60–79 |
| Reject | 0–59 |

If the mean falls outside the band, record the nearest band edge and write "clamped" beside
it: a Major-revision verdict with two 85s records 79 and says so, because the editor found a
concern the referees under-weighted (or the reverse). No `--deductions` total is recorded —
this is a band, not a deduction table. A Minor revision clears the 80 commit gate; a Major
revision does not, which is the intended reading of that verdict.

`--stress` and `--variance` produce no `editorial_decision.md` and record nothing.

---

## Storyteller-Critic (Talk Review)

**Advisory -- non-blocking.** Talk scores do not gate commits or PRs.

| Issue | Deduction |
|-------|-----------|
| Slides don't compile | -20 |
| Numbers don't match paper | -20 |
| Wrong narrative arc for paper type | -15 |
| No hook in first 2 slides | -15 |
| Talk wrong length for format | -15 |
| Structural talk missing counterfactual slide | -10 |
| Theory talk missing distinguishing prediction | -10 |
| Text overflow | -10 per slide (max -30) |
| Missing backup slides | -5 |
| Inconsistent notation with paper | -5 |
| Font too small for projection | -3 per slide |
| Slide tries to do two things | -2 per slide |

---

## Explorer-Critic (Data Assessment Review)

| Issue | Deduction |
|-------|-----------|
| Proposed variable doesn't measure the concept | -25 |
| Major sample selection issue unaddressed | -20 |
| Better dataset exists and was missed | -15 |
| No discussion of measurement error | -10 |
| Access timeline unrealistic | -10 |
| Missing identification compatibility check | -10 |
| No discussion of external validity | -5 |

---

## Lit-Critic (Literature Positioning)

| Issue | Deduction |
|---|---|
| Seminal paper in the field missing | -20 |
| Methods literature the strategy depends on not covered | -15 |
| A paper in the local Zotero index on the same question is missing | -10 per, max -30 |
| Over-reliance on working papers (>50%) | -10 |
| Missing papers from the last 2 years / scooping risk unnamed | -10 |
| Scope too narrow or too broad to position | -10 |
| Frontier map lists rather than locates a gap | -10 |
| Positioning does not survive the closest paper's redundancy sentence | -15 |
| Proximity scores inconsistent | -5 |

---

## Quality Gates

| Gate | Overall Score | Per-Component Minimum |
|------|--------------|----------------------|
| Commit | >= 80 | None enforced |
| PR | >= 90 | None enforced |
| Submission | >= 95 | >= 80 per component |
| Below 80 | < 80 | Blocked |

Talk scores are advisory and do not block pipeline progression.
