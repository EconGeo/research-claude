# `section` predicates match the section name, not the heading's typography

**Date:** 2026-09-25 · **Status:** Decided

**The defect.** `pipeline.py`'s `section` predicate compared heading text exactly
(`pred["heading"] in headings(f)`). The shipped template `skills/strategize/templates/strategy-memo.md`
writes numbered headings (`## 1. Estimand` … `## 5. Threats`), so no memo written from the
template could pass. `tested:` on the four real memos under `~/Research/*/quality_reports/strategy/`
every one failed all five of `post strategist`'s section checks (`## 1. Estimand`,
`### 1. Estimand`, `## Section 1: Estimand and Design Choice`). `post strategist` had never passed
on a real memo; the tests passed only because their fixtures wrote unnumbered headings the
template never produces.

**What changes.** `section_key()` reduces both the declared name and each heading to a section
name before comparing: a leading section number (`1.`, `2.3`, `3`, `Section 1:`) and trailing
parenthetical qualifiers (`(C1)`, `(short; detail in …)`) are dropped, whitespace is collapsed,
case is folded. What remains must **equal** the name. `Key Assumptions and Threats` is not the
Threats section, and `Threats to validity` is not either. The tolerance covers typography only,
never substring. `tested:` `tests/test_pipeline.py`: the template, copied verbatim, passes; the
real-memo shapes pass; a numbered memo missing a section still fails; a heading that only
contains a name still fails. Against the four real memos, three now pass all five. zoning2026's
2026-06-04 memo still fails Assumptions and Threats, correctly: it merges them into one section
and has no Threats section.

**Why the matcher and not the template.** Three reasons:
- Unnumbered template headings would fix no existing memo.
- The numbering is load-bearing: memos and critic reports cite sections by number (`§2.3`,
  "critic 2.2 fix").
- Authors vary typography regardless of what the template says. The NAR memo written the same day
  uses `### 4. Robustness plan (short; …)`.

A gate that checks for content should not fail on typography.

**Why every `section` predicate, not a per-predicate option.** The only other `section` use is the
manuscript's `Theory` heading (`theorist` produces, `theorist-critic` requires). `# 3 Theory` is
equally a Theory section there. A `match:` key would add registry schema, validation and rendering
for a distinction no predicate needs. The registry is unchanged, so `rules/permissions.md` is
unchanged.

**Companion fix, same day: headings inside fenced code are not headings.** `headings()` read
every `#` line, so an R comment `# Threats` in a memo's pseudo-code, or `# Theory` in a
manuscript chunk, satisfied the predicate. That was a fail-open hole in a gate. It now skips fenced
code by CommonMark's rule: a fence closes only on a run of the same character at least as long.
`tested:` no real memo or manuscript changes result (26 files scanned: every `.md` under
`~/Research/*/quality_reports/strategy/` and every top-level `.qmd`). So the hole was latent. The
fix is still worth having because the template's Specification section carries an R pseudo-code
block, where a `# Specification` comment is natural. The template's own outer fence was
` ```markdown ` around a nested ` ```r ` block, which Markdown closes at ` ```r `. It is now a
four-backtick fence. `tests/test_pipeline.py` extracts the memo body from that fence.

**Recorded on disk:** `scripts/pipeline.py` (`section_key`, `headings`); `rules/lifecycle.md`
§ Predicate types; the template's purpose line and outer fence;
`docs/decisions/clo-author-divergences.md` D-3 (2026-09-25 amendment).
