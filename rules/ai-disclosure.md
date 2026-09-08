# AI Disclosure Rule

All work products of this pipeline must comply with Wiley's AI disclosure policy
(and equivalent COPE-aligned policies from Elsevier, Springer, AEA, etc.).

This rule defines:
1. What AI use requires disclosure
2. The log entry format all agents must follow
3. Disclosure statement templates
4. Where the disclosure goes in the paper

---

## What Requires Disclosure

Disclose whenever an AI tool is used for any of the following:

| Category | Examples | Disclosure required |
|----------|---------|-------------------|
| **Drafting** | Writing or rewriting any prose section | Yes |
| **Code** | Writing, refactoring, or debugging analysis scripts | Yes |
| **Literature search** | Identifying or summarizing papers | Yes |
| **Translation** | Converting text from another language | Yes |
| **Study design** | Proposing identification strategy or research design | Yes |
| **Data analysis** | Interpreting results, suggesting estimators | Yes |
| **Figures** | Generating or substantially editing figures | Yes |
| **Tables** | Generating table structure or content | Yes |

## What Does NOT Require Disclosure

| Category | Examples |
|----------|---------|
| **Grammar / spelling** | Autocorrect, Grammarly, basic spell-check |
| **Reformatting** | Changing indentation, whitespace, line breaks with no content change |
| **Rendering** | `quarto render` invocations |

---

## Log Entry Format

Every worker agent appends one entry to `ai_use_log.md` in the project root after completing work.
If the file does not exist, create it first using `templates/ai-use-log.md`.

**Format:**

```markdown
### YYYY-MM-DD — [agent-name] (Claude [model-id])
- **Task:** [one-line description, e.g. "Drafted Introduction and Data sections"]
- **Sections affected:** [comma-separated: Introduction | Background | Data | Strategy | Results | Robustness | Conclusion | Code | Figures | Tables | Literature]
- **Human review required:** Yes — author must review and verify before submission
```

**Example entries:**

```markdown
### 2026-05-29 — writer (Claude claude-sonnet-4-6)
- **Task:** Drafted Introduction and Data sections from strategy memo
- **Sections affected:** Introduction, Data
- **Human review required:** Yes — author must review and verify before submission

### 2026-05-29 — coder (Claude claude-sonnet-4-6)
- **Task:** Wrote main estimation scripts (feols DiD), robustness checks, and summary statistics
- **Sections affected:** Code, Tables, Figures
- **Human review required:** Yes — author must verify all results and test code before submission

### 2026-05-29 — librarian (Claude claude-sonnet-4-6)
- **Task:** Literature search on ESG and commercial real estate returns
- **Sections affected:** Literature
- **Human review required:** Yes — author must verify all cited papers independently
```

---

## Disclosure Statement Templates

### Wiley / COPE-Aligned (Use for: REE, JREFE, JFQA, JUE, JF, RFS, JFE)

```
The authors acknowledge the use of Claude ([model-id]), developed by Anthropic,
via Claude Code in the preparation of this manuscript. AI assistance was used to:
[summarized task list from ai_use_log.md]. All AI-generated content was reviewed,
verified, and substantially edited by the authors before inclusion. The authors take
full responsibility for the accuracy of all content, including verification of all
claims, citations, and analyses. No AI tool was used to generate, alter, or
manipulate original research data or results.
```

**Populate [summarized task list] from `ai_use_log.md`:** consolidate all entries into a plain-English list. Merge by category (e.g., all drafting entries become one bullet; all code entries become one bullet).

### Compact Version (Use when journal word limit is tight)

```
AI assistance (Claude, Anthropic) was used for initial drafting, code writing, and
literature search during manuscript preparation. All AI-generated content was reviewed
and verified by the authors. The authors take full responsibility for all content.
```

---

## Placement in Paper

In `manuscript_<project>.qmd`, place it as

```markdown
## AI Use Statement {.unnumbered}
```

at the end of the document — after References, before the Appendix. Use
`{.unnumbered}`, not bookdown's `{-}`.

---

## Enforcement

- **All worker agents** append to `ai_use_log.md` after completing work (required by each agent's own protocol)
- **At session end** (`/checkpoint`): confirm `ai_use_log.md` has been updated this session
- **Before submission** (`/submit`): verify AI Use Statement is populated in the manuscript and covers all log entries
- **verifier agent**: check `ai_use_log.md` exists and is non-empty; check manuscript has AI Use Statement (future work)

---

## Author Responsibilities (Per Wiley Policy)

1. Review and verify all AI-generated content before submission
2. Take full responsibility for accuracy of all claims, citations, and analyses
3. Do not represent AI-generated content as original human work
4. Review Terms and Conditions of any AI tool for IP conflicts with the publishing agreement
5. Confirm no AI was used to generate, alter, or manipulate original research data
