---
name: civilize
description: Read-only audit of `.tex`, `.qmd`, or `.md` text for AI-voice tells — boilerplate transitions ("Moreover", "Furthermore", "It is important to note that"), AI-cliché lexicon ("delve", "navigate the complexities", "tapestry", "robust framework"), em-dash overuse, symmetric paragraph shapes, tricolon abuse, hedging stacking, "not only X but also Y" frames, and formulaic openers. Produces a report; does NOT rewrite. Use when user says "civilize", "does this sound like AI?", "check for AI tells", "de-AI this draft", "remove AI voice", "audit my prose for sycophancy", or before journal submission / posting a working paper.
author: Claude Code Academic Workflow
version: 1.1.0
argument-hint: "[filename or 'all'] [--severity low|med|high]"
disable-model-invocation: true
allowed-tools: ["Read", "Grep", "Glob", "Write", "Agent"]
---

# `/civilize` — AI-voice audit (detect-and-flag)

Audit the target file (or all paper-like files) for AI-voice tells in academic prose and write a structured report. **This skill does not rewrite.** The author edits. Why it is detect-only, when to run it, and how it pairs with a proofreading pass and `/verify-claims` are in the package [README](../../README.md#civilize--ai-voice-tells-audit).

## Steps

1. **Identify files to audit.**
   - `$ARGUMENTS` starts with a filename → audit that file only.
   - `$ARGUMENTS` is `all` → audit every `.qmd`, `.tex` and `.md` manuscript file in the project, the declared manuscript first where the host pipeline declares one. Reference papers by other authors are not audited.
   - Skip `.bib`, `.R`, `.py`, code files, and any file under `scripts/`.

2. **Parse `--severity`** (default: report all).
   - `low` → report all findings.
   - `med` → suppress LOW findings.
   - `high` → report only HIGH findings.

3. **For each file, launch the `civilize-auditor` agent** (`Agent` tool, `subagent_type=civilize-auditor`) with the file path and the severity threshold. The 10 detection categories, their severity rules, and the report format are defined in [`agents/civilize-auditor.md`](../../agents/civilize-auditor.md) — the agent owns them; do not restate or re-derive them here.

4. **Receive the structured report** from the agent. One row per finding:

   ```
   line N | category | severity | current text | suggested rewrite or "remove"
   ```

5. **Write the report** to `quality_reports/civilize_<filename>_report.md`:
   - per-category counts (HIGH / MED / LOW);
   - the per-finding table;
   - a summary recommendation from HIGH findings per 1000 words: **> 8** → prose reads as AI-drafted, rewrite the affected sections rather than patch; **5–8** → substantial AI voice, strip the tells before submission; **< 5** → light, mostly cosmetic cleanup.

6. **Present the summary** to the user: total findings per category, the three most concentrated paragraphs, and the action recommendation (rewrite vs. strip vs. cosmetic).

## Output

- Report at `quality_reports/civilize_<filename>_report.md` (gitignored).
- Summary in the conversation.
- **No file edits.** The user reads the report and applies changes manually.
