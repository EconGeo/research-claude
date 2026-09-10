# D3 addendum: `lit-critic` returns as an independent cold-read critic

**Date:** 2026-09-08 · **Status:** Decided (spec v2 D-15, R-1)

**What D3 stands for.** D3 stands for the *collector*: the WebSearch-first agent named
`librarian` stays deleted, and `/lit-position` over the vendored ZotPilot skills is the
collector now — local Zotero index first, external search only for what the library lacks
(`rules/literature-search-order.md`).

**What was wrong.** The collector's paired critic — `librarian-critic` and its six review
categories — was deleted as collateral damage of cutting the collector, not because the
critic itself was WebSearch-first or otherwise unsound. A creator with no paired critic is
exactly the gap this repair closes.

**What changes.** `lit-critic` returns as an independent cold-read critic agent
(`agents/lit-critic.md`), dispatched by `/lit-position` after Step 5. It carries
`mcpServers: zotpilot` so it can run coverage queries (`search_topic`, `advanced_search`)
against the local index, but it never collects: no external search, no ingest, no edits to
the three artifacts it reviews.

**Why the weight stays 10.** The referees' Literature Positioning dimension only tests the
positioning paragraph after the strategy, the code, and the draft were already built on top
of the search it certified. A low weight on the gate that runs first and everything else
depends on undercounts its leverage — the weight was never about how much text the artifact
produces.

## What would invalidate this

A literature workflow ZotPilot cannot serve — e.g. a field whose corpus is not in Zotero and
cannot be ingested — would justify a different collector, but not a different critic
discipline: whatever collects still needs a paired critic that never collects.

## Related

- `docs/decisions/2026-09-08_cut-the-orchestration-graph.md` — D3's original cut.
- `agents/lit-critic.md`, `skills/lit-position/SKILL.md` Step 7.
