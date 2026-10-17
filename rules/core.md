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
   the end; a search hit is a location, not evidence. `[hook: read-gate for edits; judgment for claims]`
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
