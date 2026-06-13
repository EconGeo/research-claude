---
name: obsidian-digest-sync
description: >
  Push weekly journal-digest insights (concepts, methods, datasets, research ideas)
  into an Obsidian vault as crosslinked notes. Runs after journal-digest Tier 2 has
  written digests/YYYY-MM-DD_digest.md and appended ideas.md. Five gated steps —
  Extract → Resolve → Preview → Push → Confirm — with no writes before explicit
  approval. Requires an Obsidian MCP server (recommended: obsidian-files / mcpvault,
  a filesystem server that needs no Obsidian app or plugins). Trigger on:
  "/obsidian-digest-sync", "sync the digest to Obsidian", "file the digest into my
  vault", "push the digest to my knowledge base".
---

# obsidian-digest-sync

Push weekly journal-digest insights into your Obsidian knowledge base as crosslinked notes.

This is the Tier-2 *filing* step of the journal-digest workflow: journal-digest writes
plain digest markdown; this skill turns it into a navigable, backlinked map of your
field and the data behind it.

## Trigger
Invoke after completing Tier 2 journal-digest analysis — after
`journal_digest/digests/YYYY-MM-DD_digest.md` has been written and
`journal_digest/ideas.md` has been updated with today's new entries.

## Pre-Conditions
Before starting, verify:
1. `journal_digest/digests/YYYY-MM-DD_digest.md` exists for today's date
2. `journal_digest/ideas.md` was updated this session (new entries under today's date header)
3. Obsidian MCP is connected (call `mcp__obsidian-files__list_all_tags` as a connectivity
   check — if it errors, stop and tell the user to confirm the `obsidian-files` (mcpvault)
   MCP server is registered in `.mcp.json` and pointed at the vault root)

## Vault Layout (configure for your vault)
Read the vault path and folder mapping from `.claude/state/obsidian-config.md`. This skill
assumes a knowledge-base area inside the vault with four subfolders. The defaults below
match the example config; adjust them to your vault's structure.

| Variable | Default path (relative to vault root) | Holds |
|----------|---------------------------------------|-------|
| `{concepts}` | `concepts/` | one note per theoretical concept |
| `{datasets}` | `datasets/`  | one note per dataset |
| `{ideas}`    | `ideas/`     | one note per research idea |
| `{weekly}`   | `weekly/`    | one synthesis note per digest run |

All note paths below are written as `{concepts}/{slug}.md`, etc. Substitute your
configured folders. If your knowledge base lives under a parent folder (e.g.
`research/concepts/`), set that prefix in `obsidian-config.md` and apply it throughout.

## Reference Files (in this skill's `references/` directory)
- `TAG-TAXONOMY.md` — your tag namespaces; check BEFORE creating any new `#concept/` or `#data/` tags
- `WEEKLY-NOTE-TEMPLATE.md` — weekly synthesis note format
- `CONCEPT-NOTE-TEMPLATE.md` — concept note format
- `IDEA-NOTE-TEMPLATE.md` — idea backlog entry format
- `DATASET-NOTE-TEMPLATE.md` — dataset note format

---

## Step 1: Extract

Read `journal_digest/digests/YYYY-MM-DD_digest.md` (today's analyzed digest).

For each paper in the digest, extract:
- **Concepts** (1–3 per paper): map to `#concept/` tags in TAG-TAXONOMY.md. If a concept doesn't match any existing tag, use the closest match; note the proposed new tag for the preview.
- **Methods** (1–2 per paper): map to `#method/` tags in TAG-TAXONOMY.md.
- **Datasets** (0–3 per paper): map to `#data/` tags in TAG-TAXONOMY.md. If a dataset is new, add it to the "new datasets" list.

Read today's new entries from `journal_digest/ideas.md`. For each new idea:
- Extract: research question (first sentence), key concepts, methods, datasets, potential journals.

Compile into an extraction table:
```
Paper 1: concepts=[concept-a, concept-b], methods=[method-a], datasets=[dataset-a, dataset-b]
Paper 2: concepts=[concept-c, concept-d], methods=[method-b], datasets=[dataset-c, dataset-b]
Idea 1: "Idea Title", concepts=[concept-a, concept-e], methods=[method-c], datasets=[dataset-a, dataset-d]
```

---

## Step 2: Resolve (reads only — no writes yet)

Call `mcp__obsidian-files__list_all_tags` to get all existing vault tags.

For each **unique concept** in the extraction table:
```
mcp__obsidian-files__read_note(path="{concepts}/{slug}.md")
→ returns content: note exists → plan "append evidence block"
→ errors (note not found): plan "create from CONCEPT-NOTE-TEMPLATE.md"
```

For each **new idea** from today's `ideas.md`:
```
mcp__obsidian-files__search_notes(query="{first 6 words of research question}")
→ result found with >70% title match: plan "skip (duplicate)" — note for preview
→ no match: plan "create from IDEA-NOTE-TEMPLATE.md"
```

For each **unique dataset** in the extraction table:
```
mcp__obsidian-files__read_note(path="{datasets}/{slug}.md")
→ returns content: note exists → plan "append paper to 'Papers Using This Dataset'"
→ errors (not found): plan "create stub from DATASET-NOTE-TEMPLATE.md"
```

Maintain a plan manifest:
```
CREATE  {weekly}/YYYY-MM-DD.md
CREATE  {concepts}/concept-slug.md    ← new concepts only
UPDATE  {concepts}/existing-slug.md   ← existing concepts
CREATE  {ideas}/idea-slug.md          ← new ideas
UPDATE  {datasets}/dataset-slug.md    ← existing datasets
CREATE  {datasets}/new-slug.md        ← new dataset stubs
SKIP    [idea title]                  ← duplicate ideas
```

---

## Step 3: Preview

Present the manifest to the user **before any writes**:

```
About to push to Obsidian (YYYY-MM-DD digest):

  CREATE  {weekly}/YYYY-MM-DD.md
  CREATE  {concepts}/concept-b.md   (new — 2 papers)
  UPDATE  {concepts}/concept-a.md   (2 new evidence blocks)
  CREATE  {ideas}/idea-title.md     (SEED)
  UPDATE  {datasets}/dataset-a.md   (1 new paper)
  CREATE  {datasets}/dataset-d.md   (new stub)

  SKIP (duplicate idea): "Idea title" — similar to existing idea-slug

Proceed? (y/n)
```

**Do not write anything until the user explicitly says "y" or "yes" or "proceed."**
If the user says "no" or "cancel", stop and log nothing.

---

## Step 4: Push (on approval only)

Write in this exact order (creates before updates; weekly note last):

### 4a. Create new concept notes
For each concept marked CREATE, write `{concepts}/{slug}.md` using CONCEPT-NOTE-TEMPLATE.md
(via `mcp__obsidian-files__write_note`). Populate the Definition section with a 2–3
sentence definition based on how the concept appeared in the digest papers. Add one
evidence block per paper that activated this concept.

### 4b. Append evidence blocks to existing concept notes
For each concept marked UPDATE, call:
```
mcp__obsidian-files__write_note(
  path="{concepts}/{slug}.md",
  mode="append",
  content="\n### YYYY-MM-DD (digest)\n- Author et al. (YEAR) — JOURNAL — [one-sentence finding]. Method: [[method-slug]]. Data: [[dataset-slug]].\n  → [[weekly-YYYY-MM-DD]]\n"
)
```
One append call per paper per concept. Do not rewrite the whole note.

### 4c. Create new idea notes
For each idea marked CREATE, write `{ideas}/{slug}.md` using IDEA-NOTE-TEMPLATE.md.
Populate all sections from the extraction (research question, motivation, datasets, journals).

### 4d. Create new dataset stubs
For each dataset marked CREATE, write `{datasets}/{slug}.md` using DATASET-NOTE-TEMPLATE.md.
Fill in Coverage, Variables, Temporal range, Geographic scope, Unit, Access, Format, Cost,
Enables, and Linked Concepts from your knowledge of the dataset. Add the citing paper under
"Papers Using This Dataset."

### 4e. Append papers to existing dataset notes
For each dataset marked UPDATE, call:
```
mcp__obsidian-files__write_note(
  path="{datasets}/{slug}.md",
  mode="append",
  content="\n- Author et al. (YEAR) — JOURNAL — [one-sentence description]\n  → added YYYY-MM-DD via digest\n"
)
```
Append to the "Papers Using This Dataset" section.

### 4f. Create weekly synthesis note (last)
Write `{weekly}/YYYY-MM-DD.md` using WEEKLY-NOTE-TEMPLATE.md.
The weekly note links to every concept, idea, and dataset note created or updated in steps
4a–4e. List only papers that appeared in the digest; each entry links to its concept and
dataset notes.

---

## Step 5: Confirm

After all writes complete:

1. Count and report:
   ```
   Obsidian sync complete:
   - 1 weekly synthesis note created
   - N concept notes (X new, Y updated)
   - M idea notes created
   - P dataset notes (Q new stubs, R updated)
   ```

2. Append to `SESSION_REPORT.md` (append only — do not overwrite):
   ```
   **Obsidian sync (YYYY-MM-DD):** Pushed digest — [N concepts, M ideas, P datasets, 1 weekly note]
   ```

---

## Edge Cases

**MCP connection fails at pre-condition check:**
Stop. Tell user: "Obsidian MCP is not responding. Confirm the `obsidian-files` (mcpvault)
MCP server is registered in `.mcp.json` and pointed at the vault root."

**Vault read returns an unexpected error (not a plain not-found):**
Note the path in the preview as "ERROR — could not resolve." Do not attempt to write that
note. Continue with others.

**All extracted ideas are duplicates:**
Show the preview with all items marked SKIP. Ask: "All ideas from this digest are similar to
existing notes. Still push the weekly synthesis note and concept/dataset updates? (y/n)"

**No new concepts or datasets (digest had no novel content):**
Show a minimal preview: "CREATE {weekly}/YYYY-MM-DD.md only (no new concepts, ideas, or
datasets this week). Proceed? (y/n)"
