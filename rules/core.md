# Pipeline core — the rules every session carries

The only pipeline rule file loaded at session start. Every other file in `.claude/rules/` loads on
demand: the skill or agent that needs it reads it. `[hook]`/`[script]` marks a rule a machine
enforces; `[judgment]` marks one nothing checks.

## The manuscript
1. **One manuscript.** The file declared on `manuscript:` in the project `CLAUDE.md` holds all
   cleaning, estimation, tables, figures and prose as cached chunks. No analysis script outside it.
   `[hook: script-guard]`
2. **Model tests that stay out of the paper go in `explorations/`** — its own `.qmd` or scripts.
   Acquisition scripts go in `scripts/acquire/` and write only `data/raw/`. Throwaway code goes in
   the session scratchpad. An exploration's number is not a result until a manuscript chunk
   produces it. `[hook: script-guard]`
3. **Read before you change or assert.** Before editing the manuscript, read all of it — above
   3,000 lines, the whole chunk or section you edit. Before stating what any file says, read it to
   the end; a search hit is a location, not evidence. `[hook: read-gate for edits; script: source_check for tagged claims; judgment for the rest]`
4. **Every number in prose is an inline `` `r ` `` expression** (INV-11).
   `[script: prose_number_check.py]`
5. **Exhibits, numbers and cross-references come from the renderer:** `tbl-`/`fig-` labelled
   chunks, `@tbl-`/`@fig-`/`@sec-` in prose, never a typed "Table 4" (INV-13, INV-25).
   `[script: quarto_structure_check.py]`
6. Before any `.qmd` edit, read `.claude/references/quarto-authoring.md`,
   `.claude/rules/quarto-empirical.md`, and the format rule for each output block the YAML
   declares (`quarto-pdf.md`, `quarto-word.md`). `[judgment]`

## Agents
7. **Every creator gets its paired critic from `.claude/rules/registry.yaml`; creators never score
   themselves; critics never edit.** Dispatch both in the foreground and save each returned report
   to disk the moment it returns. Before dispatching, read `.claude/rules/agents.md`.
   `[script: pipeline.py post]`
8. **Two failed fixes on one error → stop and report** the exact error and both hypotheses
   (`.claude/rules/systematic-debugging.md`). `[judgment]`

## Literature and the shared tree
9. **Zotero first.** ZotPilot `search_topic` → `advanced_search` → `search_papers`, then the web.
   A paper found online but not in Zotero is a gap to ingest with ZotPilot. `[judgment]`
10. **`.claude/{skills,agents,rules,hooks}` are symlinks into research-claude** — editing one
    changes every paper. Ask before editing; land approved changes with `/promote`. A
    paper-only change is a real file replacing the link; read `.claude/rules/shared-pipeline.md`
    before making one.
    When the user corrects the output of a shared skill, agent or rule, ask once: "Make this
    permanent in `<file>`?" (`.claude/rules/meta-governance.md`). `[judgment]`
11. Critics cite content invariants by number from `.claude/rules/content-invariants.md`, which
    they read themselves.

## Code
12. **Human-readable code, standard packages first.** Code is written for a research assistant
    to check line by line; every estimator comes from an established CRAN package, and custom
    code only when no package does the job.
    Before writing or reviewing code, read `.claude/rules/readable-code.md`.
    `[judgment: coder-critic category 17]`

## Design, results and review
13. **The design lives in the manuscript's `design:` block, and the author signs it in chat.**
    The block holds hypotheses → model objects, treatment with a located source quote, sample,
    inference rule, and the results of the power and size checks, which run in `explorations/`.
    The author approves with one line of their own message — `approve design sign`, or
    `approve design unlock: <reason>` — which issues a one-time token; only then does the
    session run `pipeline.py design sign|unlock`. Every amendment is recorded in
    `quality_reports/design_amendments.csv` and disclosed by a `tbl-design-changes` chunk.
    Adjusting a model after seeing results is normal; recording it is what is required.
    `[hook: design-token, design-guard; script: design-lock predicate, commit-check]`
    - **The approval line** is a whole line of the author's own message, trimmed and
      case-insensitive, optionally ending in one `.`: exactly `approve design sign` (nothing
      after it — `approve design sign: …` does not count), or `approve design unlock: <reason>`
      (the reason is required and recorded verbatim), or `approve sources: <id>[, <id>…]` (one-word
      ids; it issues the token for `pipeline.py sources approve`, see `quarto-word.md`). A line inside a fenced code block or
      starting with `>` does not count; a message must carry exactly one approval line.
    - **The token is fresh** only if the author's most recent message issued it, it is at most
      30 minutes old and unused, and it is for that operation and for the `design:` block as it
      stood at approval (a sources token: for exactly its ids). One successful `sign`, `unlock` or
      `sources approve` spends it.
    - **A session never submits an approval line itself** — design-guard refuses a nested
      `claude` command carrying one.
14. **Every result word is bound to the model:** helper output (`rc_sig`, `rc_stars`, `rc_dir`,
    `rc_cmp`, `rc_num`, `rc_pct`, pasted into the setup chunk from
    `.claude/templates/claims-helpers.R.txt`), a raw inline `if`, or a typed word in a sentence
    that carries an inline `stopifnot()` result guard whose condition reads a value
    (`stopifnot(TRUE)` binds nothing). Stars: `*` p ≤ 0.10, `**` p ≤ 0.05,
    `***` p ≤ 0.01; "statistically significant" names its level. `[script: prose_number_check.py]`
15. **A re-estimation reopens review mechanically.** Scores carry the results fingerprint; a
    strategy, manuscript or referee score earned under another one is stale, and manuscript
    commits are refused until it is re-scored (the re-estimation commit itself passes). A stale
    strategy or referee score reopens its own stage (`post`, `next`, score gates) and never
    blocks the next creator's `pre`; only a stale manuscript score does.
    Findings live in `quality_reports/findings_ledger.md`. A passed, unchanged target is not
    re-reviewed. `[script: pipeline.py; hook: pre-commit, stale-stages]`
16. **Unattended runs make rulings and continue.** Log each with `pipeline.py ruling add`
    (date, decision, the alternative, reason) in `quality_reports/rulings_log.md`. Two hard
    stops: a ruling that would contradict a decision the author recorded, and any change to
    the `design:` block. Write those with `pipeline.py question add` to
    `quality_reports/questions_for_author.md` and stop that line of work.
    `[judgment; script: ledger rulings]`
