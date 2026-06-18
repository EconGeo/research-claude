# Pipeline Precedence + Per-Project Manuscript Naming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve research-claude's clo-author layout conflicts by declaring precedence (one new rule, zero submodule edits), and make the manuscript default to `manuscript_<project>.qmd`.

**Architecture:** Add one research-claude-owned rule, `pipeline-precedence.md`, that declares `quarto-empirical.md` authoritative over clo-author's old-layout instructions and provides an old→new translation map. Update four existing research-claude rules to document the `manuscript_<project>.qmd` naming convention (project-directory basename). Update `apply.sh`'s documentation text only. No clo-author submodule files are touched; the new rule rides apply.sh's existing research-claude `rules/` copy step.

**Tech Stack:** Markdown rules, Bash (`apply.sh`), `grep` for verification. No build system, no test runner — verification is grep assertions, an apply.sh smoke test, and a submodule-clean check.

## Global Constraints

- **Naming convention (verbatim):** `manuscript_<project>.qmd`, where `<project>` is the project **directory basename** (e.g. the `zoning2026/` project → `manuscript_zoning2026.qmd`). Use the literal placeholder string `manuscript_<project>.qmd` in rule text.
- **Zero submodule edits:** no file under `submodules/clo-author/**` (or any other submodule) may be created, modified, or deleted.
- **No skill rewrites:** do not edit `analyze`/`write`/`revise` SKILL.md or any clo-author skill/rule/agent.
- **Mechanism is rules-convention-only:** do NOT add manuscript scaffolding to `apply.sh`, do NOT parse git remotes, do NOT change `.gitignore`.
- **Canonical source of the naming convention** is `pipeline-precedence.md`; the four edited rules carry a one-line note that references the same placeholder.
- **Commit policy:** the repo owner commits only when they ask. Each task below ends with a commit step; **do not run it unless the user has said to commit** — otherwise stop at the verification step and report.
- **SESSION_REPORT / docs location:** repo dev docs live under `docs/`; this repo overrides the checkpoint default (see repo `CLAUDE.md`).

---

### Task 1: Create `rules/pipeline-precedence.md`

**Files:**
- Create: `rules/pipeline-precedence.md`
- Verify against: `submodules/clo-author/.claude/skills/{analyze,write,revise}/SKILL.md`, `submodules/clo-author/.claude/rules/{working-paper-format,content-invariants,permissions}.md`, `rules/quarto-empirical.md`

**Interfaces:**
- Consumes: nothing (standalone rule loaded as Claude context).
- Produces: the canonical statement of (a) quarto-empirical precedence over the six clo-author files and (b) the `manuscript_<project>.qmd` naming convention. Tasks 2–5 reference this convention; Task 6 lists this file in apply.sh.

- [ ] **Step 1: Write the rule file**

Create `rules/pipeline-precedence.md` with exactly this content:

