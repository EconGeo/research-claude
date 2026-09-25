# data-dict Trial — Evaluation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to work through this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This is an **evaluation**, not a build: it ends in a go / no-go ruling, and nothing in the shipped tree changes unless Task 5 rules "go".

**Goal:** Find out, on one real paper's raw data, whether `data-dict` (tidyverse) is good enough to replace the free-form codebook that `data-engineer` writes, and to add a checked "data matches its dictionary" step to the pipeline.

**Architecture:** Install the CLI on this machine only. Point it at a **scratch copy** of one project's `data/raw/`, draft a dictionary, tighten it by hand, then run the three validation levels and `translate --to R`. Record what worked, what broke and what it caught in a findings file. Rule on adoption only after that.

**Tech Stack:** the `data-dict` CLI (Rust, v0.0.3 "Early preview" per data-dict.tidyverse.org, fetched 2026-09-25), R (`readr`, `haven`, `arrow`) for format conversion, bash.

**Spec:** the 2026-09-25 session assessment (below), plus:
- `rules/data-manifest.md` (read in full, 2026-09-25): provenance, 8-column table, INV-24.
- `agents/data-engineer.md` (read in full, 2026-09-25): §3 "Data Documentation" and the "Saving" line put the codebook at `quality_reports/data-assessment/<project>/data_dictionary.md`, as free prose, unchecked.

### What is known and what is not (2026-09-25)

| Claim | Status |
|---|---|
| Repo is `tidyverse/data-dict`; spec in `hadley/data-dict.yaml` (`hadley/data-dict` is a 404) | per docs: fetched |
| Three validation levels: spec, meta (names/types), data (value constraints) | per docs: README |
| `draft` and `describe` read **Parquet** | per docs: README |
| Reads **CSV / `.dta` / `.xlsx` / `.rds`** | **unverified:** not mentioned in the README or on the docs landing page |
| `translate` emits R / Python / SQL assertions | per docs: README. Output quality **unverified** |
| Version v0.0.3, "Early preview" | per docs: landing page |
| Install: shell installer, `uv`, `pipx`, R | per docs: landing page |

## Global Constraints

- **Nothing in the shipped tree changes during Tasks 0–4.** No edits to `agents/`, `skills/`, `rules/`, `hooks/`, `templates/` or `seeds/`: they go live in all six papers on save (`CLAUDE.md`).
- **The paper repo is read-only.** All trial files live in `$TRIAL=/tmp/claude-data-dict-trial` (or the session scratchpad). Copy raw files out and never write into `~/Research/<project>/`.
- **The user installs the CLI.** The installer is a `curl … | sh` download-and-execute. Claude shows the command, and the user runs it or approves it.
- **R naming rule** (`~/.claude/CLAUDE.md`): any R conversion script uses descriptive dataset names such as `zoning_parcels_raw`, never `data` or `df`. Run the `grep -nE` check on any `.R` file written.
- **Label every claim** in the findings file as `tested:`, `per docs:` or `unverified:`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Only `docs/` changes in this plan, so `scripts/check_fork.sh` has nothing new to scan. Run it anyway before each commit, exit 0.

## Trial project

**Default: `~/Research/zoning2026`.** Its `data/raw/` has 37 csv, 3 dta, 11 xlsx, 5 xls and 1 rds (counted 2026-09-25): a realistic format mix, several tables, likely joins.
**Fallback: `~/Research/POGM4`** (54 csv, 17 xlsx, 1 dta).
Confirm the choice with the user before Task 1.

---

### Task 0: Install and establish the format surface

**Files:**
- Create: `docs/audits/2026-09-25_data-dict-trial-findings.md`

- [ ] **Step 1:** Show the user the install options from data-dict.tidyverse.org and ask which to use. The shell installer is `curl --proto '=https' --tlsv1.2 -LsSf https://github.com/tidyverse/data-dict/releases/latest/download/data-dict-cli-installer.sh | sh`. Prefer the `uv`/`pipx` route if the user has no preference, since it is easier to uninstall.
- [ ] **Step 2:** Record the exact version.
  Run: `data-dict --version`
- [ ] **Step 3:** Capture the full command surface to the findings file. Do **not** guess flags anywhere later in this plan: every later invocation uses syntax taken from this capture.
  Run: `data-dict --help; for c in draft describe validate-spec validate-meta validate-data render-spec render-report translate export-spec export-data; do echo "== $c"; data-dict $c --help; done`
- [ ] **Step 4: Settle the CSV question by test.** Make a 3-row CSV and try `draft` on it.
  ```bash
  mkdir -p "$TRIAL" && printf 'id,x\n1,a\n2,b\n3,c\n' > "$TRIAL/probe.csv"
  data-dict draft "$TRIAL/probe.csv"
  ```
  Record `tested: CSV supported` or `tested: CSV rejected — <error>`. Do the same for one `.dta` file copied from the trial project.
- [ ] **Step 5:** Commit the findings file (`docs(data-dict): trial Task 0 — install and format surface`).

**Stop rule:** if the CLI will not install, stop and report. If `translate --help` shows no R target, record it and carry on, but note that Task 4 is void.

### Task 1: Stage the data

**Files:**
- Create: `$TRIAL/raw/…` (copies), plus `$TRIAL/convert.R` if Task 0 found CSV/`.dta` unsupported

