# Guarantee-Enforcement Audit — research-claude

**Date:** 2026-09-23
**Scope:** whether the pipeline's two core guarantees are *enforced* or merely *asserted*.
**Guarantee A** — exactly one Quarto document is the single source of ground truth.
**Guarantee B** — rendering and referencing are strictly native Quarto.
**Method:** every file named in the brief read to EOF; fixtures built in a scratchpad project
and every shipped executable run against them; POGM4's live manuscript used as the field case.
Every claim below is labelled `tested:` (a command was run in this session) or `per file:`
(read in full). Nothing in this audit modified a pipeline file.

**Verdict in one line.** Guarantee A is enforced by exactly one line of shell (`check_install.sh`
item 7, the `manuscript:` count) and by nothing else — no executable check looks for a second
analysis path. Guarantee B is enforced by **nothing at all**: the one script that would enforce
it, `quarto_structure_check.py`, is invoked as a *blocking* gate by `/tools commit` and **does
not exist on disk**.

---

## 1. Invariant coverage matrix (the deliverable)

Enforcement tiers:
- **EXEC** — a script or hook that exits non-zero, or whose findings are mechanical.
- **EXEC-ADV** — a script runs, but always `exit 0`; findings are advisory text only.
- **EXEC-REPO** — a script exists, but scans the *research-claude tree*, never a project manuscript.
- **CRITIC** — LLM judgment against a written rubric.
- **NONE** — no rubric line and no script.

`content-invariants.md` (read in full) asserts its own enforcement in the table at lines 108–114.
Column 3 below is what the brief calls for: what actually fires.

