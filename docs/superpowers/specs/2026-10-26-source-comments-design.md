# Source comments: outside-world claims shown beside their source text

Date: 2026-10-26. Status: design, approved in chat by the author; builder check pending.

## 1. Intent and the why

A paper's claims about the outside world (what an MLS displayed, when a rule took effect, what a
court ordered) currently enter the manuscript on Claude's word. The pipeline checks numbers
mechanically (`prose_number_check.py`, the design-block hash, inline `r` expressions), but an
institutional fact is checked only by a critic's judgment, and nothing compares the sentence the
paper relies on with the sentence the source contains.

The incident that motivates this (NAR_settlement): on 2026-08-31 the litigation calendar marked
NWMLS's reform history VERIFIED from primary sources. What those sources supported was that
NWMLS moved compensation offers to "seller-direct" on 2022-10-03 and dropped the mandatory offer
in 2019. In the design that followed, this became "NWMLS stopped posting offers", and a
Washington-2022 treatment was built on it. The 2026-10-06 plan withdrew that design ("NWMLS never
stopped posting offers"), and the author rewrote the paper. The check confirmed a date; the paper
relied on a different proposition; nothing put the two side by side.

The author's requirement, in their words: show "the entire paragraph next to the claim so i can
read the context", with the exact sentence marked, and "ensure that the paragraph is in fact the
actual text from the source document rather than something claude quotes from memory". The author
edits and comments in Word, so the paragraph appears as a Word comment anchored to the claim.

## 2. Goals

1. Every outside-world claim in the manuscript can be tagged to a source entry.
2. On request, the Word build carries one Word comment per tagged claim, anchored to the claim's
   text, holding: source label and page, then the full source paragraph with the supporting
   sentence **underlined** (author's choice over bold, tested 2026-10-26).
3. The paragraph is never typed by Claude. A script extracts it from a local copy of the source;
   if the supporting sentence is not found verbatim in that file, the claim fails the check.
4. A plain Word or PDF build is unchanged. The sourced build is optional: whenever Claude is about
   to build a Word draft for the author, it offers "plain, or with source comments" and the author
   picks.
5. The verbatim check also runs quietly at every render, at commit and before the writer-critic,
   and **warns** on failures. It never blocks.
6. Ships in research-claude, so every paper project gets it.

## 3. Non-goals

- Numbers and model results. Those stay with `prose_number_check.py` and the claim helpers.
- Judging whether the source supports the claim. The author reads the paragraph and decides; the
  tool only guarantees the paragraph is real and shows it.
- Fetching sources from the web at build time. Sources must already be saved locally.
- PDF-format comments. Word is the reading surface; PDF output ignores the tags (renders the claim
  text only).

## 4. Anti-goals (failure even if it technically works)

- A paragraph or sentence that came from Claude's memory, a search snippet or a paraphrase
  appearing in a comment. Any path that can emit unverified text into a comment is a defect.
- Silent fallback: a claim whose sentence is not found must not get a comment with "close enough"
  text, and must not be dropped without a warning.
- Changing the plain build's output or making renders fail because of this feature.
- A noisy warning stream the author learns to ignore (e.g. warning on every render about every
  untagged sentence in the paper).

## 5. How it works (decided)

### 5.1 Tag in the manuscript

The claim text in the `.qmd` is wrapped in a span naming a source entry, e.g.

```markdown
[NWMLS listings continued to carry an offer of compensation after October 2022.]{.src ref="nwmls-form21-2023"}
```

Several claims may share one entry. The tag is inert in a plain build (renders as the claim text).

### 5.2 Source registry

One file per project (location left to the builder; `quality_reports/` or `data/raw/legal/` are
the natural homes). Each entry stores only:

- `id`
- `file`: path to the local copy (PDF, HTML, or text), inside the project
- `label`: human-readable source name for the comment header (e.g. "NWMLS Form 21 (Rev. 7/23), ¶ u")
- `page` (PDF) or locator (HTML)
- `sentence`: the one supporting sentence, as it appears in the source
- `sha256` of the file, recorded when the author approves the entry
- `approved_claim`: the claim text as it stood when the author approved it (see 5.5)
- `ocr`: true when the text came from OCR

The entry never stores the paragraph. The paragraph is always re-extracted from the file.

### 5.3 Extraction and the verbatim check

A script (in `scripts/`, shipped to projects like `prose_number_check.py`):

1. Extracts text from the file (`pdftotext` for PDFs; tested on NWMLS Form 21, 2026-10-26).
2. Applies the source type's cleanup rule. Tested need: NWMLS forms print a line number at the end
   of each line; these must be stripped or the match fails. A stray trailing line number ("216")
   still survived the spike's rule and must not.
3. Normalises whitespace and typographic quotes on both sides, then requires the `sentence` to
   occur verbatim in exactly one paragraph. Zero or several matches → the entry FAILS.
4. Returns that paragraph with the sentence marked for underline.
5. Compares the file's sha256 with the entry's; a mismatch marks the entry NEEDS REVIEW.

Spike (2026-10-26, scratchpad, not shipped): `src_para.py` extracted Form 21 ¶ u correctly and
refused "NWMLS stopped posting compensation offers." with exit 1.

### 5.4 The sourced Word build

A Quarto filter (Lua or a pre-render step; builder's choice) turns each tagged span into a Word
comment anchored to the claim text, using pandoc's comment spans:

```markdown
[<label>, p. <page>. <paragraph with [sentence]{.underline}>]{.comment-start id="N" author="Source check"}<claim text>[]{.comment-end id="N"}
```

Tested 2026-10-26: `quarto render` (1.9.37) to docx with NAR_settlement's `word-reference.docx`
and `fix_docx_floats.py` post-render produced `w:commentRangeStart/End` around the claim and a
comment whose supporting sentence carries `<w:u w:val="single"/>`; the author viewed it in Word
and approved the look. A FAILED entry gets no comment from source text; it gets a comment saying
"SOURCE CHECK FAILED: <reason>" so the gap is visible where the author reads.

The sourced build is selected explicitly (a Quarto profile or a flag; builder's choice) and
writes a separately named `.docx` so it never overwrites the plain draft.

### 5.5 Approval and drift

The author approves an entry after reading its comment. Approval records the file hash and the
claim text. If later the claim text in the manuscript changes, or the file changes, the entry
becomes NEEDS REVIEW and the comment header says so. This is the check that would have caught
"seller-direct" drifting into "stopped posting". How approval is recorded (a command, a column in
the registry, a chat line like the design token) is left to the builder, with one constraint: a
session must not approve on the author's behalf.

### 5.6 Quiet check and warnings

The verbatim check runs, warning only, at:

- every render (post-render, beside `fix_docx_floats.py` in `_quarto.yml`),
- commit (`pipeline.py commit-check`, as a WARN line, like a not-retrofitted prose check),
- `pipeline.py critic-inputs` (its own section in the log, for the writer-critic).

Warnings name each FAILED and NEEDS REVIEW entry, and each tag whose `ref` has no entry.

### 5.7 Offering the sourced build

Whenever Claude is about to build a Word draft for the author, it asks once: plain or with source
comments. This belongs in the rule/skill that owns Word builds (`rules/quarto-word.md` "Build",
and `/write` where it renders).

## 6. Integration points already in the pipeline

- `design.treatment.source: {cite, page, quote}` (core rule 13). Its `quote` is typed and judged by
  strategist-critic; nothing checks it against a file. The same verbatim check should cover it
  once the quote has a local file.
- `prose_number_check.py`'s allowlist lets "an institutional fact" stay a literal with a reason.
  Those rows are claims that should carry a source tag; the warning may name allowlisted
  institutional facts with no tag.
- NAR_settlement already has a numbers-only claim map (`quality_reports/claim_source_map_gen.py`,
  project-specific). This design covers the non-numeric side and does not replace it.

## 7. Constraints

- research-claude ships nothing project-specific (`scripts/check_fork.sh`). Source-type cleanup
  rules must be generic (e.g. "trailing line numbers") and selected per entry or per file.
- Shipped `scripts/` are listed in `scripts/SHIPPED`; a new shipped script goes there.
- Edits to `rules/`, `skills/`, `hooks/` are live in every paper on save: build on a branch.
- Hooks and checks fail open on internal error (pipeline convention), but a FAILED verbatim match
  is never treated as an internal error.
- No timeouts on live evals (repo CLAUDE.md).

## 8. Calls made after the builder check (Claude's calls, for the author to check)

1. **Approval is per tagged claim, not per entry.** Each tag carries its own id
   (`[...]{.src ref="nwmls-form21-2023" id="c1"}`), and approvals are recorded per tag id with
   the claim text as approved. Drift in one claim flags only that claim. `approved_claim` moves
   from the entry to the per-tag approval record.
2. **States:** UNREVIEWED (passes verbatim, never approved), APPROVED, NEEDS REVIEW (claim text or
   file hash changed since approval), FAILED (sentence not found verbatim, or a `ref` with no
   entry), NOT ON THIS MACHINE (file missing). The comment header shows the state. Warnings list
   FAILED and NEEDS REVIEW individually; UNREVIEWED and NOT ON THIS MACHINE are one summary line
   each ("4 claims not yet reviewed"), to keep the warning stream short.
3. **Source files are committed to the paper repo.** NAR_settlement already tracks 278 files under
   `data/raw/legal/` despite the seeded `data/raw/**` ignore, so committing primary sources is
   existing practice. The seeded `.gitignore` gains an exception for the sources folder; the
   existing papers get it by hand where needed. The global "never stage `data/raw/`" rule needs a
   matching carve-out for this folder, or sources move outside `data/raw/` (builder picks one and
   says which).
4. **`design.treatment.source.quote` is out of scope for this build.** Adding a file field would
   change the design hash and force every signed paper to re-sign. Future work: point the quote at
   a registry entry from outside the `design:` block.
5. **The render-time check is added to all seven existing papers' `_quarto.yml`** (each already
   runs `fix_docx_floats.py` post-render; Quarto's `post-render:` takes a list), one local commit
   per paper, plus the seed. Without it, existing papers would get only the commit and critic
   warnings.

## 9. Left to the builder

- Registry file format (CSV, YAML) and location.
- Lua filter versus pre-render step; profile versus flag for the sourced build.
- How approval is recorded (with the constraint in 5.5).
- HTML extraction method; how OCR'd PDFs are produced and flagged.
- Which sentences Claude tags. Claude's proposal, not confirmed by the author: Claude
  tags outside-world claims, tags when unsure, and lists untagged outside-world claims it notices
  rather than leaving them silently.
- Whether to retrofit NAR_settlement's current draft as the first live use.
