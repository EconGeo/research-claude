# ztp-data-tag v2 — execution record (SDD ledger, rulings + deferred minors)

Executed 2026-10-07, commits 512e471..2422bf4. Task 12 (live pass 1) not executed — user-gated.

Spec: docs/superpowers/specs/2026-10-07-ztp-data-tag-v2-design.md (read in full). Branch feat/ztp-data-tag-v2, start 512e471.

## Pre-flight scan
| Pair / task | Produces → consumes | Finding |
|---|---|---|
| T1 | conftest path; Ollama model | tests/conftest.py absent → create. qwen2.5:7b-instruct NOT pulled (only bge-large, nomic) → Step 1 pull needed |
| T2→T4,T5,T6 | Vocab.match_sources/resolve_* | consistent |
| T2 self | tests vs YAML/code | checked costar/hmda/resolve/dv cases by hand — consistent |
| T3→T4,T6,T10 | Chunk fields | consistent |
| T4 self | test_scoring_components vs DATA_CUES | DEFECT: cues=2 (tested: findall → ['We obtain','transactions']); test needs ≥3 and score ≥12 |
| T5→T6,T10 | validated output shape | consistent |
| T6 self | test_status_no_candidates vs build_records | DEFECT: build_records([] chunks) returns 'unindexed', test + Review Focus 1 require 'no_candidates' |
| T6→T7,T9 | dataclass positional order | consistent |
| T7→T9,T10 | Sidecar methods | consistent |
| T8 self | FakeZot.item vs upsert_note update path | DEFECT: FakeZot.item only knows items_db → KeyError on note N1 |
| T8 self | PreConditionFailed import | DEFECT: pyzotero 1.13.1 exports PreConditionFailedError (tested) |
| T8→T10 | ZoteroWriterV2 + remove_tags/delete_note | T10 appends methods to T8 file — fine |
| T10 self | test_query_type expects 'T AAA' | DEFECT: title comes from Zotero fixture ('Paper A'), not Chroma |
| T10 self | undo deletes note_key | RISK: pre-existing (v1) notes updated in place would be deleted by undo |
| T10 entry | main returns dict | plan Step 5 adjusts data_tag.py — fine |
| T11 | README:558-561, :590 | line numbers must be located by content |
| T12 | live Zotero writes + USER gates | outward-facing; not automatable |

## Rulings
- Ruling: T4 — generalize year-range cue to `(?:19|20)\d\d\s?(?:[–-]|to|through)\s?(?:19|20)\d\d` (keep the `from …` form subsumed) so "2010 to 2019" counts — test is spec; spec §4.1 lists year ranges as cues — cost if wrong: slightly more cue hits per chunk.
- Ruling: T6 — build_records returns status 'no_candidates' when chunks or candidates are empty; 'unindexed' is decided upstream in cli — Review Focus 1 + test — cost if wrong: none (cli never passes empty chunks for indexed docs).
- Ruling: T8 — FakeZot.item falls back to notes by key (mirrors real pyzotero, which fetches any item by key); test assertions unchanged — cost if wrong: none.
- Ruling: T8 — import `PreConditionFailedError as PreConditionFailed` (module attr name kept for tests); implementer must verify by reading installed pyzotero that update_item raises on 412 and accepts the full item dict from zot.item() (else pass item["data"]) — cost if wrong: live 412 path untested.
- Ruling: T10 — test_query_type asserts 'Paper A' (Zotero title is the documents.title of record) — cost if wrong: none.
- Ruling: T10 — ZoteroWriterV2.upsert_note sets `self.last_note_created`; cli records note_key only when the note was created this pass (getattr default True for fakes), so undo never deletes a pre-existing v1/earlier note — non-destructive per "confirm before delete" — cost if wrong: undo leaves v2 content in previously-existing notes instead of restoring them.
- Ruling: T12 (pass 1 live on affordable_housing) is NOT executed by this SDD run — USER_REQUIRED gates + cloud writes; handed back to user — cost if wrong: one extra session.
- Ruling: T1 Step 1 `ollama pull qwen2.5:7b-instruct` (~4.7 GB) runs — explicitly in the approved plan/spec — cost if wrong: disk space, removable with `ollama rm`.