| INV | Property | `content-invariants.md` claims | What actually fires | Tier |
|---|---|---|---|---|
| **INV-1** | Table notes | `reviewer-judgment` (L114) | writer-critic rubric `-5 per, max -15` (`scoring-rubrics.md:27`) | CRITIC |
| **INV-2** | `#\| fig-cap:` on every figure | `reviewer-judgment` (L114) | writer-critic `scoring-rubrics.md:28`; coder-critic cat 11; `quarto-empirical.md:313` `-5`. **No script.** `quarto render` does not fail on a missing cap | CRITIC |
| **INV-3** | Booktabs only | `reviewer-judgment` | coder-critic cat 12 | CRITIC |
| **INV-4** | Stars per journal profile | `reviewer-judgment` | coder-critic cat 12 | CRITIC |
| **INV-5** | Abstract ≤ 150 words | `reviewer-judgment` | writer-critic. (POGM4 overrides to 200 — JRER/T&F) | CRITIC |
| **INV-6** | JEL + keywords | `reviewer-judgment` | `scoring-rubrics.md:36` `-5` | CRITIC |
| **INV-7** | Consistent notation | `reviewer-judgment` | `scoring-rubrics.md:158` `-5 per symbol` | CRITIC |
| **INV-8** | Causal claim ⇒ identification section | `reviewer-judgment` | `scoring-rubrics.md:20` `-20` | CRITIC |
| **INV-9** | pandoc `@key`; no `\citet{}`; PDF has no top-level `csl:` | "`quarto render` fails or degrades visibly; writer-critic cat 5; verifier 4c" (L112) | **The render claim is false.** `check_refs.py` has the `\\cite[tp]?\{` regex but scans only the repo tree | EXEC-REPO + CRITIC |
| **INV-10** | `hyperref` then `cleveref` in preamble | `reviewer-judgment` | writer-critic | CRITIC |
| **INV-11** | **Every prose number is an inline `` `r ` ``** | `prose_number_check.py`, exit 0 required; verifier 4b (L110) | **`prose_number_check.py`** — the one genuinely wired gate. Called by `pipeline.py` `prose-check` predicate (L258–262), `/tools commit` step 0, verifier 4b | **EXEC** |
| **INV-12** | No titles inside ggplot/matplotlib | `reviewer-judgment` | coder-critic cat 11 | CRITIC |
| **INV-13** | Exhibits are `tbl-`/`fig-` labelled chunks; no `paper/tables/` | "`quarto render` fails or degrades visibly; writer-critic cat 5" (L112) | `pipeline.py` `chunk` predicate — **existence only (`min: 1`), and broken** (§3). `check_refs.py` `manuscript-model` (`ggsave(`, `saveRDS(`, `dir.create("paper`) is repo-tree only | EXEC (broken) + EXEC-REPO + CRITIC |
| **INV-14** | `set.seed()` once, in the `cache: false` setup chunk | lint hook + coder-critic + verifier 4c (L110) | `lint-scripts.sh` warns when stochastic calls appear with no `set.seed()` (**tested: fires**) and when it sits past line 30. It cannot see "exactly once" or "in the setup chunk" | EXEC-ADV (partial) |
| **INV-15** | All packages loaded in the setup chunk | lint hook + coder-critic + verifier 4c (L110) | `lint-scripts.sh` only flags `library()` past line 30 — on a 4,299-line manuscript this is noise, not the invariant | NONE (effectively) |
| **INV-16** | No absolute paths | lint hook + coder-critic + verifier 4c (L110) | `lint-scripts.sh` HIGH (**tested: fires on `.qmd` chunks via `qmd_chunks.py`**) | EXEC-ADV |
| **INV-17** | No growing vectors in loops | `reviewer-judgment` (L114) | `scoring-rubrics.md:78` `-5` | CRITIC |
| **INV-18** | Chunks write nothing outside `_cache/`/`_files/` | `coder-critic` cat 13 (L113) | `check_refs.py` `manuscript-model` — repo tree only | EXEC-REPO + CRITIC |
| **INV-19a** | `setwd()`/`rm(list=ls())`/`install.packages()`/`attach()` | lint hook + coder-critic + verifier 4c (L110) | `lint-scripts.sh` (**tested: all four fire**) | EXEC-ADV |
| **INV-19b** | **No `source()` inside any chunk** | same row (L110) — the row even spells out "chunk-level: … `source()`" | **NOTHING.** Zero occurrences of `source(` in `hooks/` or `scripts/` | **NONE** |
| **INV-20** | Talk notation matches paper | `reviewer-judgment` | storyteller-critic | CRITIC |
| **INV-21** | Every slide claim traceable | `reviewer-judgment` | storyteller-critic | CRITIC |
| **INV-22** | *RETIRED 2026-09-08* | — | `check_refs.py` `deleted-things` flags live citations (repo tree only) | EXEC-REPO |
| **INV-23** | No derived file in `data/raw/` | `coder-critic`; verifier 4c (L111) | `check_fork.sh:78` only asserts the *string* `INV-23` appears in `agents/coder-critic.md` | CRITIC |
| **INV-24** | Every read file has a `data_manifest.md` row | `coder-critic`; verifier 4c; check 7 (L111) | **NOTHING.** `grep -rn data_manifest scripts/ hooks/` returns zero hits | **NONE** |
| *INV-25* | *cited by `skills/tools/SKILL.md:35`* | — | **Not defined in `content-invariants.md`.** `check_refs.py inv-refs` already FAILS on it | — |

**Totals.** Of 24 live invariants, **one (INV-11) has a real executable gate**. Four more
(INV-14/16/19a, and INV-13 partially) have advisory or partial coverage. **Fifteen are critic
judgment only, and three (INV-15, INV-19b, INV-24) are enforced by nothing at all** despite the
table at L110–111 naming enforcers for all three.

---

## 2. Guarantee A — single source of truth: what enforces it?

### 2.1 The one real check

`per file:` `scripts/check_install.sh` item 7 (read in full):

> `local decl; decl="$(grep -cE '^manuscript:\s*\S+\.qmd\s*$' "$P/CLAUDE.md" 2>/dev/null || true)"`
> … `else bad manuscript-declared "CLAUDE.md declares $decl manuscripts; exactly one is required"; fi`

and `scripts/pipeline.py:52-53`:

> `if len(hits) != 1:`
> `    sys.exit(f"pipeline.py: CLAUDE.md must declare exactly one 'manuscript: <file>.qmd' line (found {len(hits)})")`

