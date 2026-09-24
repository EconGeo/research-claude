---
name: write
description: Draft academic paper sections using paragraph-level argument moves. Cleanup pass strips AI patterns after drafting. Replaces the old draft-paper and humanizer commands.
argument-hint: "[section or mode: intro | strategy | results | conclusion | abstract | full | humanize | style-guide] [file path (optional)]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent
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

Identify the paper type from the strategy memo or the existing draft — reduced-form, structural,
theory+empirics, or descriptive/measurement. The signatures, and what each type turns the strategy
section into, are in `.claude/skills/write/templates/section-templates.md` ("Paper Types"). The
type decides which section template the Writer uses. Each type's narrative arc (the `**Arc:**`
line per type, shared with `/talk`) is in `.claude/references/narrative-arcs.md`.

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

#### 4b. Cleanup pass

After the writer returns and before dispatching writer-critic, apply
`.claude/skills/write/templates/cleanup-patterns.md` to the drafted section. This is the pass
the skill's description promises; without it the description is a claim no step delivers.

#### 5. Dispatch writer-critic (every mode that touches prose)
Dispatch **writer-critic** in section mode. Returns report + Claim–Evidence Table as text;
session saves to `quality_reports/reviews/writer-critic_<date>.md` and
`quality_reports/reviews/claim_evidence_<project>_<date>.md`, records: `python3 .claude/scripts/pipeline.py state record-score manuscript <score> --critic writer-critic --deductions <total> --report <path> --scope section:<name>`. Below 80 → writer fixes → critic re-reviews; `pipeline.py state strike writer` per failing round; strike three → User with a specific question. `/write humanize` gets the critic too, in proofread mode (below); `/write style-guide` is the only exempt mode (no prose).

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

**When to run:** once at the start of a project, and again after publishing a paper that shifts
the voice.

**Input:** `$ARGUMENTS` — a directory of prior papers (`.qmd`, `.docx`, `.pdf`, `.tex`); defaults
to `master_supporting_docs/`.

**Agent:** Writer (style-extraction mode)
**Output:** `.claude/references/personal-style-guide.md`

Dispatch the Writer in style-extraction mode against
`.claude/skills/write/templates/style-extraction-protocol.md`. It owns all six steps — corpus
discovery, strategic sampling, pattern extraction, writing the guide, the **self-citation check**
(which this skill used to omit, so missing self-citation bib keys went unreported), and the
summary the user confirms before the guide takes effect — plus the rules that keep extraction
descriptive rather than prescriptive.

### `/write humanize [file]` — Cleanup Pass Only
Strip AI writing patterns from existing text without rewriting content.

**Agent:** Writer (cleanup mode)
**Output:** Edited file with AI patterns removed

Strips the 24 AI patterns in `.claude/skills/write/templates/cleanup-patterns.md` (content,
language, style and communication categories) under its academic adaptation rules.

After the cleanup pass, dispatch **writer-critic** in **proofread mode** (categories 4, 5, 6, 8
only: writing quality, format, render, notation — not section mode, which would score
identification fidelity and claims-evidence on prose it never saw drafted). Returns text;
session saves to `quality_reports/reviews/writer-critic_<date>.md`, records: `python3 .claude/scripts/pipeline.py state record-score manuscript <score> --critic writer-critic --deductions <total> --report <path> --scope section:<file>`. The `section:` prefix is mandatory — without it the score falls through to the component branch and overwrites the whole-manuscript score instead of scoping to this file. Below 80 → writer fixes → critic re-reviews; `pipeline.py state strike writer` per failing round; strike three → User with a specific question.

---

## Section Standards

Every paper type shares the same backbone; the moves diverge by type. Section lengths and the
per-type moves are the "Section Length Summary" table in
`.claude/skills/write/templates/section-templates.md`, which is also where the full per-section
templates live — not in `.claude/agents/writer.md`, which only points at them.

---

## Quarto Conventions

- `@key` for textual citations ("@smith2024 shows..."), `[@key]` parenthetical (INV-9)
- `@tbl-label`, `@fig-label`, `@eq-label`, `@sec-label` — never a typed number
- Notation protocol: `.claude/skills/write/references/notation-protocol.md`