## Tasks
Task 1: minor (deferred): contract test probes Ollama at collection time (≤3s) — plan-mandated
Task 1: minor (deferred): data_tag.py entry shares name with package data_tag/ (package wins on sys.path) — plan-mandated
Task 1: complete (commits 512e471..bf7da93, review clean; ⚠️ model pulled + contract PASS verified by controller)
Task 2: Ruling: resolve_dv substring collisions (plan-mandated; "apparent"→rent, "random"→time-on-market, "price-to-income"→house-price) — fix: needles match at a word start (`\b` + escaped needle, case-insensitive, no trailing bound so stems/plurals work) and the LONGEST matching needle across all classes wins — spec §4.1 wants DVs mapped to the right class; cost if wrong: a few stems miss mid-compound words.
Task 2: minor (deferred): reviewer's "trailer should be Sonnet 5.5" is wrong — session attribution is Opus 5.5
Task 2: minor (deferred): Vocab.load raises bare KeyError/re.error on malformed YAML entry; loose 'First Street'/'Billion-Dollar' aliases (plan-mandated)
Task 2: fix round 1/5 (1 addressed, 1 open — U+2019 still absent from aliases/tests; commits d874834..b28647f)
Task 2: fix round 2/5 (1 addressed, 0 open; commits b28647f..a424c96)
Task 2: complete (commits bf7da93..a424c96, review clean)
Task 3: minor (deferred): ORDER BY chunk_index has no m.id tiebreak; connection never closed; unused `rows=[]` in fixture; missing chunk_index → 0
Task 3: complete (commits a424c96..1a63ef4, review clean)
Task 3: Ruling: real Chroma has colliding chunk_index values (figure captions share an index with body chunks, ~4/609 per paper) — chunks_for_doc keeps all rows; Task 4 select_candidates must work on list positions (neighbours = adjacent list positions, no dict keyed by chunk_index) so no chunk text is dropped; evidence lookups keyed by chunk_index downstream accept the ambiguity (page approximate for colliding caption chunks) — cost if wrong: evidence page for a figure-caption chunk may point at the body chunk's page.
Task 4: minor (deferred): HEADING_RE comment says "first non-empty line" but matches any line in text[:200]
Task 4: minor (deferred): heading gaps (plan-mandated lists): "Methods and Data", "Data and Sample Construction", "Our Data", "Sample selection" don't match; best real score only 4 on 2WF6CLF5 and 2C9XFEWY → heading signal rare on real chunks — pass-1 tuning target
Task 4: complete (commits 1a63ef4..f5adb14, review clean; ⚠️ diagnostic verified by controller: 20/19 cands, 1637/1706 words, top_k stays 10)
Task 5: Ruling: brief's code (level enum = geo_levels + [None]) conflicts with brief's test (enum == geo_levels) — spec §5.1 "unknown → null" wins: schema allows null level; test asserts non-null members == vocab.geo_levels and None in enum; live Ollama call must still return valid JSON — cost if wrong: model returns null level more often (geo inference in normalize fills it).
Task 5: minor (deferred): datasets with no valid evidence still written with []; silent coercion of unknown level/role not logged; untyped pass-through of provider/unit/access/places; bool evidence index passes isinstance(int); check_ready untested; no brace-in-chunk test; 4xx retried once
Task 5: fix round 1/5 (2 addressed, 0 open; commits 6e94afb..07ee9f2)
Task 5: minor (deferred): some defensive drops silent (non-str var names/places, non-dict geography/period); non-str provider/access/geo_text pass through
Task 5: observation: live 7b output on 2WF6CLF5 — HUD FMR, HUD PSH, Census PUMS; periods null; ~38 s/paper
Task 5: complete (commits f5adb14..07ee9f2, review clean)
Task 6: Ruling: plan-mandated merge defects fixed — a second LLM dataset resolving to an existing slug merges into it (union variables by slug, union evidence by chunk, non-null-wins for scalar fields, keep first name_raw); the grep→LLM merge also never overwrites a value with null — spec §4.1 "merge on src_slug" without data loss — cost if wrong: two genuinely distinct products of one provider collapse into one record (tags preserved).
Task 6: Ruling: infer_geo_level hardened — word-bounded state names, "Washington, DC"/"District of Columbia" → city, `usa\b`, "state of the art" excluded, "City, State-name" place/text → city, places-only state name → state; brief's parametrized cases must still pass — cost if wrong: some levels stay None (sidecar keeps geo_text).
Task 6: minor (deferred): review items not deduped; dv_class snippet is dataset name; possible empty var: slug; evidence not deduped within LLM/grep lists
Task 6: fix round 1/5 (3 addressed, 1 new open — exclusion lookahead drops '<State> State'/'<State> Department'; commits cd1858b..4dd844a)
Task 6: minor (deferred): 'Cities in Texas, Colorado' → city (loose city-state prefix); obscure not-set.add() dedup idiom
Task 6: fix round 2/5 (1 addressed, 0 open; commits 4dd844a..c11742a)
Task 6: complete (commits 07ee9f2..c11742a, review clean)
Task 7: Ruling: plan-mandated sidecar defects fixed — _delete_doc_rows also deletes the doc's OPEN review_queue rows (resolved rows kept); write_doc body wrapped in a transaction (`with self._con:`) so a failure rolls back — Review Focus 5 "re-run replaces rows" — cost if wrong: none.
Task 7: minor (deferred): DATA_TAGS_DB read at import; positional INSERT column order; query_by_type one row per dataset; no close(); topic_crosstab param name differs from brief prose
Task 7: fix round 1/5 (2 addressed, 0 open; commits 801d332..06e014a)
Task 7: complete (commits c11742a..06e014a, review clean)
Task 8: minor (deferred): url_params hack uncommented; geo_level/src_slug unescaped in note; collection filter name-only; dead items_db line in FakeZot; enumerate found 61 items (plan expected 59); 2C9XFEWY year None
Task 8: fix round 1/5 (2 addressed, 0 open; real pyzotero raises PreConditionFailedError on 412 — pinned by MockTransport test; commits 41186e4..0c6d3ff)
Task 8: complete (commits 06e014a..0c6d3ff, review clean)
Task 9: Ruling: render_pass_report gains optional kwarg `extra_counts: dict[str, list[str]] | None = None` (keys skipped_v2, unindexed → counts + keys in header); Task 10 CLI passes them — spec §8.1 needs skipped/unindexed but the brief's signature can't carry them — cost if wrong: one extra kwarg.
Task 9: Ruling: review queue and vocab diff grouped by (kind, suggested_slug) listing all papers; slugs already in vocab flagged not re-proposed; average candidate word count added (spec §8.5); placeholder `access: unknown` kept but comment says edit access too — cost if wrong: none.
Task 9: minor (deferred): "wall" is sum of per-doc time; ~400-line cap not enforced; empty grep-vs-model section prints no placeholder; candidate section lists all papers
Task 9: minor (deferred): same slug with different name_raw keeps only first name as alias; None slug renders "None"; extra_counts keys unescaped
Task 9: fix round 1/5 (4 addressed, 0 open; commits bae23c7..dfff4be)
Task 9: complete (commits 0c6d3ff..dfff4be, review clean)
Task 10: Ruling: Step 6 real dry run uses --sidecar and --report-dir inside the SDD workspace (not the real sidecar, not /tmp) so the real ~/.local/share/zotpilot/data_tags.sqlite starts clean for pass 1 — cost if wrong: none.
Task 10: Ruling: write-safety fixes before any live use (spec §10 undo is the safety net): (1) log the note in zotero_writes immediately after upsert_note, per-item `except Exception` → status write_error, pass continues, report always written; (2) zotero_writes gets undone_utc; undo skips undone rows, marks each on success, per-row error handling, skips empty-tag PATCH, treats a missing note (404) as already gone; (3) re-running an existing --pass N re-processes exactly that pass's recorded doc_ids (marker ignored for them), new items need a new pass id; (4) store prior note HTML (prev_note_html) when updating a pre-existing note, undo restores it; (5) undo reads library from the passes table, refuses an explicit mismatching --library; (6) items already recorded in the sidecar (status ok/no_candidates) are skipped like v2-marked items unless --refresh-v2 — keeps passes advancing without marker writes on no-data papers — cost if wrong: more sidecar logic; no extra Zotero writes.
Task 10: Ruling: accept implementer deviation on item 6 — sidecar skip only for other-pass ok/no_candidates docs with ZERO datasets (so a dry run never blocks a later live pass) — cost if wrong: zero-data docs from a dry run are re-skipped too (harmless).
Task 10: fix round 1/5 (6+3 addressed, 0 open; commits 1f80f6c..de6b5e1)
Task 10: minor (deferred): undo stuck at exit 1 after partial failure on a re-run pass (restore_note 404 not swallowed); doc moved to later pass not replayed by original pass id; rerun_ids outside current --collection dropped silently; Pages column repeats same page (evidence not deduped in render); sync lag re-processes items before desktop sync
Task 10: observation: dry run 3 papers → acs, ahs, hud_fmr, lihtc, mls, hud_posh, saiz + unlisted "Census PUMS data"; hud_fmr/lihtc/saiz grep-only (likely false positives); all 3 "heading regex missed"; 75 s
Task 10: complete (commits dfff4be..de6b5e1, review clean)
Task 11: observation: tests/test_allowed_tools.py fails for skill ztp-ollama on branch base 512e471 too (pre-existing, out of scope)
Task 11: Ruling: drop mcp__zotpilot__* from allowed-tools (contract only accepts bare/wildcard, which pre-approves MCP writes the skill forbids); reword the body so it no longer names mcp__zotpilot__index_library — cost if wrong: indexing prompts for approval each time.
Task 11: fix round 1/5 (1 addressed, 0 open; commits c749562..c0a41a3)
Task 11: complete (commits de6b5e1..c0a41a3, review clean)
Task 12: NOT executed — Ruling (preflight): USER_REQUIRED live pass
## Final review (512e471..c0a41a3): With fixes — 0 Critical, 6 Important
Final: Ruling: grep-only datasets (model never confirmed) stay in sidecar, report and note (marked "keyword only") but produce NO Zotero tags; drop the `\bPSH\b` alias (matches "permanent supportive housing") — shared group library, report already labels grep-only as candidate false positives — cost if wrong: datasets the model misses but grep finds go untagged until a vocab/prompt fix or a later pass (user can flip this).
Final: Ruling: fix wave also covers v1 note title regex `(?:\[ZotPilot\] )?`, page/chunk dedupe in note+report, model_error items get no Zotero write (listed for re-run), DV needle normalisation (hyphens→spaces; all-caps needles case-sensitive + trailing \b), sidecar-based skip of docs with non-undone zotero_writes (sync lag), empty var: slug guard, restore_note/remove_tags 404 tolerance, url_params comment.
Final: Ruling: accept fix-wave deviation on sync-lag skip — docs whose latest status is write_conflict/write_error are retried on the next pass (not skipped) — cost if wrong: one extra retry per failed doc.
Final: fix wave re-review clean (c0a41a3..2422bf4; 149 passed)