`tested:` a second `manuscript:` line added to the fixture's `CLAUDE.md` →
`pipeline.py manuscript` exits 1 with that message. **This half works.**

Note the asymmetry in `check_install.sh` item 7: the `find -maxdepth 2 -name '*.qmd'` sweep runs
**only in the `decl -eq 0` branch**, to decide FAIL vs WARN. Once one manuscript is declared, no
search for other `.qmd` files happens at all.

### 2.2 Everything else: nothing

`tested:` a fixture project was built at
`/private/tmp/claude-504/…/scratchpad/fixture` containing, simultaneously:
a second `appendix_analysis.qmd` with an estimation chunk and a `saveRDS()`; a root-level
`run_analysis.R` that reads `data/raw/`, estimates and writes `main_model.rds`; a copy of it in
`explorations/`; and two `source()` calls inside the declared manuscript's setup chunk.

Every shipped project-side executable was then run and its combined output grepped:

```
appendix_analysis    mentioned in any checker output: 0
run_analysis         mentioned in any checker output: 0
source(              mentioned in any checker output: 0
```

The executables run: `pipeline.py` (`manuscript`, `fresh`, `next`, `post coder`, `post writer`,
`post data-engineer`), `prose_number_check.py`, and `lint-scripts.sh` on both the manuscript and
the whole project tree. The dir-sweep lint *scanned* `run_analysis.R` and
`explorations/side_analysis.R` and had nothing to say about them — it lints their contents, and
has no concept of a file that should not exist.

`tested:` the same on the live project. `check_install.sh --project-dir ~/Research/POGM4` prints
**`✓ check_install: PASS`** on a repo that carries 15 analysis scripts in
`archive/scripts_R_reference/`, 8 more in `quality_reports/phase2_scripts_2026-09-08/`, an
`explorations/verify_rent_cagr.R`, and two further `.qmd` files under
`_archived-template-20260613/`.

### 2.3 INV-19 (`source()` prohibited) — checked by nothing executable

`tested:` a chunk was written containing seven prohibited constructs —
`sample()` with no `set.seed()`, `sapply()`, `setwd()`, `rm(list = ls())`, `source("helper.R")`,
`install.packages()`, `attach()`. `lint-scripts.sh` reported **six of the seven**:

```
  [HIGH] Line 7: setwd() — use here() instead
  [MEDIUM] Line 8: rm(list = ls()) — restart R instead
  [HIGH] Line 10: install.packages() in script — use renv
  [MEDIUM] Line 6: sapply() — use vapply() or lapply()
  [MEDIUM] Line 11: attach()/detach() — use explicit references
  [HIGH] Stochastic code detected but no set.seed() — add set.seed() at top
```

`source("helper.R")` on line 9 is the one it missed. `tested:` `grep -c "source(" hooks/lint-scripts.sh`
→ **0**; `grep -rn "source(" hooks/ scripts/` → **no matches**. `lint-scripts.sh` also ends
`exit 0` unconditionally ("Exit code: always 0 (advisory)", line 6 of its header).

