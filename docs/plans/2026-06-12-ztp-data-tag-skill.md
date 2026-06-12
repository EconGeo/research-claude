# ztp-data-tag Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in `ztp-data-tag` skill that backfills a structured "data used" field (datasets, variables, unit, timespan, access) onto papers already in the user's Zotero library, stored as both namespaced tags and a structured note.

**Architecture:** A research-claude *bridge skill* (a `SKILL.md`, no code) that the main Claude session runs against the ZotPilot MCP tools. It enumerates library items, reads each paper's indexed text, extracts the data schema, and writes it back to Zotero as tags + a note. It pilots one collection first, confirms before batch writes, and is resumable via a `data-tagged` marker tag. It lives in research-claude's own `skills/` (same home as `new-project-ztp`) so `apply.sh` installs it without touching the ZotPilot submodule.

**Tech Stack:** Markdown skill file (`SKILL.md` with YAML frontmatter); ZotPilot MCP tools (`mcp__zotpilot__*`); `apply.sh` (bash) installs it via its existing `skills/*` glob; README documents it.

**Why this design (decisions already made with the user):**
- **Storage = tags + note** (both). Tags drive filtering/Obsidian hubs; the note holds the full JSON record.
- **Scope = pilot one collection first**, then offer whole-library.
- **Batch/manual, user-opt-in.** It writes to the user's real library, so every batch is confirmed; users decide whether to run it at all.
- **Schema is identical to journal-digest's `Data` field** (`gather/writer.py` emits `{"datasets": [], "variables": [], "unit": "", "timespan": "", "access": ""}`), so digest-filed and library-backfilled papers are uniform. This skill adds one extra key, `source`, to flag extraction quality.

---

## Context the executor needs

