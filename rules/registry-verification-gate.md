# Write Gate: Registry Verification Before Any Manuscript Writing

**Nothing gets written in the manuscript until this gate is cleared.**

This rule exists because registry staleness is a structural bug, not a discipline
failure. Multi-session empirical projects accumulate stale RDS outputs when scripts
are run manually before being added to the master pipeline, when saveRDS is called
before a key transformation, or when the registry is frozen between analysis sessions
without a full pipeline re-run. Prose written against a stale registry embeds wrong
numbers that are invisible to code review, test suites, and coder-critics.

---

## The Gate Checklist (Non-Negotiable)

Before dispatching any writer agent or writing any manuscript section, the
orchestrator must confirm all five items:

```
[ ] 1. PIPELINE COMPLETE: Rscript scripts/R/00_master.R ran to exit code 0.
       Full pipeline only — not a selective re-run of individual stages.
       Timestamp of results_ground_truth.csv must be AFTER the main cleaned panel.

[ ] 2. GOLDEN TEST PASS: Rscript tests/test_results.R exits 0 with "PASS".
       No tolerance violations on any key. New keys noted but not blocking.

[ ] 3. SCRIPT INVENTORY: Every .R file in scripts/R/ that produces an RDS
       output is called via source() in 00_master.R. Run:
         comm -23 <(ls scripts/R/[0-9]*.R | sort) \
                  <(grep 'source(here' scripts/R/00_master.R | \
                    grep -o '[0-9][^"]*\.R' | sort)
       Zero orphaned scripts allowed. Any script not in master is a staleness trap.

[ ] 4. REGISTRY COVERAGE AUDIT: Read results_ground_truth.csv in full.
       Cross-reference against the manuscript outline. For every number that will
       appear in the paper — treatment effects, SEs, p-values, sample counts,
       robustness estimates, figure annotations — confirm a registry key exists.
       Missing keys must be added to the registry assembler and the pipeline re-run
       (items 1–2 again) before writing begins.

[ ] 5. REGISTRY TIMESTAMP CHECK: Confirm the registry was built from a fresh
       pipeline run that post-dates the most recent change to:
         - The main cleaned panel (data/cleaned/)
         - Any analysis script (scripts/R/0[3-9]*.R, scripts/R/1*.R)
         - Treatment/assignment data (data/raw/treatment/ or project equivalent)
       If any of these are newer than results_ground_truth.csv, re-run the pipeline.
```

To automate item 5, run this snippet from the project root (adapt paths to your project):

```r
registry_mtime   <- file.mtime(here::here("scripts/R/output/results_ground_truth.csv"))

# Adapt these two lines to your project's panel and treatment file locations:
panel_files      <- list.files(here::here("data/cleaned"), pattern = "\\.rds$",
                                full.names = TRUE)
treatment_files  <- list.files(here::here("data/raw/treatment"), full.names = TRUE,
                                recursive = TRUE)

analysis_scripts <- list.files(here::here("scripts/R"),
                                pattern = "^[0-9]+.*\\.R$", full.names = TRUE)
analysis_scripts <- analysis_scripts[!grepl("00_master", analysis_scripts)]

stale <- Filter(function(f) file.mtime(f) > registry_mtime,
                c(panel_files, treatment_files, analysis_scripts))

if (length(stale) > 0) {
  message("WARNING: registry may be stale. These files are newer than results_ground_truth.csv:")
  for (f in stale) message("  ", basename(f))
  message("Re-run scripts/R/00_master.R before writing.")
} else {
  message("Timestamp check PASS: registry is fresh.")
}
```

---

## When the Gate Applies

| Action | Gate required |
|--------|--------------|
| `/write [section]` — any section | Yes, before first invocation |
| `/write` resuming a prior section | Yes, if any analysis ran since last write |
| `/revise` responding to referees | Yes, always — R&R comments often prompt re-estimation |
| Response letter citing paper numbers | Yes — numbers must trace to fresh registry |
| Updating table notes or figure captions | Yes if numbers cited; no if purely formatting |
| Compiling/rendering the manuscript | No gate — rendering reads the manuscript as-is |

