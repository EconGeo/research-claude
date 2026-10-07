# ztp-data-tag v2 — local, grep-first dataset/variable tagging

**Status:** design approved in conversation 2026-10-07; spec awaiting user review.
**Supersedes:** the extraction engine of `skills/ztp-data-tag/SKILL.md` v1
(`docs/plans/2026-06-12-ztp-data-tag-skill.md`). The v1 tag namespaces and the Zotero note
stay compatible (§7).

## 1. Purpose

Record, for every paper in the Zotero library, **which datasets it uses, what kind of data
they are, their geographic extent and time span, which variables were drawn from them, and
which of those were dependent variables** — each with a pointer to the exact ChromaDB chunk
and PDF page where the paper describes it.

Two uses drive the design:

1. *How has topic X been studied?* — cross existing topic tags with data tags: "every paper
   using residential MLS data, with each paper's geography, period and dependent variable".
2. *What data exists that I could use?* — browse datasets, variables and geographies across
   the library to spawn new questions and new dataset combinations.

## 2. Constraints (set by the user)

- **Claude tokens are the scarce resource.** The whole library (3,388 indexed papers) must
  be taggable without a Claude call per paper. Grep does as much as possible; a local Ollama
  model does what grep cannot; Claude reads only a short per-pass report and tunes rules.
- **Controlled vocabulary with a review queue** (option C): known sources and types resolve
  to canonical slugs; anything the model names that is not in the vocabulary goes into a
  review queue that is promoted into the vocabulary between passes.
- **Storage = sidecar DB (truth) + Zotero tags + one Zotero note per paper** (option C).
- **Iterative passes of 15 papers**, first on the `affordable_housing` group library
  (groupID 2350352, libraryID 3; 59 items, 53 with PDFs, 42 indexed in Chroma as of
  2026-10-07). Each pass ends with a report; rules are revised before the next pass.
- **Approach A**: standalone script over Chroma, read-only. No change to the ZotPilot
  package, no re-index.

## 3. Facts the design rests on (verified 2026-10-07)

- Chroma lives at `~/.local/share/zotpilot/chroma/chroma.sqlite3`; 1.73M chunks. Every
  chunk's metadata (`embedding_metadata`) carries `chroma:document` (the text), `doc_id`
  (= Zotero item key), `doc_title`, `publication`, `year`, `doi`, `tags`, `collections`,
  `section`, `section_confidence`, `page_num`, `chunk_index`, `total_chunks`, `char_start`,
  `char_end`. Plain SQL `LIKE` over the text answers in well under a second.
- `section` is produced by `zotpilot/pdf/section_classifier.py` (read in full). **There is
  no `data` category.** A heading "Data" matches nothing and inherits the preceding span or
  becomes `unknown` (249k chunks); "Data and Methodology" matches `methods`. The section
  label is therefore a weak prior only; data headings must be detected from chunk text.
- Ollama is installed with embedding models only (`bge-large`, `nomic-embed-text`). No
  generative model is pulled. Hardware: Apple M3 Pro, 38 GB RAM, 28 GB free disk.
- The Zotero API key in `~/.secrets.env` (`ZOTERO_API_KEY`) has `write: true` on the user
  library and on **all groups** (`/keys/current`, checked 2026-10-07).
- v1 state in Zotero (user library only): 34 items carry `data-tagged`; 24 carry
  `dataset:*` (71 tags), 25 carry `var:*` (55 tags); 34 "Data (auto-extracted)" notes.
- v1 note JSON `{datasets, variables, unit, timespan, access, source}` shares its first five
  keys with journal-digest's `Data` field (`gather/writer.py`).
- `apply.sh` **links** `skills/*` into each paper project's `.claude/skills/`;
  `zotpilot-skills/` is vendored from the EconGeo/ZotPilot fork and overwritten by
  `scripts/sync-zotpilot-skills.sh`, so the new code must live in `skills/ztp-data-tag/`,
  not in `zotpilot-skills/`.

