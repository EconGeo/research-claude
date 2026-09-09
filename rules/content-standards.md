---
paths:
  - "**/*.R"
  - "**/*.py"
  - "**/*.jl"
  - "**/*.do"
  - "**/*.qmd"
  - "master_supporting_docs/**"
  - "explorations/**"
---

# Content Standards: Tables, Figures, PDFs, and Explorations

---

## 1. Table Standards

Owned by `.claude/skills/analyze/references/table-standards.md` — layout,
coefficient display, significance conventions, panel structure, and when a table
should have been a figure. Mechanics are in `.claude/rules/quarto-word.md`
(flextable) and `.claude/rules/quarto-pdf.md` (kableExtra).

Do not restate them here. This file previously carried a second copy of the table
rules, and the copy went stale: it told agents to export a bare LaTeX table fragment and
wrap it in a notes environment, which this pipeline has not done for months.

**The two things that are always true:** every table is a `tbl-`-labelled chunk in
`manuscript_<project>.qmd` with a `#| tbl-cap:` and notes (INV-1), and no number
from a table is ever typed into prose — it is an inline `` `r ` `` expression
against the model object (INV-11).

---

## 2. Figure Standards

Owned by `.claude/skills/analyze/references/figure-standards.md` — themes, axis
labels, color, size, captions, and the common figure types.

**The two things that are always true:** every figure is a `fig-`-labelled chunk
with a `#| fig-cap:` and no in-plot title (INV-12/INV-2), and nothing is
`ggsave()`d to disk for manual inclusion — Quarto emits vector for PDF and PNG for
Word, and cannot embed a PDF figure in a Word document at all.

---

## 3. PDF Processing

### The Safe Processing Workflow

**Step 1: Receive PDF Upload**
- User uploads PDF to `master_supporting_docs/supporting_papers/` or `supporting_slides/`
- Claude DOES NOT attempt to read it directly

**Step 2: Check PDF Properties**
```bash
pdfinfo paper_name.pdf | grep "Pages:"
ls -lh paper_name.pdf
```

**Step 3: Create Subfolder and Split**
```bash
mkdir -p paper_name/

for i in {0..9}; do
  start=$((i*5 + 1))
  end=$(((i+1)*5))
  gs -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dSAFER \
     -dFirstPage=$start -dLastPage=$end \
     -sOutputFile="paper_name/paper_name_p$(printf '%03d' $start)-$(printf '%03d' $end).pdf" \
     paper_name.pdf 2>/dev/null
done
```

**Step 4: Process Chunks Intelligently**
- Read chunks ONE AT A TIME using the Read tool
- Extract key information from each chunk
- Build understanding progressively
- Don't try to hold all chunks in working memory

**Step 5: Selective Deep Reading**
- After scanning all chunks, identify the most relevant sections
- Only read those sections in detail for slide development
- Skip appendices, references, or less relevant sections unless needed

### Error Handling Protocol

**If a chunk fails to process:**
1. Note the problematic chunk (e.g., "Chunk p021-025 failed")
2. Try splitting into 1-2 page pieces
3. If still failing, skip and document the gap

**If splitting fails:**
1. Check if Ghostscript is installed: `gs --version`
2. Try alternative: `pdftk paper.pdf burst output paper_%03d.pdf`
3. If all else fails, ask user to upload specific page ranges manually

**If memory/token issues persist:**
1. Process only 2-3 chunks per session
2. Focus on specific sections user identifies as most important

---

## 4. Explorations

**All experimental work goes into `explorations/` first**, as one `.qmd` per exploration:

```
explorations/
├── ACTIVE.md                        # one line per live exploration: goal, status
├── <name>.qmd                       # self-contained: its own setup chunk, its own data chunk
└── archive/<name>.qmd               # abandoned or graduated, with a one-paragraph note at the top
```

An exploration renders on its own (`quarto render explorations/<name>.qmd`), reads `data/raw/`
directly, and never writes to disk. **Graduation** moves its chunks into the declared manuscript
(with `cache.extra`/`dependson` per `.claude/rules/quarto-empirical.md`) and archives the file;
nothing is copied into a script tree because there is no script tree.

Quality threshold for an exploration: 60/100 (production is 80). No plan needed. Kill switch:
archive with a note ("Attempted X, hit blocker Y") and move on.
