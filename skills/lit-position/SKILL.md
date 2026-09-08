---
name: lit-position
description: >
  Position a project against the literature using the local Zotero corpus. Calls
  ztp-research to find and ingest, ztp-review to synthesize, then produces the two
  artifacts ZotPilot does not — frontier_map.md and positioning.md. Use when starting
  a project, writing an introduction, or defending a contribution claim.
  Local-first per rules/literature-search-order.md.
allowed-tools: Read,Write,Edit,Grep,Glob,WebSearch,WebFetch
---

# Literature Positioning

A literature review is not a reading list. It is an argument about where a paper
sits — and the only part of it a referee actually tests is the sentence claiming
what this paper adds that the closest existing one does not.

ZotPilot finds and summarizes papers. It does not produce the two artifacts that
argument needs: a map of the frontier, and a defensible positioning claim. This
skill is the bridge.

**`zotpilot-skills/` is vendored verbatim and is never edited.** This skill calls
those skills; it does not modify them.

---

## Step 1 — Find and ingest (`ztp-research`)

Search order is non-negotiable (`.claude/rules/literature-search-order.md`):
local Zotero index first, external databases only for what the library lacks.

1. Extract the key terms from the research question, including the *method* terms
   and the *setting* terms separately — a paper using your method in another
   setting and a paper on your setting with another method are different kinds of
   neighbour, and you need both.
2. Invoke `ztp-research` for the topic. It handles external search → candidate
   selection → PDF ingest → tagging → indexing.
3. Follow citation chains on anything scoring 4 or 5 below: check its reference
   list, and check who has cited it since.
4. Flag **scooping risks** explicitly: working papers from the last three years
   with the same question and the same data.

## Step 2 — Synthesize (`ztp-review`)

Invoke `ztp-review` over the local corpus to pull claims and passages. Stay local
here; this step reads what Step 1 ingested.

## Step 3 — `annotated_bibliography.md`

One entry per paper — question, method, data, main result (sign and magnitude),
and **what it leaves open**. That last field is the one that matters: it is where
the contribution comes from, and it is the field a summary tool will not write
for you.

Score each paper for proximity:

| Score | Meaning |
|---|---|
| 5 | Directly competes — same question, same or similar setting |
| 4 | Closely related, different angle |
| 3 | Shares a method or a setting, not both |
| 2 | Tangentially relevant |
| 1 | Background / foundational |

Then group: directly related · same method, different setting · same setting,
different method · theoretical foundations · methods papers.

## Step 4 — `frontier_map.md`

ZotPilot produces nothing like this. Cluster the corpus into three states, and be
willing to put a paper in more than one:

- **Settled** — established well enough that contradicting it needs a strong prior.
- **Contested** — credible papers disagree. Say *what* they disagree about: the
  estimand, the identifying assumption, the sample, or the interpretation.
- **Unexamined** — nobody has asked. Distinguish "nobody has asked" from "people
  asked and it did not work," which looks identical in a literature search and is
  the more common case.

## Step 5 — `positioning.md`

One paragraph. Name the two or three papers this project sits between, and state
what it adds that they do not. Then stress-test it:

- Take the single closest paper (highest proximity). Write the sentence its author
  would use to say this project is redundant. If you cannot answer that sentence,
  the positioning is not defensible yet — say so rather than writing around it.
- A contribution that is only "newer data" or "another country" is a data update,
  not a contribution. Label it honestly; some papers genuinely are updates.

## Step 6 — Self-check

Score the output against the six categories inherited from the retired
`librarian-critic`:

1. **Coverage** — missing subfields, adjacent literatures, seminal papers, or the
   econometric-methods papers the strategy depends on?
2. **Journal quality** — is more than half the corpus unpublished working papers?
   Are the top generals and the relevant field journals represented?
3. **Scope calibration** — too narrow to position against, or too broad to focus?
4. **Recency** — anything from the last two years missing? Scooping risks named?
   Working-paper versions superseded by published ones?
5. **Categorization** — are the proximity scores defensible? Does the frontier map
   actually locate a gap, or does it just list?
6. **Defensibility** — does `positioning.md` survive Step 5's stress test against
   the closest paper?

Report the score and the gaps. Do not quietly fix a coverage gap by lowering the
claim.

---

## Output

Save to `quality_reports/literature/<project>/`:

- `annotated_bibliography.md`
- `frontier_map.md`
- `positioning.md`
- BibTeX for anything cited, exported from Zotero — Zotero stays the source of
  truth for what has been read, not a hand-maintained `.bib`

## What this skill does NOT do

- Does not write the literature review section — that is `/write`.
- Does not propose an identification strategy — that is `/strategize`.
- Does not edit anything under `zotpilot-skills/`.
