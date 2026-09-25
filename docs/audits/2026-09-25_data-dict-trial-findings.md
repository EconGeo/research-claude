# data-dict Trial — Findings

Plan: `docs/plans/2026-09-25-data-dict-trial.md`. Trial project: `~/Research/zoning2026` (read-only; copies only).

## Task 0 — install and format surface (2026-09-25)

**Install.** Route: R package (user choice). No `uv`/`pipx`/`cargo` on this machine.
- `pak::pak("tidyverse/data-dict/r")` installed `datadict` 0.1.0 from GitHub `0161d46` (MIT). Its imports are `cli`, `processx`, `tools` and `utils`: no compiler, no Rust toolchain.
- `datadict::dd_install()` downloaded a 3.9 MB prebuilt `aarch64-apple-darwin` binary, verified with a `.sha256`, into `~/Library/Caches/org.R-project.R/R/datadict/data-dict`. The binary is not put on `PATH`.
- `tested:` `data-dict --version` → `data-dict 0.0.3`.

**Command surface** (`tested:`, from `--help` on the installed 0.0.3 binary):
- The commands are `describe`, `draft`, `validate-spec`, `validate-meta`, `validate-data`, `export-spec`, `export-data`, `render`, `translate`, `spec`, `skill-read` and `skill-create`.
- The `render-spec` and `render-report` commands named in the GitHub README **do not exist** in 0.0.3; there is only `render`.
- The validators take `--table`, `--json` and `--html <FILE>`. `validate-data --html` is the "report" route.
- `translate` writes JSON to stdout: one record per expression, holding the columns it reads and one bare predicate per target. It takes `--target family(dialect)`, which can be repeated.
- `skill-read` and `skill-create` ship agent skills from the CLI itself. They are relevant to a `data-engineer` integration and haven't been inspected yet.

**Format surface:**
- `tested:` `draft probe.csv` → `Parquet error: Invalid Parquet file. Corrupt footer`. **CSV is rejected.**
- `per docs:` `data-dict spec` (spec v0.1.0, read in full, 489 lines) §Source says: "Parquet is the only source `data-dict` can currently validate against". SQL, R and Python sources are listed as future work. So `.dta`, `.xlsx`, `.xls`, `.rds` and `.csv` all need converting to Parquet before `validate-meta` or `validate-data` can run. A separate `.dta` probe was unnecessary once the spec said this.

**R wrapper is out of sync with the released binary** (`tested:`):
- `datadict::dd_validate_data()` calls `data-dict render-report …`.
- The 0.0.3 binary answers `unrecognized subcommand 'render-report'` (exit 2).
- So the GitHub HEAD of the R package targets an unreleased CLI, and the R wrapper's one validation function is broken against the only binary `dd_install()` fetches. Checked 2026-09-25.

**The spec makes two points that change the plan** (`per docs:`, spec §Representative values and §Column constraints):
- `range` is **descriptive, not validated**: "nothing is validated against it, and a value outside it is not an error". A bound is enforced only by an `assert:` expression. Task 2's "range constraints" must therefore be written as `assert`, and planted fault (b) tests an `assert`.
- `enum` `values` **are** a membership constraint.
- `foreign_key` plus a `relationships` entry is checked for orphans (D05/D06). Fault (c) is in scope.

**Bearing on the criteria so far:**
- **C1 fails as worded.** No native format is read. Conversion is a small `arrow::write_parquet()` step per table, which the plan's "go" wording allows.
- **C6 is partial.** Installing is one R call with no toolchain, but the R wrapper's validator is broken against the released binary, so coauthors would call the binary directly (`datadict::dd_path()`).

## Task 1 — staging (2026-09-25)

`~/Research/zoning2026/data/raw/data_manifest.md` was read in full (116 lines). The picks cover CSV, a 14-file yearly series and a `.dta`, and each carries a known quirk worth testing:

