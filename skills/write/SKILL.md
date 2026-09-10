---
name: write
description: Draft academic paper sections using paragraph-level argument moves. Cleanup pass strips AI patterns after drafting. Replaces the old draft-paper and humanizer commands.
argument-hint: "[section or mode: intro | strategy | results | conclusion | abstract | full | humanize | style-guide] [file path (optional)]"
allowed-tools: Read,Grep,Glob,Write,Edit,Agent
---

# Write

Draft paper sections, apply a cleanup pass, or extract a personal style guide from prior papers by dispatching the **Writer** agent.

**Input:** `$ARGUMENTS` — section name or mode, optionally followed by file path.

---

## Modes

### `/write [section]` — Draft Paper Section
Draft a specific section: `intro`, `strategy`, `results`, `conclusion`, `abstract`, or `full`.

**Agent:** Writer
**Output:** prose written directly into `manuscript_<project>.qmd`

Workflow:

#### 1. Context Gathering

Before drafting, read all available context:
1. `python3 .claude/scripts/pipeline.py manuscript` — read the declared manuscript in full: YAML, the `setup` chunk's naming map, every chunk label, every section already drafted
2. Read `master_supporting_docs/` for notes, outlines, research specs
3. Read `quality_reports/strategy/<project>/strategy_memo.md` and `quality_reports/literature/<project>/positioning.md`
4. Read `.claude/references/domain-profile.md` for field conventions
5. Read `references.bib` — every `@key` you write must exist there
6. List the `tbl-` and `fig-` chunks and the objects the estimation chunks define — those are what prose may cite

#### 2. Paper Type Detection

Before routing, identify the paper type from the strategy memo or existing draft:
- **Reduced-form** — DiD, IV, RDD, event study
- **Structural** — Model estimation, counterfactual simulations
- **Theory + empirics** — Propositions tested with data
- **Descriptive / measurement** — New data, new measure, stylized facts

This determines which section templates the Writer uses.

#### 3. Section Routing

Based on `$ARGUMENTS`:
- **`full`**: Draft all sections in sequence, pausing between major sections for user feedback
- **`intro`**: Draft introduction (most common request)
- **`strategy`**: Draft empirical strategy (reduced-form), model + estimation (structural), or model + tests (theory+empirics)
- **`results`**: Draft results — narration style depends on paper type and output type (regression tables, event study figures, counterfactual simulations, etc.)
- **`conclusion`**: Draft conclusion with type-appropriate ending (policy implications, counterfactual implications, or research agenda)
- **`abstract`**: Draft abstract (must have other sections first)
- **`data`**: Draft data section — expanded for descriptive/measurement papers
- **`model`**: Draft model section (structural or theory+empirics papers only)
- **No argument**: Ask user which section to draft

#### 4. Dispatch writer
Dispatch **writer** with the paper type, the section, and the argument-move templates. It writes the section into the declared manuscript under its `#` heading; every number is an inline expression (INV-11). Standalone: `python3 .claude/scripts/pipeline.py log writer`.

#### 5. Dispatch writer-critic (every mode that touches prose)
Dispatch **writer-critic** in section mode on the section just written. It produces a scored report at `quality_reports/reviews/writer-critic_<date>.md` and the Claim–Evidence Table at `quality_reports/reviews/claim_evidence_<project>_<date>.md`. Record: `python3 .claude/scripts/pipeline.py state record-score manuscript <score> --critic writer-critic --report <path> --scope section:<name>`. Below 80 → writer fixes → critic re-reviews; `pipeline.py state strike writer` per failing round; strike three → User with a specific question. `/write humanize` is prose and gets the critic; `/write style-guide` produces no prose and is the only exempt mode.

#### 6. Present to user
Only after the critic's score. Sections go through the drafting gates (`.claude/skills/write/templates/drafting-gates.md`), each gate closing with a score, pausing for approval at each:

**GATE 1:** Introduction + Literature positioning → present, wait for approval
**GATE 2:** Data + Empirical Strategy (or Model) → present, wait for approval
**GATE 3:** Results + Robustness + Conclusion → present, wait for approval

For single-section drafts, present the section directly. For `full`, use all three gates.

Flag items that need attention:
- **BLOCKED items:** Results/Conclusion cannot be drafted without an estimation chunk and a clean render
- **VERIFY items:** Citations that need user confirmation
- **VOICE items:** Style guide not yet extracted (drafting blocked until resolved)

### `/write style-guide [paper-dir]` — Extract Personal Voice

One-shot extraction of the user's writing voice from their published or drafted papers. Produces `.claude/references/personal-style-guide.md`, which the writer auto-loads on every subsequent invocation.

**When to run:**
- Once at the start of a project, after pointing at a directory of the user's prior papers
- After publishing a new paper that shifts voice (re-run to refresh the profile)

**Input:** `$ARGUMENTS` — path to a directory containing prior papers (`.qmd`, `.docx`, `.pdf`, `.tex`). If omitted, defaults to `master_supporting_docs/` and scans for `.qmd`/`.docx`/`.pdf`/`.tex` files.

