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
