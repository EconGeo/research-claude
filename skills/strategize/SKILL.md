---
name: strategize
description: Design identification strategy, pre-analysis plan, or formal theory section. Dispatches Strategist / Theorist (proposer) and the paired critic (validator). Replaces the old identify and pre-analysis-plan commands.
argument-hint: "[mode: strategy | pap | pap interactive | theory] [research question or spec path] [--yes]"
allowed-tools: Read,Grep,Glob,Write,Bash,Agent
---

# Strategize

Design an identification strategy, pre-analysis plan, or formal theory section by dispatching the appropriate creator (**Strategist** or **Theorist**) and its paired critic.

**Input:** `$ARGUMENTS` — mode keyword followed by research question or path to research spec.

---

## Modes

### `/strategize [question]` or `/strategize strategy [question]` — Identification Strategy
Design the causal identification strategy.

**Agents:** Strategist, then strategist-critic
**Output:** Strategy memo + robustness plan + falsification tests

Workflow:
1. **Pre-Strategy Report (mandatory).** Before proposing any strategy, the Strategist outputs the
   report in `.claude/skills/strategize/templates/pre-strategy-report.md`, proving it read the
   discovery inputs. Missing spec, literature review or data assessment → proceed with ASSUMED
   placeholders, each flagged.
2. Read `.claude/references/domain-profile.md` for the field's common designs, then
   **Option gate** (`.claude/rules/option-gates.md`): show 5–8 candidate designs — columns
   *variation exploited*, *estimand*, *key assumption*, *main threat*, *data fit* — ranked,
   rank 1 marked, and wait (rank / `edit` / `none`; `--yes` takes rank 1). The pick and the
   losing designs land in Step 7's decision record under *Alternatives considered*.
3. Dispatch Strategist to produce:
   - Strategy memo: design choice, estimand, assumptions, comparison group
   - Pseudo-code: implementation sketch
   - Robustness plan: ordered list of checks with rationale
   - Falsification tests: what SHOULD NOT show effects
   - Referee objection anticipation: top 5 objections with responses

   Pass the strategist **only the chosen design's** checklist —
   `.claude/skills/strategize/templates/design-checklists/<design>.md`, one of `did`,
   `event-study`, `iv`, `rdd`, `structural`, `descriptive`.
4. Dispatch strategist-critic (4-phase audit,
   `.claude/skills/review/templates/causal-audit-4-phases.md`) on the new memo, by filename.
   Returns text; **session saves** to `quality_reports/reviews/strategist-critic_<date>.md`,
   memo filename in its header, then records:
   `python3 .claude/scripts/pipeline.py state record-score strategy <score> --critic strategist-critic --deductions <total> --report <path>`.
5. **Below 80 → revise before Step 6** (`--yes` does not waive it): `pipeline.py state strike
   strategist`, a **new foreground `Agent`** strategist call with the deductions (never
   `SendMessage`) writing a **new** memo, re-dispatch strategist-critic,
   save, `record-score strategy` again. Repeat to ≥ 80 or strike three → escalate to the
   registry's escalation target with a specific question.
6. Save to `quality_reports/strategy/<project>/`: `strategy_memo_<YYYY-MM-DD_HHMM>.md` (local
   time; a new file each round, never overwritten, newest current; all 5 required sections —
   Estimand, Specification, Assumptions, Robustness Plan, Threats), `pseudo_code.md`,
   `robustness_plan.md`, `falsification_tests.md`
7. **Save decision record** → `quality_reports/decisions/strategy_[topic].md`, using
   `.claude/skills/strategize/templates/decision-record.md`. It owns the field list: decision,
   alternatives considered with why each was rejected, rationale, key assumptions with
   credibility, what would invalidate the strategy, and risks. **Unconditional** — every run,
   an escalated one included (open question under risks).

### `/strategize pap [spec]` — Pre-Analysis Plan
Draft a pre-analysis plan following AEA/OSF/EGAP standards.

**Input:** `$ARGUMENTS` — path to research spec file, a topic, or `interactive` for guided interview.

- If `$ARGUMENTS` includes a file path: read it (research spec from `/discover interview`)
- If `$ARGUMENTS` includes `interactive`: conduct the guided PAP interview (see below)
- Otherwise: treat as topic and draft with ASSUMED placeholders marked clearly

**Agents:** Strategist (in PAP mode), strategist-critic
**Output:** Pre-analysis plan document

