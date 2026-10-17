# Design lock and prose binding — design

2026-10-12; revised 2026-10-17 with the author's rulings in §0. Status: approved spec. Branch
`feat/design-lock-prose-binding`.

## 0. Author rulings, 2026-10-17

These override anything below that reads otherwise.

1. **Adjusting a model after seeing results is standard practice** in economics and real estate.
   The pipeline does not treat it as a defect: no "results seen" field, no restriction on
   changes made after estimation, and no pre-registration language unless the paper has an
   actual pre-analysis plan. What the pipeline enforces is that every change is recorded once,
   in one place, and mechanically reopens the prose and reviews it affects.
2. **Significance convention, fixed:** `*` p ≤ 0.10, `**` p ≤ 0.05, `***` p ≤ 0.01. "Statistically
   significant" means p ≤ 0.10, and the prose states the level. The design block carries no α.
   A target journal's profile wins where it forbids stars or mandates other cutoffs.
3. **Signing is in chat.** The author approves in chat; the session then runs
   `pipeline.py design sign|unlock`. A `UserPromptSubmit` hook issues a one-time token when the
   author's own message approves signing or unlocking; the command refuses without a fresh
   token. An unattended run has no author message, so it cannot sign or unlock.
4. **Helpers are `rc_num`, `rc_pct`, `rc_sig`, `rc_stars`, `rc_dir`, `rc_cmp`.** `dir` is a base R
   function, and the R naming rule forbids assigning base names at top level.
5. **No model drops silently.** The fingerprint hashes every fitted model object in the
   environment, found by class (`lm`, `glm`, `fixest`, `fixest_multi`, `feols`, `felm`, `ivreg`,
   `plm`, `lm_robust`, extendable), with no registration step. The render also stops when a
   hypothesis's `spec:` names an object that does not exist.
6. **Staleness blocks commits,** except the commit that lands the re-estimation (it changes model
   chunk code or data hashes). After it, every manuscript commit is refused while any strategy,
   manuscript or referee score is stale, until a whole-manuscript writer-critic re-scores under
   the new fingerprint. Ledger rows fixed during that window close against the commit that ends
   it. Every session start prints the stale stages.
7. **The git hook ships as `hooks/git/pre-commit`,** beside the other hooks, installed via
   `core.hooksPath = .claude/hooks/git`. The Claude-hook auditors skip `hooks/git/`.
8. **Unattended runs make rulings and continue.** Each ruling is appended to
   `quality_reports/rulings_log.md` (date, decision, the alternative, reason) so it can be
   reversed cheaply. Two hard stops: a ruling that contradicts a decision the author recorded,
   and any change to the `design:` block (locked; needs signing in chat). Those go to
   `quality_reports/questions_for_author.md`, and that line of work stops.
9. **The design-change disclosure is generated.** `design sign` after an unlock appends a row to
   `quality_reports/design_amendments.csv` (date, field, old, new, reason) and a readable entry to
   `design_amendments.md`. A `tbl-design-changes` chunk renders the CSV; once any amendment
   exists, the commit check fails without that chunk. The author writes the prose around it.
10. **Power and size checks run in `explorations/`,** not in the manuscript
    (`rules/readable-code.md` §5). Their results are recorded in `design.checks` at signing and
    re-run on an amendment that touches the inference rule, sample, treatment or outcome.
11. **A result word is bound either way:** helper output, or a typed word with a `stopifnot()`
    result guard in the same sentence (`rules/readable-code.md` §5, L-011). The checker accepts
    both.
12. **The stricter wording gate applies only to retrofitted papers** (a `design:` block exists):
    verdict ceiling 0, the wider lexicon, jargon. Papers not yet retrofitted keep today's checker
    behaviour.
13. **The lock hashes the block's normalised text,** not parsed YAML (stdlib has no YAML parser).

## 1. Problem