So INV-19b is CRITIC-only, against `quarto-empirical.md:306` ("`source()` call inside any chunk |
−10") and `agents/verifier.md:23` (check 4c) and `:31` (check 5). `content-invariants.md:110`
names the lint hook as an enforcer of INV-19 including, parenthetically, `source()`. **That
attribution is wrong.**

---

## 3. Guarantee B — native Quarto: what enforces it?

**Nothing.** Itemising the brief's list:

| Property | Executable check | Evidence |
|---|---|---|
| Chunk-label prefix `tbl-`/`fig-` correctness | **None** | §3.1 |
| Typed exhibit reference where `@ref` belongs | **None** (incidental + defeatable) | §3.2 |
| Unresolved `?@` / dangling `@tbl-` | **None** | §3.3 |
| Caption set in R instead of `#\| tbl-cap:` | **None** | fixture `set_caption(ft, "Exhibit 1. …")` — 0 mentions in any checker output |
| `knitr::opts_knit$set(quarto.version = 0)` | **None** | fixture carries it verbatim — 0 mentions |

### 3.1 `chunk_labels()` is blind to brace-form labels — confirmed

`per file:` `scripts/pipeline.py:146-147`:

> `def chunk_labels(ms: Path) -> List[str]:`
> `    return re.findall(r"^#\|\s*label:\s*([A-Za-z0-9_-]+)", ms.read_text(), re.M)`

`tested:` against `~/Research/POGM4/manuscript_quarto_word.qmd`:

```
chunk_labels() returns: ['setup']
count: 1
total ```{r fences: 80
fences with a name inside braces e.g. {r foo}: 79
#| label: lines: 1
tbl- labels (any form): 34
```

The brief's hypothesis is confirmed exactly: **one label found in an 80-chunk manuscript**,
because 79 chunks carry their label in the brace header rather than a `#| label:` line.

Downstream, `tested:` `pipeline.py post coder` in POGM4:

```
MISSING chunks tbl-* (0 found, need 1)
MISSING chunks fig-* (0 found, need 1)
ok      render exit 0
ok      prose_number_check.py exit 0
```

Two observations. First, this fails *closed* — but for the wrong reason, and on a manuscript that
genuinely has 34 `tbl-` labels. A gate that cries wolf on a compliant document is how a real
finding gets waived. Second, and more important: the `chunk` predicate is only ever used with
`min: 1` (`rules/registry.yaml` lines 272, 275, 293, 316 — four sites, all `min: 1`). It asks
"does at least one `tbl-*` chunk exist". **It can never check that the other 79 chunks are
correctly prefixed**, which is the actual content of INV-13.

### 3.2 Typed exhibit references — caught only by accident, and defeated in practice

`tested:` the fixture prose "As shown in Exhibit 1 … Table 2 reports … Figure 3 shows …"
produced three hits from `prose_number_check.py` — but only because `1`, `2`, `3` are *digits*.
The checker has no concept of a cross-reference. `tested:` adding those three digits to
`quality_reports/prose_number_allowlist.csv` with a reason flips the run to
`Prose number check PASSED`. The catch is incidental and one CSV row wide.

`tested:` on the live manuscript, prose-only counts (using the checker's own `load_prose()`):

```
\bTable\s+\d+        prose-only count = 49
@tbl-                prose-only count = 0
@fig-                prose-only count = 20
```

and `prose_number_check.py manuscript_quarto_word.qmd` →
`Prose number check PASSED: 92 distinct literals, all allowlisted with a reason`.

**The single genuinely-wired gate in the pipeline exits 0 on a manuscript with 49 typed table
references in prose and zero native `@tbl-` cross-references.**

### 3.3 `quarto render` does not enforce what `content-invariants.md` says it enforces

`content-invariants.md:112` assigns INV-9 and INV-13 to:

> `| INV-9, INV-13 | ` + "`quarto render` fails or degrades visibly; writer-critic category 5; verifier check 4c for INV-9 |"

`tested:` (Quarto 1.9.37, `format: docx`)

1. A document whose prose is `See @tbl-nonexistent and @fig-alsomissing for details.` renders
   with `WARNING … Unable to resolve crossref @tbl-nonexistent`, produces `t.docx`, and
   **exits 0**.
2. A document whose prose is `As shown by \citet{smith2024} and \citep{jones2020} … See Table
   \ref{tab:main}.` renders with **no warning at all** and **exits 0**.

`per file:` `scripts/pipeline.py:177-179` — the `render` predicate's implementation:

> `p = subprocess.run(["quarto", "render", …], cwd=root, capture_output=True, text=True)`
> `return p.returncode == 0, …`

It tests `returncode` only. The warning text is captured and discarded (only the last line is
kept, for the failure message). So:

- The `render` predicate **passes** a manuscript with unresolved `@tbl-` references.
- The `render` predicate **passes** a manuscript written entirely in `\citet{}`/`\ref{}`.
- `agents/verifier.md` check 1 says "No `ERROR`/`WARNING` in the log" and check 3 says no `?@` in
  the output — but the verifier is an LLM agent reading output, not a script. It is CRITIC tier.

**The render is not a cross-reference gate, and treating it as one is the same category of
mistake the write gate's own commentary warns about for literals** (`quarto-empirical.md`: "a
literal is not an expression and there is nothing for the render to fail on"). A typed "Table 4"
is not an expression either.

### 3.4 The gate that would enforce Guarantee B is invoked but does not exist

`per file:` `skills/tools/SKILL.md:31-42` — the `/tools commit` Step 0 gate:

> **If the declared manuscript is among the changed files, also run the single-source-of-truth
> gates. These are blocking, not advisory:**
> ```
> python3 .claude/scripts/prose_number_check.py <manuscript>       # INV-11
> python3 .claude/scripts/quarto_structure_check.py <manuscript>   # INV-13/INV-25
> ```
> - `quarto_structure_check.py` non-zero = the document is not native Quarto — a table or
>   figure chunk is mislabelled, an exhibit is referenced by typed number instead of `@ref`,
>   a caption is set in R instead of `#| tbl-cap:`, or a cross-reference does not resolve.

That description is a precise statement of Guarantee B. `tested:`

```
$ find ~/Academic/research-claude ~/Research -name "quarto_structure_check.py"
(no output)
$ grep -rn "INV-25" ~/Academic/research-claude/rules/
(no output)
```

**`quarto_structure_check.py` does not exist anywhere on disk, and INV-25 is not defined.** Both
were introduced by commit `15fabeb feat(tools,check): promote the blocking commit gates; fail on
project-local tooling`. `scripts/SHIPPED` lists four scripts — `prose_number_check.py`,
`pipeline.py`, `registry_lib.py`, `qmd_chunks.py` — so it would not reach a project even if it
existed.

The repo's own gate already knows. `tested:` `./scripts/check_fork.sh` currently **FAILS**:

```
FAIL [path-resolves]
    skills/tools/SKILL.md:27: scripts/quality_score.py (UNPREFIXED)
    skills/tools/SKILL.md:35: .claude/scripts/quarto_structure_check.py (UNRESOLVED)
FAIL [inv-refs]
    skills/tools/SKILL.md:35: INV-25 is not defined
FAIL [project-identity]
    scripts/check_install.sh:225:  # Why it is not a style rule. POGM4 carried a project-local skill,
```

(`scripts/quality_score.py` likewise exists only as `~/Research/POGM4/scripts/quality_score.py` —
a project-local file, not a pipeline one. The `/tools commit` Step 0 first command is
unresolvable in any other project.)

`CLAUDE.md:95` requires `./scripts/check_fork.sh` to exit 0 before any commit touching the shipped
tree. It was not run before `15fabeb`. **This is the single highest-value finding in the audit:
the gate is not weak, it is absent, and the repo's own hygiene check would have said so.**

---

## 4. What `check_paths.py` and `check_refs.py` actually do

Both were read in full. **Neither ever reads a manuscript.** They are repo-hygiene gates for the
research-claude checkout, invoked only by `scripts/check_fork.sh` (lines 93–99), and neither is
in `scripts/SHIPPED`, so neither is linked into a project's `.claude/scripts/` (`tested:`
POGM4's `.claude/scripts/` contains only `pipeline.py`, `prose_number_check.py`, `qmd_chunks.py`,
`registry_lib.py`, and a project-local `statusline.sh`).

**`check_paths.py`** — `per file:` its docstring states the scope outright:

> "A gate operates on the REPO ROOT, not on an installed project, so its bare
> `rules/registry.yaml` is the correct path and prefixing it with `.claude/` would break the gate."

It walks `agents skills rules references hooks templates seeds scripts`, tokenises every
pipeline-path-shaped string, and reports each as `ok` / `UNRESOLVED` (a `.claude/`-prefixed path
naming no file) / `UNPREFIXED` (a bare pipeline path outside the exempt set). That is its entire
coverage: **broken internal documentation links in the pipeline's own prose.** It says nothing
about R code, chunks, captions, cross-references, or manuscripts.

**`check_refs.py`** — `per file:` "Each criterion scans the shipped tree and prints PASS/FAIL/WARN
rows." Eight criteria:

| Criterion | What it catches |
|---|---|
| `latex-residue` | `paper/tables`, `main.tex`, `scripts/R/`, `\citet{`, `\ref{`, `\cref`, `latexmk`, `.Rmd`, `bookdown`, `\pause` — **in pipeline docs, not in manuscripts** |
| `manuscript-model` | `ggsave(`, `saveRDS(`, `writeLines(…​.tex)`, `dir.create("paper` — again, in pipeline docs |
| `deleted-things` | deleted agent names, deleted scripts, absent skills, INV-22 cited as live |
| `inv-refs` | an `INV-N` that `content-invariants.md` does not define, or a retired one cited as live |
| `skill-refs` | a `/token` naming no skill |
| `tool-name` | `Task` in an agent's `tools:` line (should be `Agent`) |
| `hooks-readme` | `hooks/README.md` rows matching real hook files and their declared events |
| `artifact-paths` | a `quality_reports/…` path matching no registry glob |

`tested:` pointed at a project, `check_refs.py --root ~/Research/POGM4` **crashes**:
`FileNotFoundError: '/Users/andrew.mueller/Research/POGM4/rules/registry.yaml'` (via
`crit_artifact_paths` → `registry_lib.load_registry`). `check_paths.py --root ~/Research/POGM4`
does not crash but produces 20 meaningless rows by scanning POGM4's *own* `templates/` directory.
Both are correct behaviour for tools that were never meant to leave the repo — the point is that
neither is, or can be, a manuscript gate.

**The irony worth recording:** `check_refs.py`'s `LATEX_RESIDUE` regex contains
`\\cite[tp]?\{|\\input\{|\\label\{|\\ref\{|\\cref` — precisely the non-native-Quarto referencing
Guarantee B forbids. That regex is pointed at the pipeline's documentation and has never been
pointed at a manuscript.

---

## 5. The two `prose_number_check.py` copies

`tested:` `diff -u ~/Research/scripts/prose_number_check.py ~/Academic/research-claude/scripts/prose_number_check.py`.

**`~/Academic/research-claude/scripts/prose_number_check.py` (255 lines) is the superset** in
every functional respect but one. What the 152-line `~/Research/scripts/` copy is missing:

1. **`project_root()` allowlist resolution.** The short copy resolves the allowlist beside the
   *manuscript*: `os.path.join(os.path.dirname(os.path.abspath(qmd)), "quality_reports", …)`.
   The long copy walks up to the nearest ancestor carrying a `.claude/`. Its docstring records the
   real failure: a project keeping its manuscript in `paper/` had all 41 literals reported as
   unexplained because the scanner looked in `paper/quality_reports/`.
2. **Round tens in `_CARD`.** The short copy stops at `twenty`; the long copy adds
   `thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred`. "Fifty MSAs" is invisible to the short copy.
3. **Per-project noun declaration.** The long copy reads `prose-number-nouns:` from the project's
   `CLAUDE.md` (`extra_nouns()`), with `PROSE_NUMBER_NOUNS` as a one-off override. The short copy
   supports the environment variable only — and its docstring's own reasoning applies against it:
   "an environment variable is not per-project, it is per-invocation, and a gate whose answer
   depends on who ran it is not a gate."
4. **Named-allowlist typo detection.** The long copy returns exit 2 when an explicitly named
   allowlist path does not exist; the short copy silently proceeds with an empty allowlist.
5. **The missing-allowlist NOTE.** The long copy distinguishes "the allowlist was consulted and
   came up short" from "there is no allowlist"; the short copy reports both identically.
6. **Reports the allowlist path on PASS.**

**The one behavioural narrowing in the long copy** (so "superset" is not quite exact): its word
scanner uses the lookbehind `(?<![-\w])` where the short copy uses `\b`, suppressing cardinals
inside hyphenated compounds ("leave-one-state-out"). This is a deliberate false-positive fix, but
it is strictly *fewer* hits, not more.

Cosmetic divergence: the short copy's docstring lists `markets` among the scanned nouns; its
`_NOUN` does not contain it. The docstring is wrong in the fail-open direction.

### Which callers use which

| Caller | Copy invoked |
|---|---|
| `pipeline.py` `prose-check` predicate (L258-262) | `.claude/scripts/prose_number_check.py` → **255-line** (symlink) |
| `agents/verifier.md` check 4b | `.claude/scripts/…` → **255-line** |
| `skills/tools/SKILL.md` `/tools commit` Step 0 | `.claude/scripts/…` → **255-line** |
| `rules/quarto-empirical.md` write gate item 3 | `.claude/scripts/…` → **255-line** |
| **`~/Research/POGM4/CLAUDE.md`** (two places) | **`python3 ~/Research/scripts/prose_number_check.py`** → **152-line** |
| `~/Research/CLAUDE.md` / other legacy projects | 152-line |

`tested:` `~/Research/POGM4/.claude/scripts/prose_number_check.py` is a symlink to the 255-line
copy — so **POGM4 has both on hand and its own `CLAUDE.md` names the weaker one.** A hand-run of
the documented command and an automated `pipeline.py post` run can disagree, and the documented
one is the one that misses round-ten counts and per-project nouns. POGM4's `CLAUDE.md` also calls
`~/Research/scripts/prose_number_check.py` "the **research-wide** checker … the reference
implementation is NAR_settlement's `quality_reports/w_prose_number_check.py`" — a third lineage.

---

## 6. Summary of defects, ranked

1. **`quarto_structure_check.py` is invoked as a blocking gate and does not exist**
   (`skills/tools/SKILL.md:35`). Guarantee B has no enforcement whatsoever. `check_fork.sh`
   already FAILS on this and on the undefined `INV-25` beside it; it was not run before `15fabeb`.
2. **`pipeline.py chunk_labels()` reads only `#| label:`** and returns `['setup']` for an 80-chunk
   manuscript. Every `chunk` predicate downstream is therefore either vacuous or a false alarm,
   and none of them checks prefix correctness anyway (`min: 1`, four sites).
3. **`quarto render` exit 0 is treated as a cross-reference gate and is not one.** Tested: exits 0
   with unresolved `@tbl-`/`@fig-` (warning only) and with `\citet{}`/`\citep{}`/`\ref{}` (silent).
   `content-invariants.md:112` should stop claiming it.
4. **No executable looks for a second analysis path.** A second `.qmd`, a root-level analysis `.R`,
   and an `explorations/` script feeding the manuscript are all invisible; `check_install.sh`
   PASSES POGM4 with 24 such files present.
5. **INV-19b (`source()`), INV-24 (manifest), INV-15 (packages in setup) have no executable check**
   while `content-invariants.md:110-111` names enforcers for all three. INV-19's row even spells
   out `source()` as something the lint hook catches; it does not.
6. **`prose_number_check.py`'s incidental catch of typed exhibit numbers is one allowlist row
   wide**, and in POGM4 that row already exists — the gate exits 0 on 49 typed table references.
7. **Two divergent `prose_number_check.py` copies**, with the live project's `CLAUDE.md` pointing
   at the weaker one while its own `.claude/scripts/` symlinks the stronger.

## 7. What is genuinely enforced (the short list)

- Exactly one `manuscript:` declaration — `pipeline.py:52-53`, `check_install.sh` item 7. **Real.**
- No unexplained numeric literal in prose — `prose_number_check.py`. **Real**, and the only
  guarantee in this audit with a working mechanical gate.
- Absolute paths, `setwd()`, `rm(list=ls())`, `install.packages()`, `attach()`, missing
  `set.seed()` — `lint-scripts.sh`. **Real but advisory** (`exit 0` always).
- No project-local skills/agents/rules/commands — `check_install.sh` check 5b. **Real**, and it is
  the check that would have caught the waiver-granting local skill.
- Pipeline-internal documentation integrity — `check_fork.sh` / `check_paths.py` / `check_refs.py`.
  **Real for the repo, and currently failing.**
