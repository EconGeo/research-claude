---
name: new-project-ztp
description: >
  ZotPilot setup step for new research projects — run when starting a project to embed
  your Zotero library into ChromaDB so /lit-position (and the optional /seed-papers) can search it.
  Trigger on: "set up ZotPilot", "embed my Zotero library", "configure ZotPilot for
  this project", or any mention of wanting local library search before literature review.
  Run at project start, BEFORE /seed-papers or /lit-position.
allowed-tools: Read,Write,Edit,Bash
---

# ZotPilot Project Setup

This skill configures ZotPilot for a new research project, enabling semantic search
of your Zotero library during literature review. Run once per project at project start,
before `/seed-papers` or `/lit-position`.

---

## Step 1: Check if ZotPilot is already configured

Ask: **"Is ZotPilot already set up on this machine?"**

If YES → skip to Step 3 (library indexing check).  
If NO → proceed to Step 2.

If the user isn't sure: check whether `mcp__zotpilot__get_index_stats` is available. If the
tool is present, ZotPilot is installed. If absent, it needs to be installed first.

---

## Step 2: Run /ztp-setup

Invoke the `/ztp-setup` skill to walk through full ZotPilot installation:
- micromamba env setup
- zotpilot package install (EconGeo fork with BBT 7+ and group library support)
- MCP server registration in project `.mcp.json`
- Zotero API key configuration

After `/ztp-setup` completes, continue to Step 3.

---

## Step 3: Check library index status

Run `mcp__zotpilot__get_index_stats` to check how many papers are indexed.

Report to the user:
- **Indexed:** N papers
- **Unindexed:** M papers

If M > 0 (unindexed papers exist), ask:
> "Your Zotero library has M papers not yet indexed. Index them now? This takes ~15–20 min
> for 300 papers (Gemini free tier). You can also skip and index later with `/ztp-setup`."

If YES → run `mcp__zotpilot__index_library` with default settings.  
If NO → continue; remind user to run `/ztp-setup` → index before using `/seed-papers`.

---

## Step 4: Record status in CLAUDE.md

Append (or update) the `## Tools` section in the project's `CLAUDE.md`:

```markdown
## Tools

| Tool | Status |
|------|--------|
| ZotPilot | Configured — N papers indexed |
| Zotero library indexed | Yes / Partial (N of M) / No |
```

If `## Tools` already exists, update in place. If not, append after `## Current Project State`.

---

## Step 5: Confirm next steps

Tell the user:
> "ZotPilot is ready. `/lit-position` searches the Zotero index directly; it runs in the main
> session, so it holds ZotPilot access. Optionally run `/seed-papers [topic]` first: you confirm
> which library papers are anchors, and `/lit-position` reads that confirmed set from
> `quality_reports/literature/<project>/zotero_seed.md` before it searches."

---

## Notes

- `/seed-papers` is optional. It writes `quality_reports/literature/<project>/zotero_seed.md`
  (the user-confirmed anchor set, which `/lit-position` Step 0 reads) and `bibliography_base.bib`
  at the project root (a BibTeX convenience export that nothing in this pipeline reads — the
  manuscript's bibliography is `references.bib`, and nothing copies between the two)
- `/lit-position` reads the Zotero index and, when present, `zotero_seed.md`; it never reads a
  `.bib` — Zotero is the source of truth for what has been read
- ZotPilot is registered in project `.mcp.json` by default (not globally)
- To add it globally: `claude mcp add -g zotpilot -- /path/to/zotpilot mcp serve`