## 4. Architecture

```
skills/ztp-data-tag/
  SKILL.md                      # the workflow Claude follows (rewritten for v2)
  scripts/
    data_tag.py                 # CLI: select → grep → extract → normalize → write → report
    data_vocab.yaml             # controlled vocabulary: sources, types, DV classes, geo levels
    prompts/extract.md          # the Ollama prompt (versioned with the vocabulary)
    tests/                      # pytest fixtures: chunk texts, expected records
~/.local/share/zotpilot/data_tags.sqlite   # sidecar (source of truth)
<paper project>/quality_reports/data_tags/pass_NN.md   # per-pass report Claude reads
```

Runtime: the `zotpilot` micromamba env's Python (it already has `chromadb`, `httpx`;
add `pyyaml`, `pytest` if missing). Ollama model: `qwen2.5:7b-instruct` (JSON-schema output
via Ollama's `format` field — *to be tested in Task 1 of the plan*; fallback
`llama3.1:8b`, escalation `qwen2.5:14b`).

### 4.1 Pipeline per pass

```
data_tag.py run --library <group|user> --collection <name> --n 15 --pass <N> [--dry-run]
```

1. **Enumerate** items in the collection from Zotero SQLite (read-only, `immutable=1`),
   drop items carrying `data-tagged:v2`, drop items with no chunks in Chroma (reported as
   "unindexed — run index_library"), take the first `n` by item key order (deterministic,
   so pass N+1 continues where N stopped).
2. **Select candidate chunks** (SQL + regex, no model). For a `doc_id`, score each chunk:
   - `+5` data heading at chunk start:
     `^\s*(\d+(\.\d+)*\.?\s+)?(II+\.?\s+)?(Data|DATA|Sample|Variables?)( and (the )?(Sample|Sources?|Methodology|Methods?|Variables?|Descriptive Statistics|Summary Statistics|Empirical Strategy))?\s*$` (multiline; final list in `data_vocab.yaml`)
   - `+3` variable-definition heading (`Variable (Definitions?|Descriptions?)`,
     `Descriptive Statistics`, `Summary Statistics`, `^Table 1`)
   - `+1` per data cue, capped at 5: `data ?set|data source|we (use|employ|obtain|collect|draw|rely)|provided by|obtained from|observations|sample (period|consists|includes|covers)|transactions?|from (19|20)\d\d (to|through|–) (19|20)\d\d|(19|20)\d\d[–-](19|20)\d\d|at the (tract|block|parcel|county|MSA|zip)`
   - `+1` per variable cue, capped at 3: `dependent variable|outcome variable|regress(ed)? .{0,40} on|measured as|defined as|is the natural log|dummy (variable|equal)|indicator (variable|equal)`
   - `+2` any grep hit on a known source alias (§4.2)
   - `+1` if `section ∈ {methods, background, unknown, appendix}`; `−3` if `references`
   Keep the top 10 chunks plus each one's immediate neighbours, deduplicated, in document
   order — roughly 1,500–2,500 words. **This is the only text the model sees.**
3. **Grep layer.** Run every alias regex in `data_vocab.yaml → sources` over the candidate
   chunks (and, cheaply, over *all* the paper's chunks so a source named once in the intro
   is not missed). Each hit becomes a `datasets` row with `source=grep`, `confidence=0.9`,
   the vocabulary's default `type_slug`/`geo_level`, and an `evidence` row per hit chunk.
4. **Local extraction (Ollama).** One call per paper: `prompts/extract.md` + the candidate
   chunks (each prefixed `[chunk 17, p.6]`) + the grep hits as hints + the allowed `type`,
   `geo_level` and `dv_class` enums + a strict JSON schema (§5.1). Output: a list of
   datasets, each with its variables. Chunks are referenced by index so evidence is
   traceable without the model quoting text.