A forensic audit of two paper projects, each on its 15th–20th manuscript rewrite, found three
structural causes. Instruction bloat was a minor one. The evidence is private and held outside
this public repo.

1. **The research design had no single, checked home.**
   - Hypotheses, treatment definition and date, sample and inference rule lived in memos,
     project `CLAUDE.md` files and prose at once, and contradicted each other.
   - Power and test-size checks ran only after results had been written up. Some inference
     rules then rejected 16–41% under the null at a nominal 5–10%.
   - One institutional fact had been marked verified and was wrong, and two design cycles were
     built on it. The strategist-critic checked each memo's internal logic, never the evidence.
   - A design change reopened nothing, so prose written for the old design survived.
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

The paper proceeds only on a design the author has signed in chat and that has passed power and
size checks. Every result-describing word in the prose is generated from, or guarded by, the
model objects on the first draft. A re-estimation mechanically reopens exactly what it
invalidates. Reviews converge instead of re-litigating.

Success means:
- the fixture manuscript's planted defects (§9) each fail their check;
- both retrofitted papers pass the gates with a signed design;
- the next whole-manuscript writer-critic round does not score 0 for internal contradiction.

## 3. Constraints honoured

Read before designing: `rules/core.md`, `rules/agents.md` §§1–6, `rules/quarto-empirical.md`,
`rules/readable-code.md`, and the repair rulings.

- **One manuscript.** Design, estimation, exhibits and prose stay in the single `.qmd`. There is
  no results file, no analysis script and no `source()`. Reading a data file (the amendments
  CSV) in a chunk is data, not code.
- **Every number is inline `r` (INV-11).** That is extended here to words; nothing is relaxed.
- **Readable code (`rules/readable-code.md`).** No size tests in the manuscript; result guards
  are plain `stopifnot()`; no wording scanners in manuscript code.
- **Critics never edit and never save their own reports** (agents §2). Each round is a fresh
  foreground dispatch (§3), and reports are never overwritten.
- **Live evals run with no timeout.**
- **Nothing project-specific ships.** This spec names no project, journal or dataset.

Rules this design changes, with the author's ruling:
- `agents.md` §6 and the finding ledger move from rule text to `pipeline.py` predicates.
- Critics in rounds 2+ see the ledger and the diff. That trades round independence for
  convergence; the author ruled for it (2026-10-13).

## 4. Component 1 — the design lock

**The design block** lives in the manuscript's YAML front matter under `design:`:

```yaml
design:
  inference: {rule: cluster-robust, cluster: region, id: INF-1}
  treatment:
    definition: "…operational test…"
    date: YYYY-MM-DD
    source: {cite: key2024, page: 12, quote: "…"}
  sample: ["…rule…", "…rule…"]
  hypotheses:
    H1: {estimand: "…", outcome: y, spec: m_h1, direction: negative}
  checks:
    power: {mde: 0.021, target_effect: 0.03, file: explorations/power.qmd}
    size:  {rejection_at_0.10: 0.104, reps: 1000, file: explorations/size.qmd}
```

- **Checks before signing.** Power and size run in `explorations/` (§0.10):
  - power: the minimum detectable effect is no larger than `target_effect`;
  - size: a placebo or simulation rejects within ±0.03 of the nominal level at 0.10.
  - `design sign` refuses unless `checks.power` and `checks.size` are present and the named
    files exist.
- **Signing** (§0.3). `pipeline.py design sign` hashes the canonicalised block into
  `quality_reports/design_lock.json` with the date and the signer. It needs a fresh author
  token.
- **Lock.**
  - A PreToolUse hook (`design-guard`) blocks any edit that changes the `design:` block while the
    lock is `signed`, and any Bash command that runs `design sign|unlock` without a token.
  - `pipeline.py pre coder`, `pre writer` and the pre-commit check fail when the block's hash
    differs from the lock.
- **Amendments.** After the author approves in chat: `design unlock --reason`, edit, `design
  sign`. Sign appends to the amendment CSV and MD (§0.9), re-signs, and the fingerprint's design
  hash change reopens writer, strategist and referee scores.
