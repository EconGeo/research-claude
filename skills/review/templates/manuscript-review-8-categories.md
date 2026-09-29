# Manuscript Review: 8 Check Categories

Extracted from `writer-critic.md`. Used by the writer-critic agent for manuscript review.

---

## Prerequisite Checks

**Before running categories:**

- Read `.claude/rules/content-invariants.md` -- enforce INV-1 through INV-13. Cite invariant numbers (e.g., "violates INV-3") in report alongside deductions.
- Read `.claude/rules/quarto-pdf.md` and `.claude/rules/quarto-word.md` -- enforce the blocking deductions listed there for the manuscript's output format.
- Identify the paper type (reduced-form, structural, theory+empirics, descriptive) from the strategy memo or the manuscript itself. This determines which checks apply.

---

## 1. Structure and Flow

- Does the paper follow the standard section order for its paper type?
- Does each paragraph have a single identifiable argument move (motivation, result statement, mechanism, qualification, etc.)?
- Are transitions between sections coherent?
- Does the introduction contribution statement appear in the first 2 pages?
- Is there a roadmap? (Optional but if present, is it one sentence?)
- Does the conclusion restate the main finding with effect size?

**Paper-type-specific:**

**Reduced-form:** Introduction follows: motivation -> question -> stakes -> identification preview -> result -> literature positioning?

**Structural:** Introduction includes model preview -> estimation/counterfactual preview -> key counterfactual result -> literature?

**Theory + empirics:** Introduction includes theory preview -> empirical preview -> literature positioning?

**Descriptive:** Introduction includes data/measurement innovation -> key fact -> why it matters -> literature?

---

## 2. Claims and Evidence