| Table | Source file(s) | Why |
|---|---|---|
| `bps_county` | `bps/bps_county_2012…2025.csv` (14 files) | Composite key `(year, fips5)`. The manifest records **10 benign duplicate rows (AK/MD, 2014–2015)** that the manuscript tolerates. |
| `treatment` | `furman/treatment_by_state_year.csv` | Hand-coded rules between columns: compliance is the base convention, and treatment never switches on before `first_treat_year`. |
| `cbsa_state` | `controls/cbsa_state_crosswalk.csv` | Hand-verified key table. |
| `contiguity` | `geo/state_contiguity_queen.csv` | A foreign key into state codes. |
| `saiz` | `saiz/HOUSING_SUPPLY.dta` | Stata input. |

`tested:` conversion (`convert.R`, about 40 lines) needed:
- `nanoparquet` 0.5.2. `arrow` isn't installed; `nanoparquet` is on CRAN and has no dependencies.
- FIPS/CBSA columns forced to character so their leading zeros survive.
- `haven::zap_labels()` on the `.dta` file.
- An extra step to stack the 14 BPS years into one file (see Task 3).

The naming-rule grep came back clean on all three R scripts.

## Task 2 — draft and tighten (2026-09-25)

`tested:`
- `draft` on five Parquet files took 0.02 s and wrote 683 lines. It inferred types correctly and kept zero-padded FIPS as strings. It suggested `primary_key` where values were distinct, spotted enums ("only 4 distinct values"), and left a `todo` on every item. The draft passes `validate-spec` with only S31 `todo` warnings, as its help text says.
- Hand-tightening took about 15 minutes for the five tables:
  - composite primary keys;
  - 17 `assert:` expressions, including four cross-column rules on `treatment` and the `units_total` sum identity on BPS;
  - two enums;
  - one foreign key plus a relationship;
  - a three-term glossary;
  - uninteresting columns listed by name only.
- There was one `validate-spec` error: Q-1-12, caused by my YAML (an unquoted `IN (0, 1)` inside a `{…}` flow map). The message quoted the mis-parsed map, so the fix was obvious without reading source.

## Task 3 — validation, real and planted (2026-09-25)

**Globs are broken** (`tested:`):
- `source: parquet: pq/bps/*.parquet` fails with M05 `Cannot open file`, even though spec §Source says the path "may include globs".
- The M05 also **stopped validation of the other four tables**.
- Workaround: stack the years into `pq/bps_county.parquet`.

**Real data** (`tested:`):
- `validate-meta` exits 0.
- `validate-data` exits 1 with **exactly one error: D02 on `bps_county (year, fips5)`, 10 repeated occurrences**, e.g. `(2014.0, 02020)`, rows 6125…. These are the manifest's 10 benign AK/MD duplicates, found with no hint.
- All 17 assertions hold, including the sum identity across 14 years.
- One limitation: the spec has no way to write "≤ 10 duplicates allowed", so this known-benign case stays a permanent red unless the key is dropped.

**Planted faults** (`tested:`, `plant_faults.R` on a copy):

| Fault | Planted | Caught | Code | Detail |
|---|---|---|---|---|
| (a) duplicated key | `cbsa_state` row 1 repeated | ✅ | D02 | `10140; row: 495` |
| (b) breaks an `assert:` bound | `saiz.unaval[1] = 1.5` | ✅ | D07 | `row: 1 (unaval=1.5)` |
| (c) orphan foreign key | `contiguity` + `("ZZ","CA")` | ✅ | D05 | `ZZ; row: 219` |
| (d) renamed column | `reform_type → reform_kind` | ✅ | M02 + M03 | missing, plus an undocumented-column warning |
| (e) numeric stored as text | `saiz.elasticity` as character | ✅ | M01 + D08 | type mismatch; the assertion is reported "not evaluable" rather than silently passed |
| (f) cross-column rule | `treated = 1` in 2012, first year 2025 | ✅ | D07 | `row: 29 (treated=1, year=2012, first_treat_year=2025)` |

**Blind spot** (`tested:`): relationship `cardinality` isn't checked. The dictionary declares `contiguity.state = treatment.state_abbr` as `many-to-one`, even though `treatment.state_abbr` repeats across 14 years. Neither `validate-spec` nor `validate-data` objected. Only orphans (D05) are checked.

**HTML report** (`tested:`, viewed in the browser):
- `validate-data --html` writes a 140 KB self-contained page with no external requests.
- It opens with a summary ("8 errors, 1 warning · 100 of 110 checks passed"), then lists problems per table with the YAML line, the offending rows and a full checks table.
- It would drop into a replication package or a coauthor handoff as is.
- One cosmetic flaw: an integer-valued `year` stored as double prints as `2014.0`.