5. **Normalize & merge.** For each model dataset: match `name`/`provider` against vocabulary
   aliases → canonical `src_slug`; else `src_slug=NULL`, `name_raw` kept, and a
   `review_queue` row is written with a suggested slug. Merge with grep rows on `src_slug`
   (grep evidence + model-filled type/geo/period/variables). Validate enums; coerce years;
   map `geo.places` to `geo_level` when the model left it empty (simple rules: a US state
   name → `state`, "United States"/"national" → `national`, "MSA"/"metro" → `metro`).
   Variables: slugify; `role ∈ {dependent, independent, control, instrument, other}`;
   dependent variables additionally get `dv_class` from the vocabulary (review queue if
   unmatched).
6. **Write the sidecar** (always, even in `--dry-run`): `passes`, `datasets`, `variables`,
   `evidence`, `review_queue`. A re-run of the same pass id replaces that pass's rows.
7. **Write Zotero** (skipped in `--dry-run`): tags and the note (§7), via the Zotero Web API
   directly (`httpx`, key from `ZOTERO_API_KEY`), `PATCH` with `If-Unmodified-Since-Version`.
   Note first, then tags, then the `data-tagged:v2` marker — same ordering invariant as v1.
8. **Report** `quality_reports/data_tags/pass_NN.md` (§8).

### 4.2 Vocabulary — `data_vocab.yaml`

```yaml
version: 1
sources:
  costar:
    name: CoStar
    aliases: ['\bCoStar\b', '\bCo-Star\b']
    type: commercial-property
    geo_level: national          # default; model may override for a paper
    access: proprietary
  hmda:
    name: HMDA
    aliases: ['\bHMDA\b', 'Home Mortgage Disclosure Act']
    type: mortgage-loan-level
    geo_level: national
    access: public
  # … seed list in §9
types:            # closed enum; the model must pick one
  - residential-transactions-mls
  - residential-transactions-deeds
  - residential-listings-rents
  - commercial-property
  - mortgage-loan-level
  - reit-firm-financials
  - census-acs
  - administrative-program      # LIHTC, HUD, vouchers, tax records
  - survey
  - hazard-flood
  - hazard-disaster
  - climate-weather
  - zoning-land-use
  - permits-construction
  - gis-parcel-boundary
  - macro-financial-series
  - hand-collected
  - other
geo_levels: [parcel, neighborhood, city, metro, county, state, region, national, multi-country, global]
dv_classes:       # closed enum for data:dv tags; review queue for the rest
  - house-price
  - rent
  - transaction-volume
  - time-on-market
  - mortgage-approval
  - default-foreclosure
  - reit-return
  - cap-rate
  - construction-permits
  - affordability
  - displacement-mobility
  - other
```

Promotion from the review queue is an edit to this file plus a `version` bump; the pass
record stores the vocabulary version used, so later passes are comparable.

## 5. Data model

### 5.1 Extraction schema (what the model returns)

```json
{
  "datasets": [
    {
      "name": "Denver Metro MLS sales",
      "provider": "REcolorado",
      "type": "residential-transactions-mls",
      "geography": {"text": "Denver–Aurora–Lakewood MSA", "level": "metro", "places": ["Denver, CO"]},
      "period": {"start": 2010, "end": 2019},
      "unit_of_observation": "single-family sale",
      "access": "proprietary",
      "variables": [
        {"name": "log sale price", "role": "dependent"},
        {"name": "distance to light-rail station", "role": "independent"},
        {"name": "square footage", "role": "control"}
      ],
      "evidence_chunks": [17, 18]
    }
  ],
  "notes": "free text the model wants to flag (optional, ≤200 chars)"
}
```

Unknown fields are `null`, never guessed. `evidence_chunks` must be indices from the
candidate set; anything else is dropped and logged.

### 5.2 Sidecar — `~/.local/share/zotpilot/data_tags.sqlite`