- Every empirical claim is supported by a table, figure, or citation
- No orphan claims (assertions without evidence)
- Numbers in text match the tables and figures exactly (INV-11)
- Effect sizes stated with units ("4.2 percentage points", not "the coefficient is significant")
- Comparisons to prior literature include specific magnitudes from cited papers
- No stale numbers (values that don't match current output files)
- **Claim–Evidence Table (mandatory):** build it per `.claude/skills/review/templates/claim-evidence-table.md`; deductions per verdict. Save it; cite its path in the report.

---

## 3. Identification Fidelity

- Does the empirical strategy section accurately describe the strategy memo's design?
- No overclaiming: causal language only in papers with causal designs (INV-8)
- Assumptions named and stated formally (parallel trends, exclusion restriction, continuity, etc.)
- Threats acknowledged -- no "our results are robust to all concerns"
- Estimand clearly stated (ATT, ATE, LATE, or equivalent)

**Paper-type-specific:**

**Reduced-form:** Design-specific elements present (pre-trends for DiD, first stage for IV, bandwidth for RDD, event definition for ES)?

**Structural:** Identification argument maps data moments to parameters? Estimation method justified?

**Theory + empirics:** Testable predictions numbered and linked to evidence?

**Descriptive:** No causal language. Patterns described as correlations or associations.

---

## 4. Writing Quality

Run the 24-pattern AI detection check from the Writer's cleanup pass:

**Content patterns:**
- Significance inflation ("pivotal moment", "transformative impact", "groundbreaking") -- -3 per, max -9
- Promotional language -- -3 per, max -9
- Superficial -ing analyses ("highlighting...", "underscoring...") -- -2 per, max -6
- Vague attributions ("experts argue", "scholars have noted") -- -3 per, max -9

**Language patterns:**
- AI vocabulary (additionally, delve, foster, garner, interplay, tapestry, underscore, landscape) -- -2 per, max -10
- Copula avoidance ("serves as" instead of "is") -- -1 per, max -5
- Negative parallelisms ("not X but Y" overuse) -- -2 per, max -6
- Excessive hedging beyond field norms -- -3

**Style patterns:**
- Em dash overuse (>2 per page) -- -3
- Rule of three everywhere -- -3
- Uniform sentence length (no variation) -- -5

**Communication patterns:**
- Filler phrases ("It's important to note that...", "It is worth mentioning...") -- -2 per, max -6
- Announcements ("In the next section, we will discuss...") -- -2 per, max -6

---

## 5. Format

Format deductions are owned by the format rules — do not restate them here.
Enforce the blocking lists in `.claude/rules/quarto-pdf.md` (PDF output) and
`.claude/rules/quarto-word.md` (Word output), plus the shared items below.

**Shared (both output formats):**

| Issue | Deduction |
|-------|-----------|
| Missing `bibliography:` in YAML | -5 |
| Top-level `csl:` present on the PDF path (must be inside `docx:` only) | -3 |
| Section heading without a `{#sec-...}` anchor | -2 per, max -10 |
| Displayed equation without a `{#eq-...}` label | -2 per, max -10 |
| Hardcoded figure/table number instead of `@fig-` / `@tbl-` | -3 per, max -10 |
| Legacy R Markdown cross-reference syntax instead of Quarto `@` syntax | -3 per, max -10 |
| Missing JEL codes or keywords after the abstract (INV-6) | -5 |
| Abstract exceeds 150 words (INV-5) | -3 |
| Missing table notes (INV-1) | -5 per table, max -15 |
| Missing figure notes (INV-2) | -5 per figure, max -15 |
| Title inside a figure rather than in `#\| fig-cap:` (INV-12) | -3 per, max -9 |
| Chunk label missing the `fig-` / `tbl-` prefix (INV-13) | -3 per, max -9 |

**Architecture deductions** (caching, `source()`, hardcoded prose numbers,
manifest coverage) belong to the **coder-critic** via
`.claude/rules/quarto-empirical.md`. Do not double-count them here.

---

## 6. Render

**You run nothing.** You have no Bash (`.claude/rules/agents.md` §2). The dispatching skill runs
`python3 .claude/scripts/pipeline.py critic-inputs` immediately before dispatching you and names
the log it wrote — `quality_reports/critic_inputs/writer-critic_<stamp>.log` — in your prompt.
Read that log in full. It has three sections: `quarto render`, `prose_number_check.py` and
`check_render.py` (the page check on the rendered PDF; skipped for a non-PDF or failed render).

- Render section exit ≠ 0: -20
- Each `WARNING` line in the render section that is not a cross-reference warning: -3
- Each unresolved cross-reference: -3. Count from check_render's `UNRESOLVED:` lines when that
  section ran, otherwise from the render section's "Unable to resolve crossref" warnings — never
  both for the same reference.
- Each `@key` cited in the manuscript but absent from `references.bib` (Grep the source): -3
- Each hardcoded value `prose_number_check.py` lists: -10 (INV-11). A clean render proves the
  inline expressions *evaluated*, never that a typed literal is right.

**No log named in your prompt, or the named file does not exist:** report
`## Render: NOT SCORED — no critic-inputs log in the dispatch`, deduct nothing in this category,
and make that the first line under Score Breakdown so the dispatching session sees it. Never infer
a render result from the source, and never ask for Bash.

## 7. Voice Fidelity

**Only scored when `.claude/references/personal-style-guide.md` contains real content (not the template).**

Compare the draft against the style guide:

| Issue | Deduction |
|-------|-----------|
| Uses 3+ words from "author avoids" list | -5 per word, max -15 |
| Sentence length median off by >5 words from guide | -5 |
| Paragraph openings don't match documented patterns | -3 per, max -9 |
| Tone mismatch (e.g., bombastic when author is dry) | -10 |
| Hedging frequency doesn't match documented pattern | -3 |
| Em dash rate deviates significantly from guide | -2 |

If the style guide is still a template, report: "Voice fidelity not scored -- style guide not yet extracted. Run `/write style-guide [paper-dir]` to enable."

---

## 8. Notation Consistency

- Same symbol means the same thing everywhere (INV-7)
- Every symbol defined at first use
- Notation matches the strategy memo
- Subscript conventions consistent ($i$ for individual, $t$ for time, $g$ for group -- or whatever the paper uses, but consistent)
- Notation in tables matches notation in text

---

## Standalone Mode

When invoked via `/review --proofread`, run categories **4, 5, 6, 8 only** (writing quality + format + render + notation). No strategy alignment -- just prose and format quality.

When invoked via `/review --all` or `/review --peer`, run all 8 categories.

---

## Report Format

```markdown
# Manuscript Review -- [Project Name]
**Date:** [YYYY-MM-DD]
**Reviewer:** writer-critic
**Paper type:** [Reduced-form / Structural / Theory+Empirics / Descriptive]
**Score:** [XX/100]
**Mode:** [Full / Standalone (prose quality only)]

## Structure and Flow: [COHERENT/ISSUES/MAJOR ISSUES]
## Claims and Evidence: [SUPPORTED/GAPS/UNSUPPORTED]
## Identification Fidelity: [FAITHFUL/OVERCLAIMED/MISREPRESENTED]
## Writing Quality: [CLEAN/AI PATTERNS FOUND/NEEDS REWRITE]
## Format: [COMPLIANT/ISSUES/NON-COMPLIANT]
## Render: [PASS/WARNINGS/FAIL/NOT SCORED]
## Voice Fidelity: [MATCH/DRIFT/NOT SCORED]
## Notation Consistency: [CONSISTENT/INCONSISTENCIES]

## Claim–Evidence Table
- Path:
- Rows: N (SUPPORTED a / OVERSTATED b / UNSUPPORTED c / CONTRADICTED d / UNVERIFIABLE e)

## Score Breakdown
- Starting: 100
- [Deductions with invariant citations]
- **Final: XX/100**

## Escalation Status: [None / Strike N of 3]
```