## Task 4 — `translate` to R (2026-09-25)

`tested:`
- `translate --pretty` emits 17 records, one per `assert:`. Each has R(base), R(tidyverse), R(data.table) and SQL(duckdb) predicates, with notes on how NaN is handled.
- The R(base) predicates are plain vectorised base R, with no package dependency. SQL's null semantics come through as `is.na(x) | …`. No top-level assignment is generated, so the naming rule doesn't apply.
- Evaluating them with a 25-line harness (`run_assertions.R`, where a violation means the predicate is FALSE and NA passes) gives:
  - real data: all 17 pass, the same as the CLI;
  - faulty set: (b) and (f) caught at **the same rows as the CLI** (1 and 29).
- **Structural constraints aren't translated.** Primary key, foreign key, `required`, enum `values` and declared types produce no R code. So (a), (c), (d) and (e) are invisible on the R path.
- **(e) is worse than invisible.** `elasticity > 0L` on a character column **silently passes** in R, because of string comparison. The CLI refuses to evaluate the same assertion (D08).

**Consequence for the pipeline.** Cleaned data exists only in chunk caches (`agents/data-engineer.md`), so in-memory cleaned frames can be checked only through `translate`. Today that route covers row assertions and nothing structural. It would need hand-written key, type and enum checks next to it, which removes most of the reason to adopt it.

## Task 5 — ruling (2026-09-25)

| # | Criterion | Score | Evidence |
|---|---|---|---|
| C1 | Reads native formats without conversion | **fail** | Parquet only (spec §Source; CSV probe rejected). Conversion is small (`convert.R`), but globs are broken, so multi-file series must be stacked too. |
| C2 | Catches planted faults, ≥ 4/5 incl. (a) and (c) | **pass** | 6/6, plus the 10 real known duplicates. Blind spot: cardinality. |
| C3 | `translate` → chunk-usable R that respects the naming rule | **partial** | Clean base R, but assertions only; no structural checks; silent pass on a type-changed column. |
| C4 | Error messages fixable without reading source | **pass** | Every message pins a YAML line and column plus the offending rows. |
| C5 | Hand-tightening effort ≤ ~1 hour | **pass** | About 15 minutes for 5 tables. |
| C6 | Coauthor install: one command, no Rust | **partial** | One R call and no toolchain, but `dd_validate_data()` is broken against the released binary, and a Parquet writer is also needed. |

**Ruling: DEFER.**
- "Go" needs C1–C3 to pass. C1 fails and C3 is partial.
- Every blocker is v0.0.x immaturity, not a design problem:
  - Parquet as the only source;
  - the glob bug;
  - the R wrapper out of sync with the released binary;
  - `translate` covering assertions only.
- The checking itself is strong: 6/6 faults, precise messages, a good report.

**Re-test trigger.** Re-run Tasks 0, 3 and 4 of the plan once **any two** of these hold:
1. a CSV or R data-frame `source` (or an R-side validator that takes a data frame);
2. `parquet:` globs work;
3. the released binary and `datadict` R package agree on the report subcommand;
4. `translate` emits primary key, foreign key, `required` and enum checks.

The trial scripts (`convert.R`, `plant_faults.R`, `run_assertions.R`) and the tightened `data-dict.yaml` were in the scratchpad, which Task 5 deletes. The relevant content is recorded above.

**Upstream issue drafts.** Not filed; they need user approval. Check for existing issues first, since the HEAD R package already targets a newer CLI.
1. "`source: parquet:` globs fail with M05 in 0.0.3 (spec says globs are allowed), and one unreadable source aborts validation of every other table."
2. "`datadict::dd_validate_data()` calls `render-report`, which the 0.0.3 binary fetched by `dd_install()` lacks."
3. "Relationship `cardinality` isn't validated: `many-to-one` onto a non-unique column passes."

**Stopgap, outside the pipeline.** Running the CLI by hand on a paper's `data/raw/` Parquet copies at data-freeze time is cheap, and it found the known BPS duplicates unprompted. That's a personal-workflow option, not a pipeline change.