- **Strategist-critic** scores the memo against the `design:` block and the primary sources
  cited in `treatment.source`. Each treatment, date and institutional fact needs a located quote
  from a source read in that dispatch.

## 5. Component 2 — prose bound to model objects

- **Estimation stays in the `.qmd`.** The setup chunk sets
  `cache.extra = list(rc_design_hash(design), rc_data_hash())`, so a design amendment or a data
  change invalidates every model cache. `rc_data_hash` hashes the files under `data/raw/` and
  `data/derived/`. A cold-cache render is required before any commit that changes a model chunk.
- **Helpers live in the setup chunk,** pasted from `templates/claims-helpers.R.txt` (never
  sourced):
  - `rc_num(x, digits)`, `rc_pct(x, digits)` print numbers;
  - `rc_sig(p)` prints "statistically significant at the 1%/5%/10% level" or "not statistically
    significant" (§0.2);
  - `rc_stars(p)` prints `***`/`**`/`*`/"";
  - `rc_dir(b, up, down)` picks a verb from the sign;
  - `rc_cmp(a, b, more, less, same = NULL, tol = 0)` picks a comparison word.

  Every helper calls `stop()` on NA, NULL or a non-finite value. Projects with existing helpers
  keep their names as one-line aliases inside the same chunk.
- **Typed words with a guard** are accepted (§0.11): a sentence whose result word is typed passes
  when the same sentence carries an inline `stopifnot()` guard.
- **Raw inline `if`** is accepted. A literal threshold other than 0.10/0.05/0.01 warns.
- **`prose_number_check.py`, tightened.**
  - It scans the YAML title and abstract, chunk-generated captions and notes, `$…$` math and the
    response letter (all papers).
  - Retrofitted papers only (§0.12): a word from the result lexicon within the claim window of a
    value fails unless it is helper output, inside a guarded sentence, or a raw `if`. The lexicon
    covers significance, direction, comparison, magnitude and universality words; projects
    extend it with `prose-verdict-words:`. The verdict-word ceiling defaults to 0. Words get the
    same context allowlist as literals.
  - The allowlist matches a value in its context, not everywhere it appears.
- **Pipeline vocabulary is banned** (retrofitted papers). A shipped list
  (`references/pipeline-jargon.txt`, e.g. "governing p", "wording band", "rival reading",
  ruling-ID patterns) fails in manuscript prose. Projects can extend it.
- **`check_render.py`** checks the rendered PDF text for `NA`/`NaN`/`Inf` and the LaTeX log for
  overfull boxes.

## 6. Component 3 — invalidation and the finding ledger

- **Fingerprint.** The manuscript's final chunk writes `quality_reports/render_fingerprint.json`:
  the design hash, the data hash and `estimates_hash`, a digest of the coefficients, standard
  errors and N of every fitted model object in the environment (§0.5). `record-score` stores the
  fingerprint each score was earned under; this replaces the unread receipts hash.
- **Staleness.** `pre`, `post`, `score --gate` and the pre-commit check treat a writer,
  strategist or referee score earned under a different `estimates_hash` or design hash as stale
  (§0.6). Only a whole-manuscript writer-critic score clears the writer stage.
- **Finding ledger** (`quality_reports/findings_ledger.md`).
  - The dispatching skill writes one row per finding from each saved report: id, source report,
    location, finding, status (`open`, `closed <sha>`, `declined: <reason>`,
    `proposal: <pending|accepted|rejected>`).
  - `post <creator>` refuses while any row for that creator is open.
  - A decline is a ruling: unattended runs may decline with a reason, logged to the rulings log
    (§0.8), unless the finding restates a recorded author decision.
- **Rounds 2+.** The critic prompt carries the ledger and the diff since the last scored round.
  The critic verifies closures, flags regressions, reviews the changed text and every summary
  sentence, and labels any other new finding `missed-earlier`. Round 1 stays a cold read.