- **Repo:** `~/Academic/research-claude` (a.k.a. `~/academic/research-claude`). Branch `main`, pushes to `EconGeo/research-claude`.
- **How skills install:** `apply.sh` copies `skills/*` into a target project's `.claude/skills/` (see the `RC_SKILLS` block near the end of `apply.sh`). So creating `skills/ztp-data-tag/SKILL.md` is enough for it to install — only the *descriptive* `--list` output and header comment in `apply.sh` need manual updates.
- **Skill conventions (match these):** see `skills/new-project-ztp/SKILL.md` (research-claude's own skill, references MCP tools by full `mcp__zotpilot__*` name) and `submodules/zotpilot/claude-skills/ztp-profile/SKILL.md` (shows `manage_tags` / `manage_collections` usage and the rule that `manage_tags(action="set")` is destructive — use `action="add"`).
- **ZotPilot MCP tools that exist** (confirm names against the live tool list at execution time): `get_index_stats`, `browse_library`, `advanced_search`, `get_paper_details`, `search_papers`, `get_passage_context`, `manage_tags`, `manage_collections`, `create_note`, `get_notes`, `index_library`. Write ops (`manage_tags`, `create_note`) require `zotero_api_key` + `zotero_user_id` (README Step 7).
- **You cannot unit-test a Claude skill.** "Verification" is: (a) structural checks on the markdown, (b) a real `apply.sh` install into a temp dir, (c) a manual pilot run against a real Zotero collection. Tasks below reflect that.

---

### Task 1: Create the `ztp-data-tag` skill file

**Files:**
- Create: `skills/ztp-data-tag/SKILL.md`

- [ ] **Step 1: Create the skill file with the full content below**

Create `skills/ztp-data-tag/SKILL.md` with exactly this content:

````markdown
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

For each new item (work in batches of 5):

1. Pull text with `mcp__zotpilot__get_paper_details(doc_id=...)`. For methods detail, use
   `mcp__zotpilot__search_papers` / `mcp__zotpilot__get_passage_context` scoped to that
   paper to surface the data/methods passages.
2. Set `source`: "full-text" if the indexed PDF text was available, else "abstract-only".
3. Fill the schema from the text. Datasets/variables are usually in the data/methods
   section. If nothing is identifiable, leave arrays empty and say so in the report.
4. Slugify tag values: lowercase, spaces → hyphens (e.g. `dataset:zillow-ztrax`,
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
- **Resumable.** The `data-tagged` marker is the idempotency key; always skip items that
  carry it unless the user asks for a refresh.
- **Flag weak extractions.** Mark `source: abstract-only` items so the user can review.
- **Same five shared keys as journal-digest** — keep `datasets/variables/unit/timespan/access`
  identical so Obsidian hubs and any parser treat digest and library papers uniformly.
````

- [ ] **Step 2: Verify the frontmatter is well-formed and the schema matches the digest**

Run:
```bash
cd ~/Academic/research-claude
# frontmatter present with name + description
head -3 skills/ztp-data-tag/SKILL.md | grep -q '^name: ztp-data-tag' && echo "name OK"
# the five shared keys appear and match the digest's writer.py field
grep -o '"datasets": \[\], "variables": \[\], "unit": "", "timespan": "", "access": ""' \
  skills/ztp-data-tag/SKILL.md && echo "schema-prefix matches digest"
grep -o '"datasets": \[\], "variables": \[\], "unit": "", "timespan": "", "access": ""' \
  submodules/journal-digest/gather/writer.py && echo "digest still uses same prefix"
```
Expected: `name OK`, and the same key-prefix string printed from BOTH the skill and `writer.py` (confirms schema parity).

- [ ] **Step 3: Verify the skill references only real ZotPilot tools**

Run:
```bash
cd ~/Academic/research-claude
grep -oE 'mcp__zotpilot__[a-z_]+' skills/ztp-data-tag/SKILL.md | sort -u
```
Expected: only names from this set — `get_index_stats, browse_library, advanced_search, get_paper_details, search_papers, get_passage_context, manage_tags, create_note, index_library`. If any other name appears, it's a typo — fix it. (At execution time, also eyeball the live tool list to confirm these exist in the connected ZotPilot.)

- [ ] **Step 4: Commit**

```bash
cd ~/Academic/research-claude
git add skills/ztp-data-tag/SKILL.md
git commit -m "feat: add ztp-data-tag skill to backfill the data field across the Zotero library

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Wire the skill into `apply.sh` descriptions

The install is automatic (the `skills/*` glob), so only the descriptive `--list` output and the header comment need updating.

**Files:**
- Modify: `apply.sh` (header comment block + `--list` research-claude skills section)

- [ ] **Step 1: Update the header comment**

In `apply.sh`, find:
```
#   From research-claude (own skills/):
#                      .claude/skills/new-project-ztp/
```
Replace with:
```
#   From research-claude (own skills/):
#                      .claude/skills/new-project-ztp/
#                      .claude/skills/ztp-data-tag/
```

- [ ] **Step 2: Update the `--list` output**

In `apply.sh`, find:
```
  echo "From research-claude (own skills/):"
  echo "  .claude/skills/new-project-ztp/  — ZotPilot setup after /new-project"
```
Replace with:
```
  echo "From research-claude (own skills/):"
  echo "  .claude/skills/new-project-ztp/  — ZotPilot setup after /new-project"
  echo "  .claude/skills/ztp-data-tag/     — backfill dataset/variable tags+notes across the Zotero library"
```

- [ ] **Step 3: Verify syntax and that a real install lands the skill**

Run:
```bash
cd ~/Academic/research-claude
bash -n apply.sh && echo "syntax OK"
TMP=$(mktemp -d)
bash apply.sh --project-dir "$TMP" >/dev/null 2>&1; echo "exit=$?"
ls -d "$TMP/.claude/skills/ztp-data-tag" && echo "skill installed"
bash apply.sh --list | grep -q "ztp-data-tag" && echo "listed in --list"
rm -rf "$TMP"
```
Expected: `syntax OK`, `exit=0`, the `ztp-data-tag` dir path printed + `skill installed`, and `listed in --list`.

- [ ] **Step 4: Commit**

```bash
cd ~/Academic/research-claude
git add apply.sh
git commit -m "chore: list ztp-data-tag in apply.sh install output

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Document the skill in the README

**Files:**
- Modify: `README.md` (the "Using the research pipeline" skills table + a cross-reference from the Obsidian/data section)

- [ ] **Step 1: Add the skill to the pipeline table**

In `README.md`, find the row:
```
| `/ztp-review` | Synthesize papers already in your library |
```
Add immediately after it:
```
| `/ztp-data-tag` | Backfill dataset/variable tags + a structured Data note onto papers already in your Zotero library (pilots one collection first) |
```

- [ ] **Step 2: Cross-reference it from the data-discovery section**

In `README.md`, in the Obsidian section, find the paragraph that begins:
```
**Each note records the data behind the paper.**
```
At the END of that same paragraph (after "...data discovery, not just literature discovery."), append:
```
 To do the same for papers **already** in your library — not just newly digested ones — run `/ztp-data-tag`, which extracts the same fields and writes them back to Zotero as tags + a Data note (piloting one collection first).
```

- [ ] **Step 3: Verify both references render and resolve**

Run:
```bash
cd ~/Academic/research-claude
grep -n "ztp-data-tag" README.md
```
Expected: at least 2 lines — the table row and the cross-reference.

- [ ] **Step 4: Commit and push**

```bash
cd ~/Academic/research-claude
git add README.md
git commit -m "docs(readme): document /ztp-data-tag (library data-field backfill)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push origin main
git status -sb | head -1   # expect: ## main...origin/main (in sync)
```

---

### Task 4: Manual pilot verification (the real test)

A Claude skill can't be unit-tested — it's verified by running it. Do this in a project that has ZotPilot configured with write credentials and an indexed library.

- [ ] **Step 1: Trigger the skill on a small collection**

In a ZotPilot-enabled project, invoke `/ztp-data-tag` (or say "tag my library with the datasets they use"). Confirm it:
- checks preconditions (errors clearly if write creds are missing),
- lists collections and asks you to pick ONE (does not auto-run the whole library),
- shows a batch preview table and waits for approval before writing.

Pick a small collection (≤5 papers) for the pilot.

- [ ] **Step 2: Verify the writes landed in Zotero**

After approving the batch, in Zotero (or via `mcp__zotpilot__browse_library` / `get_notes`), confirm each processed item has:
- `dataset:*` and/or `var:*` tags (or just `data-tagged` if no data was identifiable),
- the `data-tagged` marker tag,
- a "Data (auto-extracted)" note containing valid JSON with the six keys.

- [ ] **Step 3: Verify idempotency / resumability**

Run `/ztp-data-tag` again on the SAME collection. Expected: it reports the items already carry `data-tagged` and skips them (no duplicate tags or notes).

- [ ] **Step 4: Verify undo works**

On one test item, remove the `data-tagged`, `dataset:*`, `var:*` tags via `mcp__zotpilot__manage_tags(action="remove")` and delete its Data note. Confirm a re-run then re-processes only that item.

- [ ] **Step 5: Note results**

Record in the session report: how many papers got datasets vs came back empty, how many were `abstract-only`, and whether extraction quality justifies a whole-library run. (No code commit — this is a findings note.)

---

## Self-Review

**Spec coverage:**
- Storage = tags + note → Task 1 Step 5 (both writes). ✓
- Pilot one collection first → Task 1 Steps 1, 6, 7 (pilot, pause, then opt-in whole-library). ✓
- Batch/manual, user-opt-in → Task 1 Steps 4 & 6 (USER_REQUIRED gates), Rules section. ✓
- Schema parity with journal-digest → Task 1 Step 2 verification greps both files. ✓
- Resumable → `data-tagged` marker (Task 1 Steps 2, 5; Task 4 Step 3). ✓
- Installs via apply.sh → Task 2 (auto-glob + descriptive update + install test). ✓
- Documented → Task 3 (pipeline table + data-section cross-reference). ✓
- Real verification → Task 4 (manual pilot, idempotency, undo). ✓

**Placeholder scan:** No "TBD"/"handle edge cases"/"similar to" — the full SKILL.md content is inline; every apply.sh and README edit shows exact before/after text and exact verify commands. ✓

**Consistency:** Tag names (`dataset:`, `var:`, `data-tagged`), tool names (`mcp__zotpilot__*`), and the six schema keys are used identically across Tasks 1–4. The five shared keys match `writer.py`'s emitted field; `source` is the one documented addition. ✓

---

## Execution note

The user asked to **execute this in a separate session**. When you start that session: read this plan, then use **superpowers:subagent-driven-development** (fresh subagent per task, review between) or **superpowers:executing-plans** (inline, batched with checkpoints). Tasks 1–3 are pure repo edits and can run anywhere; **Task 4 must run in a project with ZotPilot configured + write credentials + an indexed library.**
