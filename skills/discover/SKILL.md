---
name: discover
description: Discovery phase combining research interviews, literature search, data discovery, and ideation. Routes to appropriate agents based on arguments. Replaces the old interview-me, lit-review, find-data and research-ideation commands.
argument-hint: "[mode: interview | lit | data | ideate] [topic or query]"
allowed-tools: Read,Grep,Glob,Write,Edit,WebSearch,WebFetch,Agent
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

**This is conversational.** Ask questions directly in your text responses, one or two at a time. Wait for the user to respond before continuing. Do NOT use AskUserQuestion.

**Agents:** Direct conversation (no agent dispatch)
**Output:** Research specification + domain profile

Interview structure:
1. **Big Picture** (1-2 questions): "What phenomenon are you trying to understand?" "Why does this matter?"
2. **Theoretical Motivation** (1-2 questions): "What's your intuition for why X happens?" "What would standard theory predict?"
3. **Data and Setting** (1-2 questions): "What data do you have access to?" "Is there a specific institutional setting?"
4. **Identification** (1-2 questions): "Is there a natural experiment or policy change you can exploit?" "What's the biggest threat to causal interpretation?"
5. **Expected Results** (1-2 questions): "What would you expect to find?" "What would surprise you?"
6. **Contribution** (1 question): "How does this differ from what's been done? What gap are you filling?"

Interview style:
- **Be curious, not prescriptive.** Draw out the researcher's thinking, don't impose your own ideas.
- **Probe weak spots gently.** "What would a skeptic say about...?" not "This won't work because..."
- **Build on answers.** Each question should follow from the previous response.
- **Know when to stop.** If the researcher has a clear vision after 4-5 exchanges, move to the specification.

After interview (5-8 exchanges), produce three outputs:

**Output 1: Research Specification** → `quality_reports/research_spec_[topic].md`
```markdown
# Research Specification: [Title]
## Research Question — [one sentence]
## Motivation — [why this matters, theoretical context, policy relevance]
## Hypothesis — [testable prediction with expected direction]
## Empirical Strategy — [method, treatment, control, identifying assumption, robustness]
## Data — [primary dataset, key variables, sample, unit of observation]
## Expected Results — [what the researcher expects and why]
## Contribution — [how this advances the literature]
## Open Questions — [issues needing further thought]
```

**Output 2: Domain Profile** → `.claude/references/domain-profile.md` (if still template)
Fill in field, target journals, common data sources, identification strategies, field conventions, seminal references, and referee concerns based on the interview.

**Output 3: Decision Record** → `quality_reports/decisions/discovery_[topic].md`
Using `.claude/skills/strategize/templates/decision-record.md`, record:
- **Decision:** The research question chosen
- **Alternatives:** Other angles, framings, or questions that came up during the interview
- **Why rejected:** For each alternative, why this framing was preferred (scope, data availability, novelty, feasibility)
- **Key assumptions:** What must hold for this question to be answerable
- **What would invalidate:** What would force a pivot (e.g., "if the policy change turns out to have been anticipated")

### `/discover lit [topic]` — Literature Review
**Superseded by `/lit-position`.** Search, proximity scoring, coverage self-check,
frontier mapping and positioning all live in `.claude/skills/lit-position/SKILL.md`
now — invoke it directly instead of this mode. It is local-Zotero-first per
`.claude/rules/literature-search-order.md`.

### `/discover data [requirements]` — Data Discovery
Find and assess datasets for the research question.

**Agents:** Explorer (finder) → explorer-critic (assessor)
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
5. For each dataset found, report:
   - Name, provider, access level (public/restricted)
   - Key variables available
   - Coverage (time period, geography, sample size)
   - **Feasibility grade:**
     - **A** — Ready to use (public download, documented, standard format)
     - **B** — Accessible with effort (application required, moderate cost, needs cleaning)
     - **C** — Restricted but obtainable (FSRDC, data use agreement, IRB approval)
     - **D** — Very difficult (proprietary, requires partnership, rare access)
   - Strengths and limitations
6. Dispatch explorer-critic to critique each proposed dataset using the **5-point assessment:**
   1. **Measurement validity** — Does the variable actually measure what we need?
   2. **Sample selection** — Who is in the data? Who is missing?
   3. **External validity** — Can we generalize from this sample?
   4. **Identification compatibility** — Does this data support the proposed design?
   5. **Known issues** — Documented problems with this dataset in the literature

   Save the critic's report to `quality_reports/reviews/explorer-critic_<date>.md`. Record: `python3 .claude/scripts/pipeline.py state record-score data <score> --critic explorer-critic --report quality_reports/reviews/explorer-critic_<date>.md`.
7. Save to `quality_reports/data-assessment/<project>/`:
   - `data_sources.md` — the per-dataset report from Step 5: name, provider, access level, key variables, coverage, feasibility grade (A-D), strengths and limitations, plus the rejection table below. This is the file the downstream gate (`strategist.requires` in `.claude/rules/registry.yaml`) keys on, so it must be the one that always exists.
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

Generate:
1. 3-5 research questions with clear hypotheses
2. For each: potential identification strategy, data requirements, expected contribution
3. Rank by feasibility and novelty
4. Save to `quality_reports/research_ideas_[topic].md`

---

## Bundled Resources

| Resource | Path | What It Contains |
|----------|------|-----------------|
| Research spec | `.claude/skills/discover/templates/research-spec.md` | 8-section research specification output format |
| Interview flow | `.claude/skills/discover/templates/interview-flow.md` | 6-category conversational structure for interview mode |
| Lit review entry | `.claude/skills/discover/templates/lit-review-entry.md` | Per-paper annotation format with proximity scoring |
| Data assessment | `.claude/skills/discover/templates/data-assessment.md` | Data source evaluation with 5-point critique and feasibility grades |
| Research ideas | `.claude/skills/discover/templates/research-ideas.md` | Ideation output format with feasibility/novelty ranking |
| PDF processing | `.claude/skills/discover/references/pdf-processing.md` | Safe workflow for reading reference papers |
| Gotchas | `.claude/skills/discover/gotchas.md` | Known failure points and edge cases |

---

## Principles

- **Interview style:** Be curious, not prescriptive. Draw out the researcher's thinking.
- **Literature honesty:** Never fabricate citations. Mark unverified as `% UNVERIFIED`.
- **Proximity scoring:** Always assign 1-5 proximity scores to papers found.
- **Citation chains:** Forward and backward citation tracking is an explicit search vector — do not skip it.
- **Effect sizes matter:** Report magnitudes, not just signs. Note identification strategy for every paper.
- **Data feasibility matters:** A perfect dataset you can't access is useless. Always assign A/B/C/D grades.
- **5-point data critique:** Measurement validity, sample selection, external validity, identification compatibility, known issues. Never skip this.
- **Domain-profile aware:** Always read `.claude/references/domain-profile.md` first for field calibration.
- **Worker-critic pairing:** Explorer + explorer-critic for data discovery; never skip the critic. Literature discovery is `/lit-position`, not this skill.
