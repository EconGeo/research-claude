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
allowed-tools: Read, Bash
---

# ztp-data-tag — Backfill the data field across your Zotero library

This skill reads papers already indexed in ZotPilot and records, for each one, the
**datasets and key variables it uses** — the same schema journal-digest captures for new
papers. It stores the result two ways on each Zotero item:

- **Namespaced tags** — `dataset:hmda`, `var:loan-denial-rate`, plus a `data-tagged`
  marker — for filtering in Zotero and ZotPilot, and `[[wikilink]]`-style hubs in Obsidian.
- **A structured note** — a "Data (auto-extracted)" note holding the full JSON record.

It is **opt-in**: nothing runs until the user asks, and it always pilots one collection
and confirms before writing a batch.

## Schema (shared with journal-digest)

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

The first five keys are identical to journal-digest's `Data` field, so Obsidian hubs and
any parser treat digest-filed and library-backfilled papers the same. `source` is an
extra quality flag.

## Preconditions (check first; stop with guidance if unmet)

1. **ZotPilot MCP connected** — confirm `mcp__zotpilot__get_index_stats` is available.
   If absent, tell the user to set up ZotPilot (`/ztp-setup`) and stop.
2. **Write credentials configured** — tags and notes need `zotero_api_key` +
   `zotero_user_id`. If `mcp__zotpilot__manage_tags` / `mcp__zotpilot__create_note`
   fail for missing keys, stop and point the user to README Step 7 (write-ops config).
3. **Library indexed** — run `mcp__zotpilot__get_index_stats`. If many items are
   unindexed, warn that abstract-only extraction will be weaker for them.

## Step 1 — Pick a pilot collection (USER_REQUIRED)

Do NOT process the whole library on the first run. List collections with
`mcp__zotpilot__browse_library(view="collections")` and ask:

> "Which collection should I pilot data-tagging on? I'll process that one (~N papers),
>  show you the results, and only then offer to run the rest of your library."

Wait for the user to choose one collection.

## Step 2 — Enumerate items, skip already-tagged

1. List items in the chosen collection via `mcp__zotpilot__advanced_search` (filter by
   collection) or `mcp__zotpilot__browse_library`.
2. Drop any item that already carries the `data-tagged` marker tag — those were done in a
   prior run. Report how many are new vs already-tagged.

If every item already carries `data-tagged`, report "collection already processed" and stop.

## Step 3 — Extract the data field per paper

**How text reaches you (important):** there are two channels and no full-PDF read.
- `mcp__zotpilot__get_paper_details(doc_id=...)` returns **metadata + abstract** from
  Zotero's SQLite — *not* the body.
- The body (data/methods) lives only as **chunks in ChromaDB**. You retrieve it with
  `mcp__zotpilot__search_papers` (semantic, returns top-K matching chunks) and
  `mcp__zotpilot__get_passage_context` (surrounding chunks). There is **no tool that
  returns a paper's full text or all of its chunks** — you extract from retrieved chunks.

For each new item (work in batches of 5):

1. Get metadata + abstract via `mcp__zotpilot__get_paper_details(doc_id=...)`.
2. Get the data/methods passages from ChromaDB: run `mcp__zotpilot__search_papers` scoped
   to this `doc_id` with a data-oriented query such as
   `"data sources dataset sample period variables identification methods"`, then
   `mcp__zotpilot__get_passage_context` on the best hits to pull adjacent context. Because
   this returns top chunks (not the whole paper), run a second query if the first misses
   the data section.
3. Set `source`: "full-text" if the item is indexed and chunks came back; "abstract-only"
   if it is **not** indexed (you then have only the abstract from step 1 — lower confidence,
   datasets are often absent from abstracts).
4. Fill the schema from the abstract + retrieved chunks. Datasets/variables are usually in
   the data/methods section. If nothing is identifiable, leave arrays empty and say so in
   the report.
5. Slugify tag values: lowercase, spaces → hyphens (e.g. `dataset:zillow-ztrax`,
   `var:loan-denial-rate`). Keep the readable names in the note's JSON.

## Step 4 — Preview and confirm (USER_REQUIRED before any write)

Show a table for the batch — title · datasets · variables · source — and ask for approval
before writing. Batch writes (>5 papers) must never run without confirmation.

## Step 5 — Write back to Zotero

For each approved item:

1. **Tags** — `mcp__zotpilot__manage_tags(action="add", ...)` with the `dataset:` and
   `var:` tags plus the `data-tagged` marker.
   - Use `action="add"` ONLY. NEVER `action="set"` — set replaces all existing tags and is
     destructive.
2. **Note** — `mcp__zotpilot__create_note` with a note titled "Data (auto-extracted)"
   containing the JSON block and a readable list:

   ```
   Data (auto-extracted by /ztp-data-tag)

   {"datasets": ["HMDA"], "variables": ["loan-denial rate","LTV"], "unit": "census tract", "timespan": "2010-2020", "access": "public (FFIEC)", "source": "full-text"}

   - Datasets: HMDA
   - Variables: loan-denial rate, LTV
   - Unit: census tract · 2010-2020 · public (FFIEC)
   ```

## Step 6 — Report and pause for review (USER_REQUIRED)

After the pilot collection, present a summary table and STOP:

- N processed · M with datasets found · K abstract-only (lower confidence)
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
  `dataset:*`, `var:*`.
- Delete the "Data (auto-extracted)" notes.

## Rules

- **Opt-in & confirm.** Never write without an explicit user OK on the batch preview.
- **Pilot first.** Always one collection before any whole-library run.
- **`add`, never `set`** for tags — `set` is destructive.
- **Resumable & cross-project.** The `data-tagged` Zotero tag is the idempotency key —
  it lives on the item in the global Zotero library, so it is visible from every project.
  Always skip items that carry it unless the user asks for a refresh. NEVER track "done"
  state in a project-local file; that would silently re-tag the whole library in each new
  project. (Tags/notes persist in Zotero immediately; ChromaDB only reflects them after a
  re-index, which is needed for search but not for this skip check.)
- **Flag weak extractions.** Mark `source: abstract-only` items so the user can review.
- **Same five shared keys as journal-digest** — keep `datasets/variables/unit/timespan/access`
  identical so Obsidian hubs and any parser treat digest and library papers uniformly.