#### Interactive PAP Interview

`/strategize pap interactive` runs the 6-question guided flow in
`.claude/skills/strategize/references/pap-interview-flow.md` — one question at a time, with its
probes, red flags and observational adaptations — then proceeds to drafting.

#### Drafting

Ask which registry the user is targeting, then dispatch the Strategist in PAP mode with **only
that registry's template**:

| Registry | `.claude/skills/strategize/templates/pap-templates/…` | Pick it when |
|---|---|---|
| AEA RCT | `aea-rct.md` | An RCT registered before the intervention begins; every field required |
| OSF | `osf.md` | Observational, quasi-experimental or archival work; flexible, versioned |
| EGAP | `egap.md` | Development economics / political science, with governance and ethics questions |

The template owns the section list, the ordering and — for `osf.md` §6 — the observational
adaptation. Do not restate any of it here.

#### Safety and review

Drafting and review both follow `.claude/skills/strategize/templates/pap-safety.md`: how to mark
and list every `[ASSUMED]` item, the mandatory Pre-Registration Checklist that closes every PAP,
and the PAP-specific criteria the strategist-critic applies on top of its own rubric.

Dispatch the strategist-critic after the PAP is drafted — mandatory, not conditional. It returns
text; **session saves** to `quality_reports/reviews/strategist-critic_<date>.md`, records: `python3 .claude/scripts/pipeline.py state record-score strategy <score> --critic strategist-critic --deductions <total> --scope section:pre-analysis-plan --report <path>`.

The `--scope section:` prefix is load-bearing and must not be dropped or reworded — see
`.claude/skills/strategize/gotchas.md` ("Why the PAP score is section-scoped") for what breaks
without it.

Below 80 → Strategist revises → critic re-scores; `pipeline.py state strike strategist` per failing
round; strike three → escalate to the registry's escalation target with a specific question.

Save PAP to `quality_reports/pre_analysis_plan_[topic].md`

---

### `/strategize theory [target]` — Formal Theory Section

Produce a formal theory section: assumptions, definitions, lemmas, theorems, and proofs.

**When to use:**
- Paper type is **econometric methods** (the method is the contribution)
- Paper type is **theory + empirics** (theoretical predictions are tested)
- Paper type is **structural** (identification of structural parameters needs formal argument)
- Paper type is **methodological reduced-form** (the design contributes a new estimator)

**Skip** for applied papers using off-the-shelf estimators — the strategy memo is enough.

**Input:** `$ARGUMENTS` — research question, path to strategy memo, or path to existing paper/draft.

**Agents:** Theorist, then theorist-critic
**Output:** Theory memo + a `# Theory` section and proofs appendix in the manuscript + notation glossary

Workflow:
1. **Pre-Theory Report (mandatory).** Before writing any math, the Theorist outputs the report in
   `.claude/skills/strategize/templates/pre-theory-report.md`, showing what it read. If the
   strategy memo or the paper type is missing, the Theorist flags it and asks before proceeding.
   Any question the Theorist would ask is asked here, in the main session, before dispatch —
   the theorist has no user-facing tool.
2. Read `.claude/references/domain-profile.md` for the Theoretical Foundational References table and Author Team table.
3. Dispatch **Theorist** to produce:
   - `quality_reports/theory/[topic]/theory_memo.md`
   - a `# Theory` section and proofs appendix written directly into the manuscript
   - `quality_reports/theory/[topic]/notation_glossary.md`
4. Dispatch **theorist-critic** (4-phase review,
   `.claude/skills/review/templates/theory-review-4-phases.md`, early-stopping on critical proof
   gaps). Returns text; **session saves** to `quality_reports/reviews/theorist-critic_<date>.md`,
   then records:
   `python3 .claude/scripts/pipeline.py state record-score theory <score> --critic theorist-critic --deductions <total> --report <path>`.
5. Below 80 → Theorist revises → critic re-scores; `pipeline.py state strike theorist` per
   failing round; strike three → escalate to the registry's escalation target with a specific
   question.
6. **Save decision record** → `quality_reports/decisions/theory_[topic].md`
   Record:
   - **Decision:** The theoretical objects proved (identification, asymptotic distribution, etc.)
   - **Assumptions:** Full list with interpretation
   - **What's open:** What the theory does NOT cover (caveats for the writer)
   - **Linkage:** Which empirical claims each theorem supports