**Agent:** Writer (style-extraction mode)
**Output:** `.claude/references/personal-style-guide.md`

Workflow:
1. **Discover corpus.** List `.qmd`, `.docx`, `.pdf`, `.tex` files in the target directory. If fewer than 2 papers found, flag and ask before proceeding (style extraction on a single paper overfits).
2. **Sample strategically.** For each paper, extract:
   - The full introduction
   - The first two paragraphs of each major section
   - The abstract and conclusion
   - A random sample of 5–10 results-section paragraphs
   This keeps context usage bounded while capturing voice variation across sections.
3. **Extract patterns.** The Writer (in style-extraction mode) produces quantitative and qualitative patterns:
   - Sentence-length distribution (median, 10th–90th pct)
   - Passive-voice frequency, first-person-plural frequency, em dash rate
   - Paragraph opening and closing moves
   - Section-architecture patterns (how introductions open, how results lead)
   - Lexicon: words used repeatedly, words demonstrably avoided
   - Hedging and comparison patterns
   - Citation conventions (textual vs. parenthetical split; papers-per-claim)
   - Tone markers and anti-patterns already stripped
4. **Write to `.claude/references/personal-style-guide.md`.** Fill every template section with quoted examples from the corpus. Never invent patterns — if a section has no evidence, write "[insufficient corpus evidence]".
5. **Present summary.** One-paragraph recap of the voice profile: sentence length, passive rate, signature lexicon, distinguishing tone markers. User confirms before the guide takes effect on subsequent `/write` calls.

Principles for the extraction:
- **Ground every claim in the corpus.** Each pattern must have at least one quoted example.
- **Extract, don't prescribe.** The guide records the author's observed behavior, not what the Writer thinks is good style.
- **Don't duplicate `domain-profile.md`.** The style guide is about voice; the domain profile is about field conventions.
- **Don't override the content invariants.** Voice doesn't trump INV-1..21 (`.claude/rules/content-invariants.md`).

### `/write humanize [file]` — Cleanup Pass Only
Strip AI writing patterns from existing text without rewriting content.

**Agent:** Writer (cleanup mode)
**Output:** Edited file with AI patterns removed

Strips 24 patterns across 4 categories:
- Structural: forced narrative arcs, artificial progression
- Lexical: "delve, leverage, nuanced, robust"
- Rhetorical: rule-of-three, negative parallelisms, em dash overuse
- Formatting: excessive bullet points, promotional language

---

## Section Standards

**All paper types share the same backbone. Moves diverge by type — see writer.md for full templates.**

| Section | Length | Reduced-Form | Structural | Theory+Empirics | Descriptive |
|---------|--------|-------------|-----------|----------------|-------------|
| Introduction | 1000-1500 | ...preview → result → contribution | ...model preview → counterfactual → contribution | ...theory preview → test result → contribution | ...data innovation → key fact → contribution |
| Data | 800-1200 | Treatment, outcome, controls | Moments that identify parameters | Standard | 1200-1800 (core contribution) |
| Strategy/Model | 800-1500 | Design-specific (DiD/IV/RDD/ES) | Environment → decisions → equilibrium → estimation | Model → propositions → tests | N/A (merged into Data) |
| Results | 800-1500 | Main spec → robustness → heterogeneity | Estimates → model fit → counterfactuals → welfare | Prediction-by-prediction evidence | Key facts → decompositions → implications |
| Conclusion | 500-700 | Policy implications | Counterfactual implications + model limitations | What model gets right/wrong | Research agenda enabled by new data |
| Abstract | 100-150 | Question, design, finding with magnitude | Question, model, counterfactual finding | Question, prediction, test result | Question, measurement, key fact |

---

## Quarto Conventions

- `@key` for textual citations ("@smith2024 shows..."), `[@key]` parenthetical (INV-9)
- `@tbl-label`, `@fig-label`, `@eq-label`, `@sec-label` — never a typed number
- Notation protocol: `.claude/skills/write/references/notation-protocol.md`

---

## Bundled Resources (Level 3)

Loaded on demand by the writer agent:

| Resource | Path | When |
|----------|------|------|
| Section templates | `.claude/skills/write/templates/section-templates.md` | Always -- defines section structure |
| Paragraph moves | `.claude/skills/write/templates/paragraph-moves.md` | Always -- defines argument types |
| Cleanup patterns | `.claude/skills/write/templates/cleanup-patterns.md` | After drafting -- cleanup pass |
| Style extraction | `.claude/skills/write/templates/style-extraction-protocol.md` | `/write style-guide` mode |
| Drafting gates | `.claude/skills/write/templates/drafting-gates.md` | Full draft mode |
| Notation protocol | `.claude/skills/write/references/notation-protocol.md` | Strategy + results sections |

See also: `gotchas.md` for known failure points and edge cases.

---

## Principles
- **Never a draft without its critic.** The score comes before the user sees the section.
- **This is the user's paper, not Claude's.** Match their voice and style.
- **Never fabricate results.** Use TBD placeholders.
- **Citations must be verifiable.** Only cite confirmed papers.
- **Argument moves first, cleanup second.** Draft with structure, then strip AI patterns.