```
passes      (pass_id PK, library, collection, n_docs, vocab_version, model, started_utc, notes)
documents   (doc_id PK, library_id, title, year, pass_id, status: ok|no_candidates|unindexed|model_error)
datasets    (id PK, doc_id, pass_id, name_raw, provider, src_slug NULL, type_slug, geo_text,
             geo_level, places_json, period_start, period_end, unit, access,
             confidence REAL, source: grep|llm|merged|manual)
variables   (id PK, dataset_id, name_raw, slug, role, dv_class NULL)
evidence    (id PK, dataset_id, chunk_index, page_num, snippet TEXT)   -- snippet ≤ 300 chars
review_queue(id PK, kind: source|dv_class|type, name_raw, doc_id, suggested_slug, status: open|promoted|rejected)
```

Cross-tab queries this must answer (acceptance tests on fixture data):

- all papers with `type_slug='residential-transactions-mls'` → title, geo_text, geo_level,
  period, dependent variables;
- for a topic tag present in Chroma `tags` (e.g. "Housing rental yield"), the distribution
  of `src_slug`/`type_slug` used;
- all distinct `(src_slug, geo_level)` pairs with paper counts — the "what data exists" view.

## 6. Local model

- `qwen2.5:7b-instruct` via `POST http://localhost:11434/api/chat` with `format: <json schema>`
  and `options: {temperature: 0, num_ctx: 8192}`. Before each run the script checks
  `/api/tags` and refuses to start if Ollama or the model is absent (same rule as
  `/ztp-ollama`).
- Expected cost: ~2–3k input tokens per paper, a few seconds each on M3 Pro; a 15-paper
  pass is minutes, not hours. The whole library (~3.4k papers) is an overnight job.
- A model failure (timeout, invalid JSON after one retry) records `status=model_error` and
  the grep rows still stand; the paper is listed in the report for a re-run.

## 7. Zotero writes — compatibility with v1

Namespaces **kept** (v1 already uses them on 34 items; Obsidian hubs key on them):

- `dataset:<src_slug>` — only for vocabulary sources; unlisted names stay in the review
  queue until promoted (no tag).
- `var:<slug>` — every extracted variable, any role.
- `data-tagged` — kept for v1 compatibility.

Namespaces **added**:

- `datatype:<type_slug>` — one per dataset.
- `dv:<dv_class>` — dependent variables only.
- `geo:<geo_level>` — one per dataset (level only; place names and years live in the
  sidecar and the note, not in tags).
- `data-tagged:v2` — the v2 idempotency marker. v2 skips items carrying it; v1-only items
  (`data-tagged` without `:v2`) **are** reprocessed by v2 so the 34 existing items gain the
  richer record. Their v1 note is replaced (see below), their v1 tags kept unless the user
  later asks for a cleanup.

Note: one child note per item titled **"Data (auto-extracted)"** (v1 title, so
`get_notes` consumers keep working). Content, regenerated from the sidecar each pass:

1. a v1-compatible JSON line `{"datasets": [...names], "variables": [...], "unit": "...",
   "timespan": "...", "access": "...", "source": "full-text", "schema": "v2"}` — the five
   journal-digest keys derived from the richer record;
2. a table: Dataset · Type · Geography · Period · Variables (DV in bold) · Page(s);
3. a footer: `pass NN · vocab vN · qwen2.5:7b · chunk ids …`.

Write path: Zotero Web API directly from the script (the MCP `create_note(idempotent=true)`
refuses to write if *any* ZotPilot note exists, which is exactly the v1 pitfall; the script
finds the existing "Data (auto-extracted)" note by title and `PATCH`es it, or creates it).
Tags are added with `PATCH` on the item's `tags` array (merge, never replace).

## 8. Pass report — what Claude reads

`quality_reports/data_tags/pass_NN.md`, kept under ~400 lines:

1. header: pass id, collection, n processed / skipped / unindexed / model_error, vocab
   version, model, wall time;