- [ ] **Step 1:** Read `~/Research/zoning2026/data/raw/data_manifest.md` **in full**. Pick 3–5 tables that the manuscript joins, based on the manifest's `Variables Used` column and the manuscript's read calls. Record the picks and why in the findings file.
- [ ] **Step 2:** Copy those files into `$TRIAL/raw/`. Never symlink them.
- [ ] **Step 3 (only if needed):** If Task 0 found the native formats unsupported, convert them to Parquet in `$TRIAL/convert.R`. Use `arrow::write_parquet()`, with one descriptive object name per table and `local({...})` around any loop. Run the naming-rule grep on the script.
  Record `tested:` which conversions the tool itself forced. That count is an adoption cost.

### Task 2: Draft and hand-tighten a dictionary

**Files:**
- Create: `$TRIAL/data-dict.yaml`

- [ ] **Step 1:** Run `draft` on each staged table and merge the drafts into one `data-dict.yaml`. Use the multi-table syntax from the Task 0 help capture and the spec README.
- [ ] **Step 2:** Tighten it by hand in the ways that matter for this paper:
  - primary keys;
  - at least one cross-table relationship (e.g. a FIPS or parcel ID);
  - range and allowed-value constraints on 3+ analysis variables;
  - a vocabulary entry for 2+ domain terms.
- [ ] **Step 3:** Run `validate-spec` until it is clean. Log every error message and whether it was **clear enough to fix without reading source**. Clarity of messages is a criterion in Task 5.
- [ ] **Step 4:** Record the time spent, from first draft to clean spec.

### Task 3: Validate against the data, including planted faults

- [ ] **Step 1:** Run `validate-meta` and `validate-data` on the real staged files. Log every failure, and for each one say whether it is a real data problem or a dictionary mistake.
- [ ] **Step 2: A gate that cannot go red is not one.** Make `$TRIAL/raw_faulty/`, a copy containing these planted faults:
  - (a) one duplicated primary key;
  - (b) one value outside a declared range;
  - (c) one orphan foreign key;
  - (d) one renamed column;
  - (e) one column with its type changed (numeric stored as text).

  Run both validations on it and record which of (a)–(e) are caught (`tested:`). Anything missed is a recorded blind spot.
- [ ] **Step 3:** Run `render-report` and open the HTML. Note whether it is readable enough to go into a replication package or a coauthor handoff.

### Task 4: `translate` to R — the only route to cleaned data

The pipeline never writes cleaned data to disk (`agents/data-engineer.md`: "nothing is saved to disk"; cached chunks only). So the CLI can check only `data/raw/`. The cleaned frames could be checked only by assertions run inside the manuscript.

- [ ] **Step 1:** Run `translate` to R on `$TRIAL/data-dict.yaml` and save the output to `$TRIAL/assertions.R`.
- [ ] **Step 2:** Read the output in full, then record:
  - which packages it depends on;
  - whether the assertions are plain functions that could sit in a Quarto chunk;
  - whether any generated top-level name breaks the R naming rule (run the grep).
- [ ] **Step 3:** Source it against the staged tables loaded in R, and again against `raw_faulty/`. Record which faults (a)–(e) the R assertions catch. Compare with Task 3.

### Task 5: Rule go / no-go and write it down

**Files:**
- Modify: `docs/audits/2026-09-25_data-dict-trial-findings.md` (ruling section)
- Modify: `docs/SESSION_REPORT.md` (entry)
- Modify: `CLAUDE.md` "Start here" (repoint the pointer only if a follow-up plan is opened)

- [ ] **Step 1:** Score each criterion from the findings. Each is pass / fail / partial, with the evidence line cited.

| # | Criterion | Go requires |
|---|---|---|
| C1 | Reads the project's native formats (csv, dta) without conversion | pass, or conversion is a one-line R step |
| C2 | Catches planted faults (a)–(e) | ≥ 4 of 5, including (a) and (c) |
| C3 | `translate --to R` produces chunk-usable assertions that respect the naming rule | pass |
| C4 | Spec error messages are fixable without reading the tool's source | pass |
| C5 | Hand-tightening effort for 3–5 tables | ≤ ~1 hour |
| C6 | Coauthor install cost | one command, no Rust toolchain |

- [ ] **Step 2: Ruling.**
  - **Go** (C1–C3 pass, the rest are no worse than partial): open a follow-up plan, `docs/plans/<date>-data-dict-adoption.md`, covering:
    - `data-engineer` §3 writes `data-dict.yaml` in place of `data_dictionary.md`;
    - a new optional content invariant, or a verifier step, that runs `validate-data` on `data/raw/` when `data-dict.yaml` exists;
    - translated assertions for the cleaned data;
    - `seeds/` and `apply.sh` changes, then `check_fork.sh` and `check_install.sh --all`.

    That plan is where shipped-tree changes happen, not this one.
  - **No-go:** record the failing criteria and the version tested, and name the upstream change that would flip the ruling so a later session can re-test cheaply. If a missed fault is a clear upstream bug, draft an issue for `tidyverse/data-dict` and show it to the user. Do not file it without the user's approval.
  - **Defer** (v0.0.x churn is the only blocker): record a re-test trigger, e.g. "re-run Tasks 0 and 3 at v0.1".
- [ ] **Step 3:** Append the `docs/SESSION_REPORT.md` entry, run `./scripts/check_fork.sh`, and commit (`docs(data-dict): trial findings and ruling`).
- [ ] **Step 4:** Delete `$TRIAL`. It holds copies of paper data and must not linger outside the paper repo.
