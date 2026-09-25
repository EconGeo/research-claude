---
name: talk
description: Create and audit Quarto RevealJS presentations. Combines talk creation, visual audit, and rendering.
argument-hint: "[mode: create | audit | render] [format: job-market | seminar | short | lightning] [file path] [--yes]"
allowed-tools: Read,Grep,Glob,Write,Edit,Agent,Bash
---

# Talk

Create, audit, or render Quarto RevealJS presentations.

**Input:** `$ARGUMENTS` — mode and format/path.

---

## Modes

### `/talk create [format]` — Create Quarto RevealJS Talk

Generate a presentation from the paper.

**Agents:** Storyteller (creator), then storyteller-critic (reviewer)

#### Format Constraints

Slide counts, durations and per-format rules for all four formats are
`talk/templates/format-constraints.md` — the Storyteller reads this file directly
(`.claude/agents/storyteller.md`); not restated here so there is one number to keep current, not two.

#### Workflow

**Step 1: Parse Arguments**

- **Format** (required): `job-market` | `seminar` | `short` | `lightning`
- **Paper path** (optional): defaults to `manuscript_<project>.qmd`
- If no format specified, ask the user.
- **Resolve the manuscript symlink.** Run `python3 .claude/scripts/pipeline.py manuscript` to
  get the declared manuscript filename. If `talks/<manuscript filename>` does not already exist,
  create it as a relative symlink to `../<manuscript filename>` before rendering any talk — talks
  embed the manuscript by bare filename, and the embed only resolves when the source is reachable
  from inside `talks/`. (The embed probe that established this lives in the
  research-claude repo's `docs/audits/`, which is NOT linked into a project — do not
  expect to find it here.)

**Step 1b: Option gate — hook and outline**

Read the paper's arc (`.claude/references/narrative-arcs.md`, the `**Arc:**` line for its
type). **Option gate** (`.claude/rules/option-gates.md`): 5–8 hooks / key-slide framings —
columns *hook*, *key slide*, *first result shown*, *what is cut for this format* — each with a
one-line outline, ranked, wait (`--yes` takes rank 1). The Storyteller is dispatched with the
pick; the pick is recorded in the talk file's YAML comment block.

**Step 2: Dispatch Storyteller**

Read the paper and extract: research question, identification strategy, main result, secondary results, robustness checks, key figures/tables, institutional background. Design narrative arc for the chosen format. Build the slide file with shared preamble if available.

The Storyteller follows these design principles:
- **One idea per slide** — never cram two concepts onto one frame
- **Figures over tables; tables in backup** — audiences absorb figures instantly; regression tables belong in backup slides where referees can inspect them during Q&A
- **Build tension** — motivation → question → method → findings → implications
- **Transition slides between major sections** — signal where the talk is going
- **All claims must appear in the paper** — the paper is the single source of truth; never add results or claims that are not in the manuscript

Render with `quarto render`.

Read `.claude/references/quarto-authoring.md` (Format matrix, Diagrams) first: RevealJS
accepts raw HTML that Beamer and PDF drop, and a `{dot}`/`{mermaid}` cell without `fig-width`
overflows the slide silently.

Save to `talks/[format]_talk.qmd`.

**Step 3: Dispatch Storyteller-Critic**

After the Storyteller returns, dispatch the storyteller-critic to review. Six categories —
narrative flow, visual quality, content fidelity, scope for format, compilation, paper-type
coherence — defined in `.claude/skills/review/templates/talk-review-6-categories.md`, which
storyteller-critic already reads directly; not restated here.

Score as advisory (non-blocking). storyteller-critic returns its report as text; session saves it to `quality_reports/reviews/storyteller-critic_<date>.md`.

**Step 4: Fix Critical Issues**

If the storyteller-critic finds Critical issues (compilation failures, content not in paper):
1. Re-dispatch Storyteller with specific fixes; `pipeline.py state strike storyteller` per
   failing round; strike three → escalate to the registry's escalation target (writer) with a
   specific question
2. Re-run storyteller-critic to verify

**Step 5: Present Results**

Report to the user:
1. Generated file path
2. Slide count and format compliance
3. Storyteller-critic score (advisory, non-blocking)
4. TODO items (missing figures, tables not yet generated)

---

### `/talk audit [file]` — Visual Audit

Check existing slides for layout issues.

Run visual quality checks:
- Text overflow on any slide
- Font sizes (>= 10pt for projection)
- Table readability
- Figure sizing and labels
- Consistent formatting
- Slide overflow: content running past the bottom of a 16:9 frame

---

### `/talk render [file]` — Render Talk

Before rendering, confirm `talks/<manuscript filename>` exists (per Step 1 above); create it if
absent — the embed will not resolve otherwise.

```bash
quarto render talks/[file]
```

Pass: exit 0 and a fresh `.html`. Check the render log for `ERROR`/`WARNING`
and for unresolved cross-references.

---

## Bundled Resources

| Resource | Path | What It Contains |
|----------|------|-----------------|
| Narrative arcs | `.claude/references/narrative-arcs.md` | Paper-type-specific story structures (reduced-form, structural, theory+empirics, descriptive) with pacing and audience calibration — shared with `/write` (Step 2), not `/talk`-only |
| Format constraints | `talk/templates/format-constraints.md` | Slide counts, durations, per-format rules for all 4 formats |
| Quarto scaffold | `.claude/skills/talk/templates/quarto-scaffold.qmd` | RevealJS skeleton with YAML config, section dividers, figure/equation slots (default) |
| Slide design | `talk/references/slide-design-principles.md` | Visual design principles: font sizes, colors, builds, rhythm |
| Gotchas | `talk/gotchas.md` | Known failure points and edge cases |

The Storyteller agent reads these resources before building slides. The narrative arc determines the slide sequence; the format constraints determine scope.

---

## Principles

- **Paper is authoritative.** Every claim must appear in the paper.
- **Figures over tables.** Audiences absorb figures instantly. Put regression tables in backup slides for Q&A.
- **Less is more.** Especially for short and lightning formats — ruthlessly cut.
- **One idea per slide.** If you need a second point, make a second slide.
- **Audience calibration.** Job market = demonstrate rigor and command of the literature. Seminar = sell the interesting result. Short = method and key finding. Lightning = sell the idea in one breath.
- **Advisory scoring.** Talk scores don't block commits.
- **Worker-critic pairing.** Storyteller creates, storyteller-critic critiques. Never skip the review.
