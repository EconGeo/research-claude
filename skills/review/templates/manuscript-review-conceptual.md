# Manuscript Review: Conceptual-Review Categories

Used by writer-critic **instead of** `manuscript-review-8-categories.md` when the paper type is
`conceptual-review` (structured literature review + framework-based synthesis; no data, no
estimation, no formal model). Same agent, same registry component (`manuscript`), same
three-strikes escalation. Invariants that presuppose data or Quarto chunks (INV-3, INV-4,
INV-11, INV-13, INV-25) do not apply; INV-1, INV-2, INV-7 (as terminology), INV-8 do.
Abstract, keyword, heading, voice and statement rules come from the target journal's profile
in `.claude/references/journal-profiles.md`, not from INV-5/INV-6.

## 1. Structure and Arc
- Follows the Conceptual Review arc in `.claude/references/narrative-arcs.md`.
- Research question stated once in the introduction and answered in the conclusion in the same terms.
- Background defines every term before the analysis uses it; design section precedes findings.
- One argument move per paragraph (`paragraph-moves.md`); no discursive paragraph that does not advance the claim chain.
- Roadmap, if present, is one sentence; no summarising restatement (e.g. a conclusion that re-lists findings).

## 2. Claims and Citations — Claim–Citation Table (mandatory)
Build the table per `claim-evidence-table.md`, with evidence = a cited source (author, year,
page for quotes) or "paper's own proposition". Verdicts as in that template.
- Every substantive claim cites a source or is explicitly labelled the paper's own proposition.
- Every direct quotation carries a page reference.
- Corpus and search numbers (records, assembled, analysed) are identical everywhere they appear:
  abstract, methodology, tables, supplement, response letter.
- Every in-text citation has a reference-list entry and every entry is cited (supplement-only
  entries live in the supplement's own list).

## 3. Framework Fidelity (replaces Identification Fidelity)
- The analytical framework is described as its source defines it (layers, mechanisms, terms).
- Findings are assigned to framework elements as the framework defines them; no element is silently redefined.
- No causal language beyond what the synthesised evidence supports (INV-8); case evidence is labelled illustrative.
- Framework blind spots and the "artifact of the lens" risk are stated in Limitations.

## 4. Writing Quality
Unchanged from `manuscript-review-8-categories.md` § 4 (24-pattern check).

## 5. Journal Format (replaces Quarto Format)
- Abstract within the profile's limit and type (structured/unstructured); keywords within range.
- Required statements present and in the profile's element order (e.g. funding, disclosure,
  generative-AI use, data availability).
- Heading numbering, spelling variety and voice rule (e.g. impersonal) as the profile states.
- Double-anonymised journal: the reviewer-facing version carries no author names,
  affiliations, "our previous work", or self-identifying disclosures.
- Tables have notes (INV-1); figures have captions and source/permission lines (INV-2).

## 6. Build (replaces Render)
- The declared build exits 0 (`pandoc <md> -f markdown-implicit_figures -o <docx>` for a Markdown
  manuscript; `quarto render` for a `.qmd`); every figure resolves.
- The profile's word definition is met, counted by the project's word-count gate if one exists.

## 7. Voice Fidelity
Unchanged, except that the journal profile's voice rule overrides the personal style guide
where they conflict (e.g. the guide's "we" vs a journal's impersonal voice).

## 8. Terminology Consistency (replaces Notation)
- Each key term and abbreviation is defined once, at first use, and used with one meaning
  throughout (INV-7 applied to terms).
- Where the paper declares a usage convention (e.g. one term for the paradigm and another for
  the paper's construct), every use follows it.

## Report Format
As `manuscript-review-8-categories.md`, with category names as above and
`**Paper type:** Conceptual-review`; the table section is headed "Claim–Citation Table".
