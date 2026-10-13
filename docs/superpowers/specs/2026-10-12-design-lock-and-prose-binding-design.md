# Design lock and prose binding — design

2026-10-12. Status: spec, awaiting author review. Branch `feat/design-lock-prose-binding`.

## 0. Changes made while planning (author to confirm)

Reading the code changed seven details; the plan implements these, not the text below them.

1. **Signing is the author's terminal command.** `session-guard` cannot detect an unattended
   run, so the author runs `pipeline.py design sign|unlock` in their own terminal and the new
   `design-guard` hook refuses any agent attempt to run them. That makes the lock hold for
   unattended runs too.
2. **Helpers are `rc_num`, `rc_pct`, `rc_sig`, `rc_dir`, `rc_cmp`.** `dir` is a base R function,
   and the R naming rule forbids assigning base names at top level.
3. **No `rc_register()`.** The fingerprint takes its model list from the `spec:` of each
   hypothesis in the design block, and stops when one is missing. A side effect inside a cached
   chunk does not replay from the cache, so a registry would silently empty itself.
4. **At pre-commit, staleness is a warning, not a block.** Blocking it would refuse the very
   commit that lands a re-estimation. The block is at `post`, `next` and the score gates.
5. **The git hook ships as `templates/git-hooks/pre-commit`,** installed via
   `core.hooksPath = .claude/templates/git-hooks`. That keeps it out of the Claude-hook auditors.
6. **"Unattended runs make no rulings" is `[judgment]`:** a core rule plus skill text, with no
   hook behind it.
7. **The lock hashes the block's normalised text,** not parsed YAML (stdlib has no YAML parser).
   The design-change disclosure is a required `{#sec-design-changes}` section that the commit
   check enforces once an amendment exists. It is not a table generated from the log.

## 1. Problem

A forensic audit of two paper projects, each on its 15th–20th manuscript rewrite, found three
structural causes. Instruction bloat was a minor one. The evidence is private and held outside
this public repo.

1. **The research design was never frozen before estimation or prose.** This was 45–70% of the
   rework.
   - Hypotheses, the treatment definition and date, the sample, the inference rule and α all
     changed after results were seen.
   - Power and test-size checks ran only after results had been written up. Some inference
     rules then rejected 16–41% under the null at a nominal 5–10%.
   - One institutional fact had been marked verified and was wrong, and two design cycles were
     built on it.
   - The strategist-critic checked each memo's internal logic, never the evidence behind it.
2. **Only digits were bound to model output.** Verdict words, signs, direction verbs,
   comparatives and qualifiers were typed by hand. So were exhibit notes, the YAML abstract and
   the response letter, and all of them sat outside the checker.
   - This was the most frequent defect class: about 40% of all critic deduction points.
   - In one paper, across 725 matched rows, no estimate moved more than 1% between rewrites and
     none changed sign. Only the verdict words did.
3. **A model change invalidated nothing mechanically, and critics had no memory.**
   - Scores survived re-estimation, and `receipts.jsonl` stored a `.qmd` hash that nothing read.
   - Every round was a cold read: dozens of rounds ran on targets that had already passed, fixes
     introduced new deductions, and simulated referee "MUST"s were built and later deleted.
   - Stage gates block only when `/pipeline` calls `pipeline.py`; standalone skills skip `pre`.

## 2. Goal and success criteria

The paper proceeds only on a design the author has signed and that has passed power and size
checks. Every result-describing word in the prose is generated from the model objects on the
first draft. A re-estimation mechanically reopens exactly what it invalidates. Reviews converge
instead of re-litigating.

Success means:
- the fixture manuscript's planted defects (§9) each fail their check;
- both retrofitted papers pass the gates with a signed design;
- the next whole-manuscript writer-critic round does not score 0 for internal contradiction.

## 3. Constraints honoured

Read before designing: `rules/core.md` 1–11, `rules/agents.md` §§1–6,
`rules/quarto-empirical.md`, and the repair rulings.

- **One manuscript (core 1).** Design, estimation, exhibits and prose stay in the single `.qmd`.
  There is no results file, no analysis script and no `source()`.
- **Every number is inline `r` (core 4).** That is extended here to words; nothing is relaxed.
- **Critics never edit and never save their own reports** (agents §2). Each round is a fresh
  foreground dispatch (§3), and reports are never overwritten.
- **Live evals run with no timeout.**
- **Nothing project-specific ships.** This spec names no project, journal or dataset.

Rules this design changes, with the author's ruling of 2026-10-12:
- `agents.md` §6 and the finding ledger move from rule text to `pipeline.py` predicates.
- Critics in rounds 2+ see the ledger and the diff. That trades round independence for
  convergence; the author ruled for it.