```markdown
# Pipeline Precedence: Quarto-Empirical Overrides Legacy Layout

**This rule resolves the file-layout contradiction between research-claude's
single-`.qmd` pipeline and clo-author's inherited LaTeX/multi-file layout.**

research-claude installs clo-author's research-phase skills and rules (`/analyze`,
`/write`, `/revise`, `working-paper-format.md`, `content-invariants.md`,
`permissions.md`). Those files are mature and actively maintained upstream, and their
**methodological** content — analysis rigor, writing moves, revision discipline,
referee simulation, numerical discipline — fully applies. Only their **file-layout
assumptions** predate the quarto-empirical pipeline.

## Precedence Rule

When `quarto-empirical.md` is present in `.claude/rules/`, it is **authoritative over
all file-layout instructions** in the following clo-author files:

- `skills/analyze/SKILL.md`
- `skills/write/SKILL.md`
- `skills/revise/SKILL.md`
- `rules/working-paper-format.md`
- `rules/content-invariants.md` (specifically INV-12 and INV-13)
- `rules/permissions.md`

Follow those files for *how to think* (what makes a good analysis, a good section, a
good revision). Follow `quarto-empirical.md` for *where things live*. Where they
conflict on layout, quarto-empirical wins — no exceptions.

## Translation Map (legacy layout → quarto-empirical)

| clo-author layout instruction | quarto-empirical equivalent |
|---|---|
| `scripts/R/*.R`; `saveRDS()` to `scripts/R/output/` | cached code chunks inside the manuscript `.qmd` (`#\| cache: true`, `#\| dependson:`) |
| `paper/sections/*.tex` section files | prose sections written directly in the manuscript `.qmd` |
| `paper/main.tex` (the assembled paper) | `manuscript_<project>.qmd` (see Naming below) |
| LaTeX `\caption{}` on figures/tables (INV-12) | `#\| fig-cap:` / `#\| tbl-cap:` chunk options |
| Scripts export bare `tabular`, `main.tex` wraps the float (INV-13) | `modelsummary` / `kableExtra` emit the complete float from inside the chunk |
| `permissions.md` gates requiring/producing `paper/tables/*.tex`, `paper/main.tex`, `paper/sections/*.tex` | the gate is `quarto render` exits 0 with no NA/NaN inline expressions (see quarto-empirical "Write Gate") |
| Response letters as `paper/.../*.tex` | response letters as `.qmd` or `.md`, per project preference |

A reference to any legacy path above is satisfied by producing its quarto equivalent.
Do not create `scripts/R/`, `paper/sections/`, or `paper/main.tex` for a project that
follows quarto-empirical.

## Manuscript Naming Convention

The manuscript file is named **`manuscript_<project>.qmd`**, where `<project>` is the
**project directory basename**. Example: in a project directory named `zoning2026/`,
the manuscript is `manuscript_zoning2026.qmd`. This is the single source of truth for
the naming convention; `quarto-empirical.md`, `quarto-pdf.md`, `quarto-word.md`, and
`data-manifest.md` use `manuscript_<project>.qmd` as a placeholder for the same name.

Render artifacts (`manuscript_<project>_files/`, `manuscript_<project>_cache/`) already
match the `*_files/` and `*_cache/` gitignore globs — no gitignore change is needed.

## Scope

This rule governs **layout precedence and naming only**. It does not alter any
clo-author file (those remain pristine upstream submodule content) and does not change
the methodological guidance in the skills it references.
```

- [ ] **Step 2: Verify the translation map covers every conflicting file**

Run:
```bash
cd ~/Academic/research-claude
for term in "scripts/R" "paper/sections" "paper/main.tex" "tabular" "paper/tables"; do
  printf '%-18s in precedence map: ' "$term"
  grep -q "$term" rules/pipeline-precedence.md && echo "yes" || echo "MISSING"
done
grep -c "INV-12\|INV-13" rules/pipeline-precedence.md
```
Expected: every term prints `yes`; the INV count is `1` (both appear on one line) or greater.

- [ ] **Step 3: Verify no submodule files were touched**

Run:
```bash
cd ~/Academic/research-claude
git status --porcelain submodules/ | head
git submodule status
```
Expected: `git status --porcelain submodules/` prints nothing; `git submodule status` shows no `+`/`-` prefix on any line.

- [ ] **Step 4: Commit** *(only if the user has asked to commit — see Global Constraints)*

```bash
cd ~/Academic/research-claude
git add rules/pipeline-precedence.md
git commit -m "feat(rules): add pipeline-precedence (quarto-empirical overrides legacy layout)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Rename convention in `rules/quarto-empirical.md`

**Files:**
- Modify: `rules/quarto-empirical.md` (lines 17, 19, 30, 193, 207, 247, 256, 295 reference `manuscript.qmd`/`manuscript_files`)

**Interfaces:**
- Consumes: naming convention from `pipeline-precedence.md` (Task 1).
- Produces: the architecture/gate/critic references that downstream readers rely on, now using `manuscript_<project>.qmd`.

- [ ] **Step 1: Add a convention note after the intro**

In `rules/quarto-empirical.md`, after the line `The rendered PDF is the paper.` (the paragraph ending around line 7), insert a blank line and this note:

```markdown
> **File name:** the manuscript is `manuscript_<project>.qmd`, where `<project>` is the
> project directory basename (e.g. `manuscript_zoning2026.qmd` in the `zoning2026/`
> project). Examples below use `manuscript_<project>.qmd` as a placeholder. See
> `pipeline-precedence.md` for the canonical statement of this convention.
```

- [ ] **Step 2: Replace the layout-diagram references**

In the architecture code block, replace:
```
├── manuscript.qmd     ← single source of truth: code + prose
```
with:
```
├── manuscript_<project>.qmd  ← single source of truth: code + prose
```
and replace:
```
├── manuscript_files/  ← gitignored; render artifacts
```
with:
```
├── manuscript_<project>_files/  ← gitignored; render artifacts
```

- [ ] **Step 3: Replace the prose/gate/critic references**

Replace `manuscript.qmd` with `manuscript_<project>.qmd` on each of these lines (verbatim phrases to locate them):
- `live inside \`manuscript.qmd\` as cached code chunks.` → `live inside \`manuscript_<project>.qmd\` as cached code chunks.`
- `[ ] 2. quarto render manuscript.qmd exits 0` → `[ ] 2. quarto render manuscript_<project>.qmd exits 0`
- `available from the **same** \`manuscript.qmd\`` → `available from the **same** \`manuscript_<project>.qmd\``
- `what \`manuscript.qmd\` reads via \`cache.extra\`` → `what \`manuscript_<project>.qmd\` reads via \`cache.extra\``
- `the reviewed artifact is \`manuscript.qmd\`` → `the reviewed artifact is \`manuscript_<project>.qmd\``
- `formats of the single \`manuscript.qmd\`` → `formats of the single \`manuscript_<project>.qmd\``

- [ ] **Step 4: Verify no stale bare `manuscript.qmd` remains**

Run:
```bash
cd ~/Academic/research-claude
grep -n "manuscript\.qmd\|manuscript_files" rules/quarto-empirical.md
```
Expected: no output (every reference now reads `manuscript_<project>.qmd` / `manuscript_<project>_files`).

- [ ] **Step 5: Commit** *(only if the user has asked to commit)*

```bash
cd ~/Academic/research-claude
git add rules/quarto-empirical.md
git commit -m "docs(rules): manuscript_<project>.qmd convention in quarto-empirical

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Rename convention in `rules/quarto-pdf.md`

**Files:**
- Modify: `rules/quarto-pdf.md` (lines 3, 16, 110, 111)

**Interfaces:**
- Consumes: naming convention from `pipeline-precedence.md` (Task 1).
- Produces: PDF-format reference text using `manuscript_<project>.qmd`.

- [ ] **Step 1: Replace each reference**

Replace `manuscript.qmd` with `manuscript_<project>.qmd` on each line:
- `**PDF is the canonical output of the single \`manuscript.qmd\`.**` → `...single \`manuscript_<project>.qmd\`.**`
- `Add this under \`format:\` in \`manuscript.qmd\`.` → `...in \`manuscript_<project>.qmd\`.`
- `quarto render manuscript.qmd            # default format (PDF)` → `quarto render manuscript_<project>.qmd   # default format (PDF)`
- `quarto render manuscript.qmd --to pdf` → `quarto render manuscript_<project>.qmd --to pdf`

- [ ] **Step 2: Verify**

Run:
```bash
cd ~/Academic/research-claude
grep -n "manuscript\.qmd" rules/quarto-pdf.md
```
Expected: no output.

- [ ] **Step 3: Commit** *(only if the user has asked to commit)*

```bash
cd ~/Academic/research-claude
git add rules/quarto-pdf.md
git commit -m "docs(rules): manuscript_<project>.qmd convention in quarto-pdf

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Rename convention in `rules/quarto-word.md`

**Files:**
- Modify: `rules/quarto-word.md` (lines 3, 151)

**Interfaces:**
- Consumes: naming convention from `pipeline-precedence.md` (Task 1).
- Produces: Word-format reference text using `manuscript_<project>.qmd`.

- [ ] **Step 1: Replace each reference**

Replace `manuscript.qmd` with `manuscript_<project>.qmd` on each line:
- `**Word (DOCX) is the optional secondary output of the single \`manuscript.qmd\`**` → `...single \`manuscript_<project>.qmd\`**`
- `quarto render manuscript.qmd --to docx          # Word output from the same file` → `quarto render manuscript_<project>.qmd --to docx   # Word output from the same file`

- [ ] **Step 2: Verify**

Run:
```bash
cd ~/Academic/research-claude
grep -n "manuscript\.qmd" rules/quarto-word.md
```
Expected: no output.

- [ ] **Step 3: Commit** *(only if the user has asked to commit)*

```bash
cd ~/Academic/research-claude
git add rules/quarto-word.md
git commit -m "docs(rules): manuscript_<project>.qmd convention in quarto-word

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Rename convention in `rules/data-manifest.md`

**Files:**
- Modify: `rules/data-manifest.md` (line 72)

**Interfaces:**
- Consumes: naming convention from `pipeline-precedence.md` (Task 1).
- Produces: data-manifest reference text using `manuscript_<project>.qmd`.

- [ ] **Step 1: Replace the reference**

Replace:
- `1. Find the inline \`r\` expression or hardcoded value in \`manuscript.qmd\`` → `1. Find the inline \`r\` expression or hardcoded value in \`manuscript_<project>.qmd\``

- [ ] **Step 2: Verify**

Run:
```bash
cd ~/Academic/research-claude
grep -n "manuscript\.qmd" rules/data-manifest.md
```
Expected: no output.

- [ ] **Step 3: Commit** *(only if the user has asked to commit)*

```bash
cd ~/Academic/research-claude
git add rules/data-manifest.md
git commit -m "docs(rules): manuscript_<project>.qmd convention in data-manifest

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: List `pipeline-precedence.md` in `apply.sh`

**Files:**
- Modify: `apply.sh` (header comment block ~lines 24-30; `--list` rules block ~lines 95-101; install-step log line ~line 212)

**Interfaces:**
- Consumes: the file produced by Task 1.
- Produces: accurate install documentation. No behavior change — the file already installs via the existing `RC_RULES` copy loop (apply.sh step 6, `cp "$RC_RULES/"*.md`).

- [ ] **Step 1: Add to the header comment block**

In `apply.sh`, in the `# From research-claude (own rules/):` comment block, after the
`quarto-empirical.md` line, add:
```
#                      .claude/rules/pipeline-precedence.md      (quarto-empirical overrides legacy clo-author layout)
```

- [ ] **Step 2: Add to the `--list` output block**

In the `echo "From research-claude (own rules/):"` block, after the `quarto-empirical.md` echo line, add:
```bash
  echo "  .claude/rules/pipeline-precedence.md         — quarto-empirical overrides clo-author legacy layout + manuscript naming"
```

- [ ] **Step 3: Add to the install-step log line**

Replace the step-6 log line:
```bash
  echo "→ Installing research-claude rules (quarto-empirical, data-manifest, quarto-pdf, quarto-word, registry-verification-gate, literature-search-order)..."
```
with:
```bash
  echo "→ Installing research-claude rules (quarto-empirical, pipeline-precedence, data-manifest, quarto-pdf, quarto-word, registry-verification-gate, literature-search-order)..."
```

- [ ] **Step 4: Smoke-test apply.sh into a temp `zoning2026` project**

Run:
```bash
cd ~/Academic/research-claude
rm -rf /tmp/rc-test-plan && mkdir -p /tmp/rc-test-plan/zoning2026
./apply.sh --project-dir /tmp/rc-test-plan/zoning2026 >/dev/null 2>&1
ls /tmp/rc-test-plan/zoning2026/.claude/rules/pipeline-precedence.md
./apply.sh --list | grep pipeline-precedence
```
Expected: the `ls` prints the path (file installed); the `--list` grep prints the new line.

- [ ] **Step 5: Verify the installed precedence rule names the project correctly**

Run:
```bash
grep -c "manuscript_<project>.qmd" /tmp/rc-test-plan/zoning2026/.claude/rules/pipeline-precedence.md
```
Expected: a count ≥ 1 (the convention text installed verbatim; `<project>` is a literal placeholder, resolved by Claude at manuscript-creation time, not by apply.sh).

- [ ] **Step 6: Commit** *(only if the user has asked to commit)*

```bash
cd ~/Academic/research-claude
git add apply.sh
git commit -m "docs(apply): list pipeline-precedence.md in install summary

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Whole-repo consistency check

**Files:** none modified — verification only.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: confirmation the spec's verification criteria are met.

- [ ] **Step 1: No stale `manuscript.qmd` in research-claude's own rules**

Run:
```bash
cd ~/Academic/research-claude
grep -rn "manuscript\.qmd" rules/
```
Expected: no output. (Bare `manuscript.qmd` is allowed to remain only inside `submodules/`, which we do not touch.)

- [ ] **Step 2: Submodule still pristine**

Run:
```bash
cd ~/Academic/research-claude
git status --porcelain submodules/
git submodule status
```
Expected: first command prints nothing; `git submodule status` shows no `+`/`-` prefixes.

- [ ] **Step 3: Every conflicting file has a translation-map row**

Run:
```bash
cd ~/Academic/research-claude
for term in analyze write revise working-paper-format content-invariants permissions; do
  printf '%-22s referenced in precedence: ' "$term"
  grep -q "$term" rules/pipeline-precedence.md && echo yes || echo MISSING
done
```
Expected: every line prints `yes`.

- [ ] **Step 4: Done** — report results to the user. No commit (verification only).
```