2. per-paper table: title · datasets (slug or *unlisted*) · type · geo · period · DVs · pages;
3. review queue additions this pass (name_raw, suggested slug, paper, snippet);
4. grep-vs-model disagreements: sources the model named that grep did not hit (candidate
   aliases), and grep hits the model did not use (candidate false positives);
5. candidate-selection diagnostics: papers whose top chunk scored < 5 (heading regex
   missed), average candidate word count;
6. a ready-to-apply "proposed vocabulary diff" block.

Claude's job per pass is to read this file, spot-check 2–3 papers with the user, apply the
vocabulary diff and regex tweaks, bump `version`, and start the next pass. That is the only
place Claude tokens are spent.

## 9. Seed vocabulary (pass 1)

Sources: CoStar, Real Capital Analytics, NCREIF (NPI/ODCE), CRSP, Compustat, SNL/S&P
Global, Bloomberg, Datastream, GRESB, MSCI ESG, HMDA, CoreLogic, ZTRAX/Zillow, Redfin,
ATTOM, DataQuick, MLS (generic + regional boards), ACS, Decennial Census, LEHD/LODES, CPS,
AHS, PSID, LIHTC database (HUD), HUD Picture of Subsidized Households, HUD Fair Market Rents,
FEMA NFHL / NFIP, NOAA Storm Events / Billion-Dollar Disasters, First Street, PRISM,
NOAA climate normals, Energy Star / LEED (USGBC), WRLURI, Saiz elasticity, county assessor
records (generic), Zillow ZHVI/ZORI, Apartment List, Yardi Matrix, RealPage, Moody's CRE,
Trepp, FRED. Each with aliases, default type and geo level. The first pass report will show
what this list misses.

## 10. Skill workflow (`SKILL.md` v2, summary)

1. Preconditions: Ollama up with the model pulled; Chroma present; `ZOTERO_API_KEY` set;
   target collection named. Stop with guidance otherwise.
2. `data_tag.py run … --dry-run` for the first pass on a new collection; show the report.
3. **USER_REQUIRED** gate before any non-dry run (same as v1).
4. Run for real; read the report; propose the vocabulary diff; **USER_REQUIRED** gate on
   promotions; bump version; next pass.
5. Whole-library mode (`--all --n 0`) only after the user says so; resumable via
   `data-tagged:v2`.
6. Undo: `data_tag.py undo --pass NN` removes that pass's tags and note changes using the
   sidecar as the record of what was written.

The v1 `agents/data-tag-extractor.md` becomes unused once v2 ships. Deleting it is a
separate, user-confirmed step (memory: confirm before delete); the spec only notes it.

## 11. Testing

- Unit (pytest, fixtures in `scripts/tests/`): heading regex (positives: "3. Data",
  "II. Data and Methodology", "Data and Sample"; negatives: "Data availability",
  "Results"), cue scoring, alias matching incl. word boundaries ("CoStar" not "costar
  analysis" in prose about costs), geo-level inference, schema validation (bad enum, bad
  chunk id, missing period), sidecar round-trip, note rendering, v1-JSON derivation.
- Integration (no Zotero writes): `--dry-run` on 3 known affordable_housing papers whose
  data sections the user knows; assert the expected `src_slug`s and at least one DV each.
- Ollama contract test: `format` with the schema returns parseable JSON for one fixture;
  if not, switch to prompt-embedded schema + post-validation and record the finding.
- Acceptance for pass 1: the per-paper table is judged by the user; target ≥ 12/15 papers
  with correct primary dataset and geography, ≥ 10/15 with a correct DV.

## 12. Out of scope (deliberately)

- Changing ZotPilot's section classifier (approach B). The heading regex from §4.1 is the
  input that change would need; revisit after the rules stabilise.
- Indexing the 11 unindexed affordable_housing PDFs (run `index_library` separately).
- Cleaning up v1 tags on the 34 items; Obsidian hub generation; journal-digest changes.
- Any Claude-side extraction fallback. If the local model is inadequate the fix is a
  larger local model, not Claude.