## 4. Component 1 — the design lock

**The design block** lives in the manuscript's YAML front matter under `design:`:

```yaml
design:
  alpha: 0.10
  inference: {rule: cluster-robust, cluster: region, id: INF-1}
  verdicts: {sig: "statistically significant", nonsig: "not statistically significant"}
  treatment:
    definition: "…operational test…"
    date: YYYY-MM-DD
    source: {cite: key2024, page: 12, quote: "…"}
  sample: ["…rule…", "…rule…"]
  hypotheses:
    H1: {estimand: "…", outcome: y, spec: m_h1, direction: negative}
  checks:
    power: {mde: 0.021, target_effect: 0.03, chunk: chk-power}
    size:  {rejection_at_alpha: 0.104, reps: 1000, chunk: chk-size}
```

- **Pre-sign checks.** Two labelled chunks run in the `.qmd` and fail the render if they don't
  pass:
  - `chk-power`: the minimum detectable effect is no larger than `target_effect`.
  - `chk-size`: a placebo or simulation rejects within a tolerance of α (default ±0.03).
  - Each check writes its result back to the render log; the author copies it into `checks:`
    when signing.
- **Signing.**
  - `pipeline.py design sign` hashes the canonicalised `design:` block into
    `quality_reports/design_lock.json`, with the date and the signer. The session runs it only
    after the author approves in chat.
  - Unattended runs (`session-guard` detects them) cannot sign.
- **Lock.**
  - A PreToolUse hook (`design-guard`) blocks any edit to the `design:` block while a lock
    exists, unless a pending amendment approved in chat is recorded.
  - `pipeline.py pre coder` and the pre-commit hook fail when the block's hash differs from the
    lock.
- **Amendments.**
  - `pipeline.py design amend "<reason>"` runs after the author's approval in chat. It appends
    to `design_amendments.md` (date, field, old → new, reason, whether results had been seen),
    re-signs, and resets the writer, strategist and referee stages.
  - The paper's design-changes disclosure is an inline-rendered table generated from that file.
- **Strategist-critic** scores the memo against the `design:` block and the primary sources
  cited in `treatment.source`. Each treatment, date and institutional fact needs a located quote
  from a source read in that session.

## 5. Component 2 — prose bound to model objects

- **Estimation stays in the `.qmd`.** Model chunks set
  `cache.extra = list(rc_design_hash, rc_data_hash)`, so a design amendment or a data change
  invalidates every model cache.
  - `rc_data_hash` hashes the files the data chunks read under `data/raw/` and `data/derived/`.
  - A cold-cache render is required before any commit that changes a model chunk.
- **Helpers live in the setup chunk,** inserted from the shipped template
  `templates/claims-helpers.R.txt` (a text template, never sourced):
  - `num(x, digits)` and `pct(x, digits)` print numbers;
  - `sig(p)` prints `design$verdicts` at `design$alpha`;
  - `dir(b, up, down)` picks a verb from the sign;
  - `cmp(a, b, more, less, same = NULL, tol = 0)` picks a comparison word.

  Every helper calls `stop()` on NA, NULL or a non-finite value. `design` is read from the
  front matter by `rmarkdown::metadata`, or by `yaml` on the file as a fallback. Projects with
  existing helpers keep their names as one-line aliases inside the same chunk.
- **Raw inline `if`** is accepted when it compares against `alpha` or another design field. A
  literal threshold (`p < .1`) warns.
- **`prose_number_check.py`, tightened.**
  - It scans the YAML title and abstract, chunk-generated captions and notes, `$…$` math and the
    response letter.
  - A word from the result lexicon within the claim window of a value fails unless it is helper
    output or a design-referencing `if`. The lexicon covers significance, direction, comparison,
    magnitude and universality words, e.g. "significant", "rose", "fell", "larger", "doubled",
    "every specification"; projects extend it with `prose-verdict-words:`.
  - The verdict-word ceiling defaults to 0.
  - The allowlist matches a value in its context, not everywhere it appears.
- **Pipeline vocabulary is banned.** A shipped list (`references/pipeline-jargon.txt`, e.g.
  "governing p", "wording band", "rival reading", ruling-ID patterns) fails in manuscript prose.
  Projects can extend it.
- **`check_render.py`** checks the rendered PDF text for `NA`/`NaN`/`Inf`, overfull boxes and
  text running past the margin.

## 6. Component 3 — invalidation and the finding ledger