---

## Enforcement

The gate is checked by the orchestrator before writer dispatch. The writer agent
must not be dispatched until the orchestrator has confirmed all five items.

If the user says "just write it" or "skip the gate," the orchestrator should:
1. Report which gate items are open
2. Offer to run the pipeline now (Rscript scripts/R/00_master.R)
3. If the user explicitly overrides, write a WARNING in the session log and proceed

The gate is NOT skipped because coder-critic scored ≥ 80. Code quality and
execution freshness are orthogonal. A correct script that hasn't been run since
the data changed produces a stale output.

---

## The Registry Coverage Audit (Item 4 in Detail)

This is the step most likely to be skipped. It must not be.

**Procedure:**

1. Open `scripts/R/output/results_ground_truth.csv`. Read all keys.

2. Read the manuscript outline (section headers + planned subpoints).

3. For each planned numerical claim, find its registry key. Flag any with no key:
   - Treatment effect estimates and SEs
   - Confidence intervals
   - p-values (including for falsification/placebo tests — these are commonly omitted)
   - Sample counts (observations, treated units, control units)
   - Robustness specification estimates
   - Leave-one-out / sensitivity results cited by name
   - Figure annotation values (e.g., correlation coefficients, first-stage F-stats)

4. For every flagged claim: add a key to the registry assembler script, re-run
   the pipeline, confirm it lands in the CSV.

5. Record the registry key count and confirm it matches the number of keys in the CSV.

**Claims that commonly lack registry keys — add proactively:**

- Falsification test p-values (separate from the main estimate/SE)
- Robustness spec estimates for the PRIMARY outcome, not just surviving specs
- Synthetic control or matching sample sizes (treated N, donor pool N)
- Leave-one-out significance counts ("holds in X of Y exclusions")
- Pre-period model fit statistics (max placebo ATT, pre-period R²)
- Correlation coefficients and p-values in cross-validation exhibits

---

## The saveRDS Ordering Rule

When a script transforms an object before saving it, the `saveRDS()` call MUST
appear AFTER the transformation.

Bad (silent divergence — the RDS captures the pre-mutation state):
```r
result <- list(main = est_a, robustness = est_b)
saveRDS(result, "output/results.rds")      # ← saves est_b from prior step
result$robustness <- est_c                 # ← replacement happens AFTER save
write_csv(build_table(result), "tables/tab_main.tex")
```

Correct:
```r
result <- list(main = est_a, robustness = est_b)
result$robustness <- est_c                 # ← replace first
saveRDS(result, "output/results.rds")      # ← then save
write_csv(build_table(result), "tables/tab_main.tex")
```

The coder-critic checks for this pattern in any script that saves an RDS object
near a transformation of that object (see code-review-16-categories.md, Category 13).

---

## The Orphaned Script Rule

Every R script that produces an RDS output must be reachable from `00_master.R`
via a `source()` call. Scripts run manually during analysis are not automatically
added to master. This creates a staleness trap: the RDS exists, the registry reads
it, but subsequent pipeline runs don't regenerate it.

**After writing any new analysis script:**
1. Add it to `00_master.R` in the correct sequence (before the ground-truth assembler)
2. Add a comment with the stage number and a brief description
3. Verify the stage runs cleanly end-to-end in `00_master.R`

**Never commit a new analysis script without adding it to `00_master.R`.**

---

## How This Integrates with the Pipeline

```
Data acquisition
  ↓
01_build_panel.R  [data contracts: stopifnot at end]
  ↓
02..NN_*.R  [all sourced in 00_master.R, in order]
  ↓
NN_ground_truth.R  [assembles registry — runs last]
  ↓
tests/test_results.R  [golden test: PASS required]
  ↓
═══════════════════════════════════════
   WRITE GATE CHECKLIST (this rule)
═══════════════════════════════════════
  ↓
/write [section]  [writer dispatched ONLY after gate clears]
  ↓
writer-critic review
  ↓
/submit
```

The write gate sits between the golden test and the writer. Numbers that pass
this gate are traceable, fresh, and consistent. Numbers that don't are guesses.