- **No re-review after a pass.** `pipeline.py` refuses to dispatch a critic on a passed target
  whose manuscript is unchanged, unless the author asks (`--author-request`).
- **Closed findings become guards.** When a fix is mechanically checkable, the creator adds a
  `stopifnot()` guard beside the claim, and the ledger row names it.
- **Simulated referees** enter the ledger as `proposal` rows. Accepting a proposal is a ruling
  (§0.8); one that touches `design:` needs signing in chat.

## 7. Component 4 — enforcement and sessions

- **Pre-commit hook** `hooks/git/pre-commit`, installed by `apply.sh` through `core.hooksPath`.
  On a commit that touches the manuscript it runs the design-lock check, `prose_number_check`,
  `quarto_structure_check`, the staleness check (§0.6), the cold-cache requirement when model
  chunks changed, and the disclosure check (§0.9). `--no-verify` remains forbidden.
- **Standalone skills.** `/analyze`, `/write`, `/revise` and `/review` run `pipeline.py pre` as a
  blocking step.
- **`protect-files`** adds a Bash-write check covering `pipeline_state.json`, critic reports,
  `design_lock.json`, the amendment files, `findings_ledger.md` and `rulings_log.md`.
- **Rulings** follow §0.8.
- **Instruction hygiene.**
  - research-claude's `CLAUDE.md` imports `rules/core.md`.
  - `check_install` turns the project `CLAUDE.md` size warning into a failure at 60 lines.
  - `check_install` fails when a project `CLAUDE.md` states design facts (date patterns beside
    "treatment", hypothesis lists). Those belong to `design:`.
- **`check_fork.sh`** fails on shipped changes that add `source(` in templates, results stores, or
  analysis scripts outside a manuscript.
- **Post-results sweep** (§0.1). Shipped text that treats a post-results change as a defect, or
  asks for a "results seen" record, is removed. Pre-analysis-plan templates stay for papers that
  actually have one. The star convention (§0.2) replaces `<` with `≤` wherever the shipped tree
  states it.

## 8. Retrofit (existing papers)

For each paper, in order, with a project commit after each step:
1. Write `design:` as the paper stands today, with existing amendments seeded into the CSV. Run
   the power and size explorations. The author signs in chat, or first resolves a size failure
   or a missing strategy memo.
2. Insert the helper setup chunk; existing helpers become aliases.
3. Run the tightened checker. Its failures become one fix list per paper, fixed before any new
   writing.
4. Seed the ledger from the open findings in current reports.
5. Render cold and run one whole-manuscript writer-critic under the new fingerprint.

## 9. Testing

- **Fixture manuscript** `tests/fixtures/design-lock/`. Each planted defect must fail its check,
  and the clean variant must pass:
  - a typed verdict word with no guard (a guarded one passes);
  - a direction verb typed against the sign;
  - an NA value;
  - pipeline jargon;
  - a typed number in a note;
  - an abstract claim;
  - an edit to the design block without an unlock;
  - `design sign` without an author token;
  - a model cache that survives a data change;
  - a robustness model, named in no hypothesis, whose re-estimation changes the fingerprint;
  - a stale writer score blocking a prose-only commit, while the re-estimation commit passes;
  - an amendment without the `tbl-design-changes` chunk;
  - an open ledger row at `post`;
  - a critic dispatch on a passed target.
- **Unit tests** for `pipeline.py design sign|unlock`, the token hook, the staleness predicate,
  the ledger and the rulings log.
- **Live evals** re-run for `/analyze`, `/write`, `/revise` and `/review`, with no timeout.
- **Release checks:** `check_fork.sh` and `check_install.sh --all` green after the re-link.

## 10. Out of scope

- Literature-claim verification (ledger L-009, the read-before-cite hook) is a separate plan.
- The superpowers plugin's session-start injection is a user-level setting.