- **Fingerprint.**
  - The manuscript's final chunk writes `quality_reports/render_fingerprint.json`: the design
    hash, the data hash and `estimates_hash`, a digest of every fitted model's coefficients,
    standard errors and N, collected from objects registered with `rc_register(m)`.
  - `record-score` stores the fingerprint each score was earned under; this replaces the unread
    receipts hash.
- **Staleness predicate.**
  - `pre`, `post` and `score --gate submission` treat a writer, strategist or referee score
    earned under a different `estimates_hash` or design hash as stale.
  - Stale stages reopen. Only a whole-manuscript writer-critic score (`--scope whole`) clears
    the writer stage.
- **Finding ledger** (`quality_reports/findings_ledger.md`).
  - The dispatching skill writes one row per finding from each saved report: id, source report,
    location, finding, status (`open`, `closed <sha>`, `declined: <author reason>`,
    `proposal: <pending|accepted|rejected>`).
  - `post <creator>` refuses while any row for that creator is open.
- **Rounds 2+.**
  - The critic prompt carries the ledger and the diff since the last scored round. The critic
    verifies closures, flags regressions, reviews the changed text and every summary sentence,
    and labels any other new finding `missed-earlier`.
  - Round 1 stays a cold read.
- **No re-review after a pass.** `pipeline.py` refuses to dispatch a critic on a passed target
  whose fingerprint is unchanged, unless the author asks (`--author-request`).
- **Closed findings become guards.** When a fix is mechanically checkable, the creator adds a
  `stopifnot()` guard beside the claim, and the ledger row names it.
- **Simulated referees** enter the ledger as `proposal` rows. No session builds a proposal until
  the author accepts it, and one that touches `design:` needs an amendment.

## 7. Component 4 — enforcement and sessions

- **Pre-commit hook.** `hooks/git/pre-commit` is installed by `apply.sh` through
  `core.hooksPath`. On a commit that touches the manuscript it runs:
  - the design-lock check;
  - `prose_number_check`;
  - `quarto_structure_check`;
  - the staleness predicate;
  - the cold-cache requirement, when model chunks changed.
  `--no-verify` remains forbidden by the user rules.
- **Standalone skills.** `/analyze`, `/write`, `/revise` and `/review` run `pipeline.py pre` as
  a blocking step.
- **`protect-files`** adds a Bash-redirect check covering `pipeline_state.json`, the critic
  reports, `design_lock.json` and `findings_ledger.md`.
- **Unattended sessions make no rulings.** A decision point goes to
  `quality_reports/questions_for_author.md`, and that line of work stops.
- **Instruction hygiene.**
  - research-claude's `CLAUDE.md` imports `rules/core.md`.
  - `check_install` turns the project `CLAUDE.md` size warning into a failure at 60 lines.
  - `check_install` fails when a project `CLAUDE.md` states design facts (date patterns beside
    "treatment", hypothesis lists). Those belong to `design:`.
- **`check_fork.sh`** fails on shipped changes that add `source(` in templates, `saveRDS` results
  stores, or analysis scripts outside a manuscript.

## 8. Retrofit (existing papers)

For each paper, in order, with a project commit after each step:
1. Write `design:` as the paper stands today. Run `chk-power` and `chk-size`. The author signs,
   or resolves what fails first: an undisclosed post-results change, a missing strategy memo, a
   size failure.
2. Insert the helper setup chunk; existing helpers become aliases.
3. Run the tightened checker. Its failures become one fix list per paper, fixed before any new
   writing.
4. Seed the ledger from the open findings in current reports.
5. Render cold and run one whole-manuscript writer-critic under the new fingerprint.

## 9. Testing

- **Fixture manuscript** `tests/fixtures/design-lock/`. Each planted defect must fail its check,
  and the clean variant must pass:
  - a typed verdict word;
  - a direction verb typed against the sign;
  - a literal threshold in an `if`;
  - an NA value;
  - pipeline jargon;
  - a typed number in a note;
  - an abstract claim;
  - an edit to the design block without an amendment;
  - a model cache that survives a data change;
  - a stale writer score after re-estimation;
  - an open ledger row at `post`;
  - a critic dispatch on a passed target.
- **Unit tests** for `pipeline.py design sign|amend`, the staleness predicate and the ledger
  parser.
- **Live evals** re-run for `/analyze`, `/write`, `/revise` and `/review`, with no timeout.
- **Release checks:** `check_fork.sh` and `check_install.sh --all` green after the re-link.

## 10. Out of scope

- Literature-claim verification (ledger L-009, the read-before-cite hook) is a separate plan.
- The superpowers plugin's session-start injection is a user-level setting.
