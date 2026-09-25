#!/usr/bin/env python3
"""check_ztp_research.py — /ztp-research halts at the candidate table: external search ran; no
ingest in the same turn (Phase 1 step 3 gate); no advanced_search dedup (the search result already
carries local_duplicate); no Phase 3 tool before the user's Y.
usage: check_ztp_research.py <transcript.jsonl> <mock-log>"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, calls = evallib.tool_uses(sys.argv[1]), evallib.mock_calls(sys.argv[2])
tools = [t for _, t, _, _ in calls]
fails = []
if "search_academic_databases" not in tools: fails.append("search_academic_databases never reached the mock")
if "ingest_by_identifiers" in tools: fails.append("ingest_by_identifiers ran in the same turn as the candidate table")
if "advanced_search" in tools: fails.append("a separate advanced_search dedup call ran (the skill says the search annotation is authoritative)")
for t in ("manage_tags", "manage_collections", "create_note", "index_library"):
    if t in tools: fails.append(f"Phase 3 tool {t} ran before the user replied Y"); break
if any(n in ("WebFetch", "WebSearch") for n, _, _ in uses): fails.append("a web tool ran — the canonical term is known; reconnaissance is not needed")
evallib.finish("check_ztp_research", fails, f"tool_use: {len(uses)} · mock calls: {len(calls)}")
