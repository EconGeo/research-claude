# Literature Search Order (Non-Negotiable)

**Before any `WebSearch` / `WebFetch` for literature, search the local Zotero index first.**
Order: ZotPilot `search_topic` → `advanced_search` → `search_papers`, then web (Semantic
Scholar / CrossRef / WebSearch). Any paper found online but not in Zotero is a **gap** —
ingest it via ZotPilot `ingest_by_identifiers`.

Applies to the librarian agent, the `/discover` skill, and any inline literature work.
Rationale: local-first avoids redoing work already done and keeps Zotero as the single
source of truth for what has been read and annotated.
