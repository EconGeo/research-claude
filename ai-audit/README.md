# ai-audit

Standalone Claude Code skills package for auditing AI-generated academic prose.
Two complementary tools — no Python dependencies.

| Tool | What it does | When to use |
|------|-------------|-------------|
| `/civilize` | Detects AI-voice tells (lexical, structural, stylistic) in `.tex`, `.qmd`, `.md` | Before journal submission or posting a working paper |
| `/verify-claims` | Chain-of-Verification (CoVe) hallucination check — fresh-context verifier never sees the original draft | After any text generation that asserts facts about papers, datasets, or numerical results |

Both are **read-only auditors** — they flag problems but do not rewrite. The author edits manually.

---

## Why detect-only (no auto-rewrite)?

We deliberately do not ship `/civilize --rewrite`. Cross-vendor research (Cursor / Aider community findings) finds that auto-rewriting prose to strip AI-voice tells degrades quality more often than it improves it — the rewriter introduces its *own* tells. The detect-and-flag pattern preserves authorial voice; the cost is your editing time, which is exactly the cost we want to pay.

If you find yourself reaching for an auto-rewriter, that is the signal to rewrite the paragraph from scratch — not to patch the tells one by one.

---

## Installation

### Copy into your project (project-scoped, recommended)

```bash
# Clone this repo
git clone https://github.com/EconGeo/ai-audit.git
cd ai-audit

# Copy into your project's .claude/ directory
cp -r skills/civilize    /your-project/.claude/skills/
cp -r skills/verify-claims /your-project/.claude/skills/
cp agents/civilize-auditor.md /your-project/.claude/agents/
cp agents/claim-verifier.md   /your-project/.claude/agents/
cp rules/ai-disclosure.md     /your-project/.claude/rules/
```

### Install globally (active in all Claude Code projects)

```bash
cp -r skills/civilize    ~/.claude/skills/
cp -r skills/verify-claims ~/.claude/skills/
cp agents/civilize-auditor.md ~/.claude/agents/
cp agents/claim-verifier.md   ~/.claude/agents/
cp rules/ai-disclosure.md     ~/.claude/rules/
```

### Via research-claude apply.sh (recommended if using the full research stack)

If you're using [EconGeo/research-claude](https://github.com/EconGeo/research-claude), these skills are installed automatically when you run `./apply.sh`.

---

## Usage

### `/civilize` — AI-voice tells audit

```
/civilize paper/main.tex
/civilize paper/main.tex --severity high    # only high-severity tells
/civilize all                               # audit all .tex/.qmd/.md files
```

Output: a report at `quality_reports/civilize_<filename>_report.md` with location (line), category, severity (HIGH/MED/LOW) and one suggested rewrite per finding, plus a summary recommendation — rewrite the affected sections (> 8 HIGH per 1000 words), strip the tells (5–8), or cosmetic cleanup (< 5).

**Why audit before submission.** Referees and editors increasingly recognise AI-generated prose. The tells are not stylistic preferences — they are statistically conspicuous patterns the LLM training distribution produces at higher rates than human academic writers. Even good substance pays a credibility tax if the prose reads as AI-drafted; a growing number of venues require disclosure or prohibit AI-drafted text; boilerplate transitions usually cover a logical gap the author did not think through; and authors who use AI tools heavily can still keep their own voice by stripping the model's lexical fingerprint. The cost is detection, not rewriting — once the report flags the tells, removal is mechanical.

**When to run it.** Before journal submission; before posting a working paper, preprint or SSRN draft; after any AI-assisted prose generation (R&R response drafts, lit-review synthesis, abstract revisions); and as a self-discipline pass after long writing sessions — your own writing drifts toward LLM patterns when you stare at LLM output all day, so run it even on prose you wrote yourself.

**When not to.** Not on `.bib`, `.R`, or other non-prose files (the detectors are tuned for academic prose), not on code comments (the tells are different), not on UI/UX copy (voice norms diverge).

**What it is not.** Not a rewriter (see [Why detect-only](#why-detect-only-no-auto-rewrite)); not a substance reviewer (use a manuscript review — in research-claude, `/review`); not a grammar checker (use a proofreading pass — in research-claude, `/review --proofread`); not a fact-checker (use `/verify-claims`). `/civilize` is the *voice* lens. Run it alongside the others — none of them substitute.

**The 10 detection categories** are defined, with their severity rules, in [`agents/civilize-auditor.md`](agents/civilize-auditor.md):

1. Boilerplate transitions ("Moreover,", "Furthermore,", "It is important to note that", "In conclusion,")
2. AI-cliché lexicon ("delve into", "navigate the complexities", "rich tapestry", "robust framework", "shed light on", "play a crucial role")
3. Em-dash and punctuation overuse (> 3 em-dashes or ≥ 3 semicolons in a paragraph; repeated triple-Oxford-comma cadence)
4. Symmetric paragraph shapes (topic sentence → three examples → summarising clause, repeated across consecutive paragraphs)
5. Tricolon abuse (> 4 three-part lists per page; stacked adjective tricolons)
6. Hedging stacking ("might potentially be argued", "could possibly suggest")
7. "Not only X, but also Y" frames (> 2 per paper, non-parallel X and Y, or as paragraph openers)
8. Formulaic openers ("This paper does X.", openers that restate the section title, "In this paper, we..." where the discipline avoids it)
9. Hyphenation excess (≥ 3 compound modifiers such as "data-driven", "evidence-based" in one paragraph)
10. Sycophancy / self-important framing ("This important contribution", "Our novel approach", self-citation as "groundbreaking")

### `/verify-claims` — Chain-of-Verification

```
/verify-claims paper/main.tex --source papers/smith2024.pdf
/verify-claims paper/main.tex                              # infers sources from context
/verify-claims paper/main.tex --no-fail-closed             # downgrade a FAIL outcome to a warning
```

**Architecture:** The `claim-verifier` agent runs in a fresh (forked) context — it never sees the original draft. It receives only the extracted claims + source material, and answers verification questions independently. This architectural separation (context isolation) is the CoVe independence trick from Dhuliawala et al. 2023 (arXiv:2309.11495).

Output: a report at `quality_reports/verify_claims_<filename>_<date>.md`, written on every outcome, with the per-claim verdicts and the overall PASS / PARTIAL / FAIL.

**Severity tiers:**
- `HIGH-WARN`: Fabricated citation / numerical contradiction / directional contradiction → outcome **FAIL** (the report says do not commit; nothing enforces it mechanically)
- `MED-WARN`: Transient retrieval failure (source not accessible)
- `LOW-WARN`: Source genuinely inaccessible (paywalled, link rot)

---

## AI disclosure rule

`rules/ai-disclosure.md` defines what AI use requires disclosure (drafting, code, literature search, figures, tables) and provides disclosure statement templates for Wiley/COPE-aligned journals.

Install the rule to auto-enforce the `ai_use_log.md` maintenance workflow in your project.

---

## Uninstall

Delete the installed files from `.claude/` in your project (or from `~/.claude/` if globally installed).

No Python environments, no global state, no MCP registrations — just `.claude/` files.

---

## Attribution

`/civilize` was designed based on cross-vendor research on AI-voice detection in academic prose.
`/verify-claims` adapts the Chain-of-Verification protocol from:
> Dhuliawala, S., Komeili, M., Xu, J., Raileanu, R., Li, X., Celikyilmaz, A., & Weston, J. (2023). *Chain-of-Verification Reduces Hallucination in Large Language Models.* arXiv:2309.11495.
