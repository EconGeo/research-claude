---
name: analyze
description: End-to-end analysis inside the declared manuscript — dispatches data-engineer (wrangling chunks) and coder (estimation, robustness, tbl-/fig- chunks), each followed by coder-critic. R primary; Python/Julia via their engines.
argument-hint: "[goal or strategy-memo path] [--yes]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent
---

# Analyze

Run the analysis as chunks of the declared manuscript (`manuscript:` in `CLAUDE.md`), by
dispatching **data-engineer** then **coder**, with **coder-critic** after each.

**Input:** `$ARGUMENTS` — analysis goal or path to the strategy memo.

Read `.claude/rules/agents.md` before the first dispatch.

## Workflow

### Step 0: Resolve the manuscript and check inputs
```bash
python3 .claude/scripts/pipeline.py manuscript
python3 .claude/scripts/pipeline.py design status
python3 .claude/scripts/pipeline.py pre coder
```
**Design sign-off before the first chunk.** If the manuscript has a `design:` block that is not
signed (`design status` prints UNSIGNED), run the power and size explorations
(`explorations/power.qmd`, `explorations/size.qmd`), copy their results into `design.checks`, show
the author the block, and ask them to approve with the line `approve design sign` in their own
message (core rule 13). Only after that message run `pipeline.py design sign --signer <author>`,
then `pre coder`. Wrangling (Step 2) waits for signing too — `pre coder` fails on UNSIGNED — and
no chunk is dispatched before the block is signed; the power and size explorations read the raw
data directly. An unattended run
cannot sign: it writes the request with `pipeline.py question add` and stops that line of work
(core rule 16).

`pre coder` is a **blocking** step, standalone or orchestrated: a FAIL stops the skill and is
reported.

### Step 1: Pre-Code Report (mandatory)
The coder outputs `.claude/skills/analyze/templates/pre-code-report.md` filled in — strategy memo
path, paper type, naming map, planned **chunk labels** (not filenames). If the memo is missing,
proceed on the user's description and flag that categories 1–3 of the review cannot be verified.
Every row of the report's *Assumptions made* is an **Option gate**
(read `.claude/rules/option-gates.md` first) with 2–4 alternatives — sample restriction, control set,
clustering level, functional form are the usual ones; design questions belong to
`/strategize`, not here. Wait once for the whole table; `--yes` takes rank 1 on every row. The
picks are recorded in the report itself, which is saved alongside the coder-critic review.

### Step 2: Wrangling — data-engineer, then its paired critic
Read `.claude/rules/readable-code.md` before the first dispatch and name it in both creator
prompts. Dispatch **data-engineer**: `build-*` chunks with `cache.extra` (until the setup chunk sets the global `rc_data_hash()` key; then none), manifest rows, `tbl-summary`
chunk. Then `python3 .claude/scripts/pipeline.py log data-engineer` (standalone) and dispatch
**coder-critic** on the manuscript. Before every coder-critic dispatch (this step and Step 3, each
round), run `python3 .claude/scripts/pipeline.py critic-inputs` and name the log path it prints in
the prompt: coder-critic has no Bash and scores INV-11 and the render state from that log only.
Before that, run `python3 .claude/scripts/pipeline.py dispatch-ok coder-critic`: `PASSED-UNCHANGED`
(exit 1) means no dispatch unless the author asked (`--author-request`). From round 2, also run
`python3 .claude/scripts/pipeline.py critic-context coder-critic` and name the file it prints in
the prompt (`.claude/rules/agents.md` §3).
It returns its report as text; session saves it to
`quality_reports/reviews/coder-critic_<date>.md` first, then records its score:
`python3 .claude/scripts/pipeline.py state record-score code <score> --critic coder-critic --deductions <total> --report quality_reports/reviews/coder-critic_<date>.md`.
Then add one ledger row per finding in the report:
`python3 .claude/scripts/pipeline.py ledger add --creator <creator> --report <report path> --location <chunk or line> --finding "<finding>"`.
Three rounds maximum (`pipeline.py state strike data-engineer` after each failing round;
escalation target from the registry).

### Step 3: Estimation — coder, then its paired critic
Dispatch **coder**: `estimate-*`, `robustness-*`, `tbl-*`, `fig-*` chunks per
`.claude/skills/analyze/templates/chunk-structure.md`; render clean; prose check clean. Log,
run `dispatch-ok` and `critic-inputs` (and `critic-context` from round 2), dispatch
**coder-critic** with the log path, save its returned report to
`quality_reports/reviews/coder-critic_<date>.md`, record the score, then add one `ledger add` row
per finding. Three rounds maximum
(`pipeline.py state strike coder` after each failing round; escalation target from the registry).

### Step 4: What coder-critic checks
The twelve deductions in `.claude/rules/quarto-empirical.md` ("What the Coder-Critic Checks")
plus the numerical-discipline rows of `.claude/skills/review/config/scoring-rubrics.md`, using
`.claude/skills/review/templates/code-review-17-categories.md`; category 17 scores
`.claude/rules/readable-code.md`.

### Step 5: Present
Rendered output path; chunk labels added; coder-critic score; open items (missing data,
specifications the memo names that could not be run).

## Bundled resources
| File | Purpose |
|---|---|
| `.claude/skills/analyze/templates/chunk-structure.md` | the five chunk patterns |
| `.claude/skills/analyze/templates/pre-code-report.md` | mandatory pre-check |
| `.claude/skills/analyze/templates/paper-to-code-map.md` | naming map (lives in the setup chunk) |
| `.claude/skills/analyze/references/table-standards.md` | tables |
| `.claude/skills/analyze/references/figure-standards.md` | figures |
| `.claude/skills/analyze/gotchas.md` | failure points |

## Principles
- **Reproduce, don't guess.** If the user specifies a regression, run exactly that.
- **Readable, package first.** An established package for every estimator, every option that
  matters stated in the call, code an RA can check (`.claude/rules/readable-code.md`).
- **Root cause before retry.** On a chunk error or render failure,
  read `.claude/rules/systematic-debugging.md` and follow it — one hypothesis, smallest
  test, stop after two falsified attempts and report rather than guess a third time.
- **Strategy alignment.** If a memo exists, chunks implement it faithfully.
- **Creator then critic, every time.** Each creator's paired critic is declared in `.claude/rules/registry.yaml`, not restated here.
- **One manuscript.** No script tree, no results file, no output directory; the render is the output.
