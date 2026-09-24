---
name: discover
description: Discovery phase combining research interviews, a pointer to /lit-position for literature, data discovery, and ideation. Routes to appropriate agents based on arguments. Replaces the old interview-me, lit-review, find-data and research-ideation commands.
argument-hint: "[mode: interview | lit | data | ideate] [topic or query] [--yes]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent
---

# Discover

Launch the Discovery phase of research. Routes to the appropriate agents based on the mode specified.

**Input:** `$ARGUMENTS` — a mode keyword followed by a topic or query.

---

## Modes

### Default (no mode specified)
If no mode keyword is given, start with an interactive interview to build the research specification.

### `/discover interview [topic]` — Research Interview
Conduct a structured conversational interview to formalize a research idea.

**This is conversational.** Ask in your text responses, one or two questions at a time, and wait
for the answer. Do NOT use AskUserQuestion. No agent is dispatched.

Run the six-category flow in `.claude/skills/discover/templates/interview-flow.md` — origin,
question, significance, data, strategy, literature — with its follow-up probes and its style
rules (curious not prescriptive; probe weak spots gently; build on answers; stop when the vision
is clear).

After interview (5-8 exchanges), produce three outputs.

**Option gate** (`.claude/rules/option-gates.md`): before writing the spec, show 5–8
framings of the research question — columns *question*, *contribution*, *closest paper*,
*data needed*, *feasibility* — ranked, and wait (`--yes` takes rank 1). The pick becomes the
spec's research question; the rest are Output 3's alternatives.

**Output 1: Research Specification** → `quality_reports/research_spec_[topic].md`, written with
`.claude/skills/discover/templates/research-spec.md`. That template owns the eight sections:
research question, contribution, literature position, data requirements, preliminary
identification strategy, expected results, feasibility assessment, risk factors.

**Output 2: Domain Profile** → `.claude/references/domain-profile.md` (if still template)
Fill in field, target journals, common data sources, identification strategies, field conventions, seminal references, and referee concerns based on the interview. Target journals are
offered as an **Option gate** (`.claude/rules/option-gates.md`) of 5–8 journals in tiers from
`.claude/references/discipline-cards.md`; `--yes` takes rank 1; the pick fills the field.

**Output 3: Decision Record** → `quality_reports/decisions/discovery_[topic].md`, written with
`.claude/skills/strategize/templates/decision-record.md`. The decision is the research question
chosen; the alternatives are the other framings the interview raised, each with why it was not
preferred.

### `/discover lit` — superseded

Literature search and positioning are `/lit-position` (optionally after `/seed-papers`). Run that
instead; this skill no longer has a `lit` mode.

### `/discover data [requirements]` — Data Discovery
Find and assess datasets for the research question.

**Agents:** Explorer (finder), then explorer-critic (assessor)
**Output:** Ranked data sources with feasibility grades

Workflow:
1. Read research spec and strategy memo if they exist
2. Read `.claude/references/domain-profile.md` for common data sources in the field
3. Understand what variables are needed: treatment, outcome, controls, time period, geography
4. Dispatch Explorer to search across source categories:
   - Public microdata (CPS, ACS, NHIS, MEPS, etc.)
   - Administrative data (Medicare claims, tax records, court records)
   - Survey data (RAND HRS, PSID, Add Health, NLSY)
   - International (World Bank, OECD, Eurostat)
   - Novel/alternative (satellite imagery, web scraping, proprietary)
5. For each dataset found, report — then, before Step 6, **Option gate**
   (`.claude/rules/option-gates.md`): the ranked shortlist (5–8 datasets, or every feasible one
   if fewer; columns *name*, *access*, *coverage*, *grade*), wait, `--yes` takes rank 1; the
   pick heads `data_sources.md`, the rest stay in it as alternatives:
   - Name, provider, access level (public/restricted)
   - Key variables available
   - Coverage (time period, geography, sample size)
   - **Feasibility grade**, on access effort — A ready to use (public, documented, standard
     format); B accessible with effort (application, moderate cost, needs cleaning); C restricted
     but obtainable (FSRDC, data use agreement, IRB); D very difficult (proprietary, partnership,
     rare access); F not obtainable for this project, which sends it to the rejection table.
   - Strengths and limitations

   Write each source up with `.claude/skills/discover/templates/data-assessment.md`, which uses
   the same A–F scale and the same critique categories.
6. Dispatch explorer-critic. It runs its own six check categories
   (`.claude/skills/review/templates/data-review-6-categories.md`): measurement validity, sample
   selection, external validity, alternative data sources, practical feasibility, identification
   compatibility. The local-first search order in `.claude/rules/literature-search-order.md`
   applies to any literature it cites about a dataset's known issues.

   Returns text; session saves it to
   `quality_reports/reviews/explorer-critic_<date>.md`. Record: `python3 .claude/scripts/pipeline.py state record-score data <score> --critic explorer-critic --deductions <total> --report quality_reports/reviews/explorer-critic_<date>.md`.
   Below 80 → Explorer revises → critic re-scores; `pipeline.py state strike explorer` per
   failing round; strike three → escalate to the registry's escalation target with a specific
   question.
7. Save to `quality_reports/data-assessment/<project>/`:
   - `data_sources.md` — the per-dataset report from Step 5: name, provider, access level, key variables, coverage, feasibility grade (A–F), strengths and limitations, plus the rejection table below. This is the file the downstream gate (`strategist.requires` in `.claude/rules/registry.yaml`) keys on, so it must be the one that always exists.
   - `data_dictionary.md` — the variables needed (Step 3: treatment, outcome, controls, time period, geography) crossed with what each dataset in Step 5 actually supplies for them
   - `access_instructions.md` — how to obtain each viable dataset: application route, cost, timeline, IRB/DUA/FSRDC requirements, drawn from Step 5's access level and feasibility grade

**Rejected datasets:** Include a rejection table in `data_sources.md`:

| Dataset | Reason for Rejection | Deal-breaker? |
|---------|---------------------|---------------|
| [Name]  | [explorer-critic's finding] | [Yes/No] |

### `/discover ideate [topic]` — Research Ideation
Generate structured research questions and hypotheses from a topic or dataset.

**Agents:** Direct generation (no agent dispatch)
**Output:** Research questions with empirical strategies

Generate 5–10 research questions with clear hypotheses; for each, a potential identification
strategy, data requirements and expected contribution; rank by feasibility and novelty, and offer
them as an **Option gate** (`.claude/rules/option-gates.md`; columns *question*, *hypothesis*,
*identification*, *data*, *contribution*; `--yes` takes rank 1). The pick is written first with
the rest below it. Save to
`quality_reports/research_ideas_[topic].md`, written with
`.claude/skills/discover/templates/research-ideas.md`.

Known failure points for every mode: `.claude/skills/discover/gotchas.md`.

