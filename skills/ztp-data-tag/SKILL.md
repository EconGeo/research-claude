---
name: ztp-data-tag
description: >
  Tag Zotero papers with the datasets they use (source, type, geography, period, variables, dependent variables, evidence page) using SQL grep over ChromaDB plus a local Ollama model — no Claude tokens per paper. Use for "tag my library with datasets", "what data do my papers use", "which papers use MLS data and where". Runs 15-paper passes, one collection at a time; Claude only reads the pass report and tunes the vocabulary.
argument-hint: "[--library user|group:<id>] [--collection NAME] [--pass N] [--yes]"
allowed-tools: Read, Edit, Bash
---

# ztp-data-tag v2 — local, grep-first dataset/variable tagging

Spec: `docs/superpowers/specs/2026-10-07-ztp-data-tag-v2-design.md` (research-claude).
Code: `scripts/data_tag.py` beside this file (package `scripts/data_tag/`), run with the
`zotpilot` micromamba env. Nothing here calls the ZotPilot MCP tools; the script reads the
Chroma and Zotero SQLite files read-only and writes Zotero through pyzotero.

## What a pass does

For each of N papers: select data/variable chunks from Chroma → regex grep against
`scripts/data_vocab.yaml` → one `qwen2.5:7b-instruct` call → merge → write the sidecar
(`~/.local/share/zotpilot/data_tags.sqlite`) → write Zotero tags + one "Data (auto-extracted)"
note → render `quality_reports/data_tags/pass_NN.md`.

Per-item write failures are recorded as `write_conflict` / `write_error` in the sidecar and the
pass continues (a later pass retries them). Only papers with status `ok` and at least one dataset
are written to Zotero; `model_error` papers get no note, tags or marker and are listed in the
report for a re-run. `DATA_TAG_MODEL` (env) overrides the model, as does `--model`.

Tags written: `dataset:<slug>` (vocabulary sources only), `datatype:<type>`, `geo:<level>`,
`var:<slug>`, `dv:<class>`, `data-tagged`, `data-tagged:v2` — from datasets the model reported
or confirmed. Grep-only (keyword) hits the model did not confirm are recorded in the sidecar and
shown as "keyword only" in the note and report, but are not tagged. Geography detail, periods
and evidence pages live in the sidecar and the note.

## Preconditions (stop with the fix if unmet)

1. `source ~/.secrets.env` in the shell you run from — `ZOTERO_API_KEY`, `ZOTERO_USER_ID`.
2. Ollama up with the model: `curl -s localhost:11434/api/tags | grep -q qwen2.5:7b-instruct`
   — else `open -a Ollama`, `ollama pull qwen2.5:7b-instruct` (see `/ztp-ollama`).
3. Papers indexed in Chroma. Unindexed items are listed in the report; index them with
   ZotPilot's `index_library` tool (ask the user first; Ollama must be up) and include them in a
   later pass.

## Step 1 — Dry run (always first on a new collection or after a vocabulary change)

```bash
micromamba run -n zotpilot python .claude/skills/ztp-data-tag/scripts/data_tag.py run \
  --library group:2350352 --pass <N> --n 15 --dry-run
```
Read `quality_reports/data_tags/pass_NN.md` **in full**. Check the per-paper table against
2–3 papers the user knows. The sidecar is written even in dry-run (pass rows are replaced on
re-run); Zotero is not touched. Re-running the same `--pass N` re-processes exactly the papers
recorded for pass N (sidecar rows replaced, notes updated in place); new items need a new pass id.

## Step 2 — **USER_REQUIRED**: approve the live run

Show the user the per-paper table and the review queue. Ask for an explicit yes before any
non-dry run. `--yes` in the skill invocation counts as that yes for the current pass only
(`run` itself has no `--yes` flag; `--yes` exists only on `undo`).

## Step 3 — Live run

Same command without `--dry-run`. Notes are written before tags; `data-tagged:v2` is the
idempotency marker — items carrying it are skipped on later passes, as are items already
recorded in the sidecar with zero datasets (`ok` / `no_candidates`), and items the sidecar's
write log shows an earlier pass already wrote (not undone) — so a pass run before desktop Zotero
has synced does not redo the previous pass (`skipped_written` in the report); `--refresh-v2`
forces reprocessing of all three. v1 items (`data-tagged` without `:v2`) are
reprocessed and their note updated in place.

## Step 4 — Tune between passes (this is where Claude tokens go)

From the report: (a) **Review queue** — promote real sources into `data_vocab.yaml` `sources`
(slug, name, regex aliases, type, geo_level, access) and DV needles into `dv_classes`;
(b) **Grep vs model** — model-only slugs need an alias, grep-only slugs may be false positives
(tighten the regex); (c) **Prompt** — if the model misreads a pattern across papers, adjust
`scripts/prompts/extract.md` (the extraction prompt), then re-dry-run;
(d) **Candidate selection** — papers flagged "heading regex missed" need a
`HEADING_RE` extension in `scripts/data_tag/candidates.py` *and* a positive case in
`tests/test_data_tag_candidates.py`. Bump `version:` in the YAML. Run
`micromamba run -n zotpilot python -m pytest tests/test_data_tag_*.py -q` in research-claude,
commit, then run the next pass with `--pass N+1`. Promotions are a **USER_REQUIRED** gate:
list them, wait for yes.

## Queries (sidecar; no Zotero needed)

```bash
DT=.claude/skills/ztp-data-tag/scripts/data_tag.py
micromamba run -n zotpilot python $DT query type residential-transactions-mls
micromamba run -n zotpilot python $DT query matrix
micromamba run -n zotpilot python $DT query topic "Housing rental yield"
```

## Undo

`data_tag.py undo --pass N` previews; `--yes` applies. It removes only the tags that pass
**added**, deletes only notes the pass **created**, and **restores the previous HTML** of notes the
pass updated (e.g. v1 notes), using the sidecar's write log. Tags that existed before the pass are
untouched. It reads the library from the pass record; an explicit `--library` that does not match
is refused. It is resumable (rows are marked undone); an item or note already gone from Zotero
(404) counts as undone.

## Whole-library run (only after the user says so)

`--library user --n 0 --pass N` processes every remaining indexed item; resumable via the
marker. Expect hours on local hardware; run it in a terminal tab, not inside a Claude turn.

## Rules

- Never call `manage_tags(action="set")` or any MCP write — the script merges tags itself.
- Never write to `chroma.sqlite3` or `zotero.sqlite`.
- No Claude-side extraction fallback. If the model is weak on a paper, the fix is the
  vocabulary, the heading regex, or `DATA_TAG_MODEL=qwen2.5:14b-instruct` — never Claude.
- Confirm before every live pass and before every vocabulary promotion.
