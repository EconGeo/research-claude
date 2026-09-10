# ai-audit

Standalone Claude Code skills package for auditing AI-generated academic prose.
Two complementary tools — no Python dependencies.

| Tool | What it does | When to use |
|------|-------------|-------------|
| `/humanize` | Detects AI-voice tells (lexical, structural, stylistic) in `.tex`, `.qmd`, `.md` | Before journal submission or posting a working paper |
| `/verify-claims` | Chain-of-Verification (CoVe) hallucination check — fresh-context verifier never sees the original draft | After any text generation that asserts facts about papers, datasets, or numerical results |

Both are **read-only auditors** — they flag problems but do not rewrite. The author edits manually.

---

## Why detect-only (no auto-rewrite)?

Cross-vendor research (Cursor/Aider community) shows that auto-rewriting AI-voice tells degrades prose quality and introduces *new* tells. The author edits manually — that's the price of preserving voice. Same rationale as keeping `/proofread` advisory.

---

## Installation

### Copy into your project (project-scoped, recommended)

```bash
# Clone this repo
git clone https://github.com/EconGeo/ai-audit.git
cd ai-audit

# Copy into your project's .claude/ directory
cp -r skills/humanize    /your-project/.claude/skills/
cp -r skills/verify-claims /your-project/.claude/skills/
cp agents/humanize-auditor.md /your-project/.claude/agents/
cp agents/claim-verifier.md   /your-project/.claude/agents/
cp rules/ai-disclosure.md     /your-project/.claude/rules/
```

### Install globally (active in all Claude Code projects)

```bash
cp -r skills/humanize    ~/.claude/skills/
cp -r skills/verify-claims ~/.claude/skills/
cp agents/humanize-auditor.md ~/.claude/agents/
cp agents/claim-verifier.md   ~/.claude/agents/
cp rules/ai-disclosure.md     ~/.claude/rules/
```

### Via research-claude apply.sh (recommended if using the full research stack)

If you're using [EconGeo/research-claude](https://github.com/EconGeo/research-claude), these skills are installed automatically when you run `./apply.sh`.

---

## Usage

### `/humanize` — AI-voice tells audit

```
/humanize paper/main.tex
/humanize paper/main.tex --severity high    # only high-severity tells
/humanize all                               # audit all .tex/.qmd/.md files
```

Checks for 10 detection categories:
1. Boilerplate transitions ("Moreover", "Furthermore", "It is important to note that")
2. AI-cliché lexicon ("delve", "navigate the complexities", "tapestry", "robust framework")
3. Em-dash overuse (AI-drafted prose uses `—` at 3-5× human rate)
4. Symmetric paragraph shapes (each paragraph same length — sign of templated structure)
5. Tricolon abuse (three-part lists used compulsively)
6. Hedging stacking ("it is worth noting that, while acknowledging that, it should be emphasized")
7. "Not only X but also Y" frames
8. Formulaic openers ("In today's rapidly evolving...", "This paper examines...")
9. Hyphenation excess (AI over-hyphenates: "context-dependent", "evidence-based")
10. Sycophancy / self-important framing ("groundbreaking", "novel contribution", "fills a gap")

Output: structured report with location (file:line), severity (HIGH/MED/LOW), and suggested rewrites.

### `/verify-claims` — Chain-of-Verification

```
/verify-claims paper/main.tex --source papers/smith2024.pdf
/verify-claims paper/main.tex                              # infers sources from context
/verify-claims paper/main.tex --no-fail-closed             # warnings only; don't block commit
```

**Architecture:** The `claim-verifier` agent runs in a fresh (forked) context — it never sees the original draft. It receives only the extracted claims + source material, and answers verification questions independently. This architectural separation (context isolation) is the CoVe independence trick from Dhuliawala et al. 2023 (arXiv:2309.11495).

**Severity tiers:**
- `HIGH-WARN`: Fabricated citation / numerical contradiction / directional contradiction → **blocks `/commit`**
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

`/humanize` was designed based on cross-vendor research on AI-voice detection in academic prose.
`/verify-claims` adapts the Chain-of-Verification protocol from:
> Dhuliawala, S., Komeili, M., Xu, J., Raileanu, R., Li, X., Celikyilmaz, A., & Weston, J. (2023). *Chain-of-Verification Reduces Hallucination in Large Language Models.* arXiv:2309.11495.
