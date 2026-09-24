---
name: ztp-data-tag
description: >
  Backfill a structured "data used" field (datasets, variables, unit, timespan, access)
  onto papers already in your Zotero library, stored as both namespaced tags and a
  structured note. Trigger on: "tag my library with datasets", "extract datasets and
  variables from my papers", "backfill the data field", "what data do my papers use",
  "add data tags to Zotero", "build a data-discovery index from my library". Pilots one
  collection first, then offers to extend to the whole library. Opt-in and user-driven —
  it writes to your Zotero library, so it always confirms before batch writes.
argument-hint: "[--yes]"
allowed-tools: Read, Bash, mcp__zotpilot__*
---

# ztp-data-tag — Backfill the data field across your Zotero library

This skill reads papers already indexed in ZotPilot and records, for each one, the
**datasets and key variables it uses**. It stores the result two ways on each Zotero item:

- **Namespaced tags** — `dataset:hmda`, `var:loan-denial-rate`, plus a `data-tagged`
  marker — for filtering in Zotero and ZotPilot, and `[[wikilink]]`-style hubs in Obsidian.
- **A structured note** — a "Data (auto-extracted)" note holding the full JSON record.

It is **opt-in**: nothing runs until the user asks, and it always pilots one collection
and confirms before writing a batch.

## Schema

```json
{"datasets": [], "variables": [], "unit": "", "timespan": "", "access": "", "source": "full-text|abstract-only"}
```

- `datasets` — named data sources (e.g. "HMDA", "Zillow ZTRAX"). `[]` if none stated.
- `variables` — key measures/variables (e.g. "loan-denial rate", "LTV").
- `unit` — observation/geographic unit (e.g. "census tract").
- `timespan` — coverage (e.g. "2010-2020").
- `access` — "public (FFIEC)" / "proprietary (Zillow)" if identifiable.
- `source` — "full-text" if extracted from the indexed PDF, "abstract-only" if only the
  abstract was available (lower confidence — flag these for the user).

`source` is a quality flag layered on top of the five-key schema above, so any downstream
parser or Obsidian hub can treat every backfilled paper uniformly.

## Preconditions (check first; stop with guidance if unmet)

1. **ZotPilot MCP connected** — confirm `mcp__zotpilot__get_index_stats` is available.
   If absent, tell the user to set up ZotPilot (`/ztp-setup`) and stop.
2. **Write credentials configured** — tags and notes need `zotero_api_key` +
   `zotero_user_id`. If `mcp__zotpilot__manage_tags` / `mcp__zotpilot__create_note`
   fail for missing keys, stop and point the user to the ZotPilot install step in the
   research-claude README ("Step 7 — Install and configure ZotPilot") (write-ops config).
3. **Library indexed** — run `mcp__zotpilot__get_index_stats`. If many items are
   unindexed, warn that abstract-only extraction will be weaker for them.

## Step 1 — Pick a pilot collection (USER_REQUIRED)

Do NOT process the whole library on the first run. List collections with
`mcp__zotpilot__browse_library(view="collections")`, then **Option gate**
(`.claude/rules/option-gates.md`): rank 5–8 collections — columns *name*, *items*,
*indexed share*, *why a good pilot* (small, mostly indexed, empirical) — and wait; `--yes`
takes rank 1. The pilot processes that one collection (~N papers), shows the results, and
only then offers the rest of the library.

## Step 2 — Enumerate items, skip already-tagged

1. List items in the chosen collection via `mcp__zotpilot__advanced_search` (filter by
   collection) or `mcp__zotpilot__browse_library`.
2. Drop any item that already carries the `data-tagged` marker tag — those were done in a
   prior run. Report how many are new vs already-tagged.

If every item already carries `data-tagged`, report "collection already processed" and stop.

## Step 3 — Extract the data field per paper

For each batch of 5 new items, dispatch **data-tag-extractor**
(`.claude/agents/data-tag-extractor.md`; `Agent`, `subagent_type=data-tag-extractor`) with the
`doc_id`s and the collection name. It holds ZotPilot itself, runs the per-paper loop —
`get_paper_details` for metadata and abstract, one collection-scoped `search_papers` grouped by
`doc_id` for the data/methods chunks, `get_passage_context` on the best hits — and returns one
JSON record per paper in the schema above, with `source` set to `full-text` or `abstract-only`.
The whole-library loop therefore never lives in this context; only the records do.

Slugify tag values here: lowercase, spaces → hyphens (e.g. `dataset:zillow-ztrax`,
`var:loan-denial-rate`). Keep the readable names in the note's JSON. A record with empty
arrays is reported as such, not filled in.

## Step 4 — Preview and confirm (USER_REQUIRED before any write)

Show a table for the batch — title · datasets · variables · source — and ask for approval
before writing. Batch writes (>5 papers) must never run without confirmation.

## Step 5 — Write back to Zotero

**Note first, tags second.** The `data-tagged` marker is the library-wide idempotency key
(Step 2 skips anything carrying it, forever). Write `data-tagged` **only** for an item that
now holds a Data note. Writing it first and the note second let an item be marked done with no
note — silently and permanently.

For each approved item:

1. **Check for an existing Data note** — `mcp__zotpilot__get_notes(item_key=...)`. If a note
   titled "Data (auto-extracted)" is already there, the item is genuinely done: go to step 3.
2. **Note** — `mcp__zotpilot__create_note(idempotent=true, title="Data (auto-extracted)", ...)`
   containing the JSON block and a readable list. **`idempotent=true` skips creation if the
   item already has ANY ZotPilot note** — one from `/ztp-tutor` or `/ztp-research` counts —
   not specifically a Data note. So if the call returns without creating, **stop here for this
   item: do NOT write `data-tagged`.** Record it for Step 6 under
   "skipped: has a non-Data ZotPilot note (no Data note written)" so the user can decide.
3. **Tags** — only for an item that now has a Data note:
   `mcp__zotpilot__manage_tags(action="add", allow_new=true, ...)` with the `dataset:` and
   `var:` tags plus the `data-tagged` marker.
   - **`allow_new=true` is REQUIRED.** The `dataset:*`/`var:*` tags are new to the library
     vocabulary; without `allow_new=true`, `add` silently creates **none** of them.
   - Use `action="add"` ONLY. NEVER `action="set"` — set replaces all existing tags and is
     destructive.

   The note's content:

   ```
   Data (auto-extracted by /ztp-data-tag)

   {"datasets": ["HMDA"], "variables": ["loan-denial rate","LTV"], "unit": "census tract", "timespan": "2010-2020", "access": "public (FFIEC)", "source": "full-text"}

   - Datasets: HMDA
   - Variables: loan-denial rate, LTV
   - Unit: census tract · 2010-2020 · public (FFIEC)
   ```

## Step 5b — Merge near-duplicate tags

Before reporting, list every `dataset:*` / `var:*` tag written this batch next to any existing
library tag within edit distance 2 or differing only by a plural or a hyphen
(`dataset:hmda` vs `dataset:hmda-data`) — a near-duplicate splits the vocabulary Obsidian hubs
key on. Offer each pair as `keep both / merge into existing / merge into new`; `--yes` keeps
both. Merging is `manage_tags(action="add")` of the survivor then `action="remove"` of the
other — never `set`.

## Step 6 — Report and pause for review (USER_REQUIRED)

After the pilot collection, present a summary table and STOP:

- N processed · M with datasets found · K abstract-only (lower confidence)
- S skipped: has a non-Data ZotPilot note, so no Data note was written and **no
  `data-tagged` marker** — list them by title; they will be picked up again on the next run
  unless the user adds the Data note by hand or asks you to write it non-idempotently
- The tag namespaces created (`dataset:*`, `var:*`)

Then offer the user a choice — do NOT auto-continue:
1. Adjust the schema/tag conventions and re-run the pilot.
2. Run the next collection, or the whole library (resumable — skips `data-tagged`).
3. Re-index (`mcp__zotpilot__index_library`) so the new Data notes become searchable.

## Step 7 — Whole-library run (only after the user approves)

Same loop over all items (or the remaining collections), still in batches of 5 with the
`data-tagged` skip. Remind the user this is one LLM pass per paper — for a large library
it may span multiple sessions; the marker tag makes it resumable.

## Undo

- Remove tags: `mcp__zotpilot__manage_tags(action="remove")` for `data-tagged`,
  `dataset:*`, `var:*`. Removing `data-tagged` alone makes the item eligible for
  reprocessing on the next run.
- **Notes:** delete the "Data (auto-extracted)" note with
  `mcp__zotpilot__delete_note(note_key=...)` (find the key via
  `mcp__zotpilot__get_notes(item_key=...)`). It only deletes items of type 'note'
  and, by default, only ZotPilot-created notes. Delete the note **and** remove
  `data-tagged` together: an item with the marker and no Data note is exactly the state
  Step 5 exists to prevent.

## Rules

- **Opt-in & confirm.** Never write without an explicit user OK on the batch preview.
- **Pilot first.** Always one collection before any whole-library run.
- **`add` + `allow_new=true`, never `set`** for tags — `allow_new=true` is required or no
  new `dataset:*`/`var:*` tags are created; `set` is destructive (replaces all tags).
- **Notes are idempotent via `idempotent=true`** — re-runs won't duplicate them. But the
  flag keys on *any* ZotPilot note, so an item with a note from another skill gets no Data
  note; Step 5 checks `get_notes` first and never writes `data-tagged` for such an item. To
  remove a note, use `mcp__zotpilot__delete_note(note_key=...)` (note-type-guarded;
  ZotPilot-only by default).
- **Resumable & cross-project.** The `data-tagged` Zotero tag is the idempotency key —
  it lives on the item in the global Zotero library, so it is visible from every project.
  Always skip items that carry it unless the user asks for a refresh. NEVER track "done"
  state in a project-local file; that would silently re-tag the whole library in each new
  project. (Tags/notes persist in Zotero immediately; ChromaDB only reflects them after a
  re-index, which is needed for search but not for this skip check.)
- **Flag weak extractions.** Mark `source: abstract-only` items so the user can review.
- **Keep the five-key schema stable** — `datasets/variables/unit/timespan/access` — so
  Obsidian hubs and any parser treat every backfilled paper uniformly.
