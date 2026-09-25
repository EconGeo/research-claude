#!/usr/bin/env python3
"""check_ztp_profile.py — /ztp-profile maps the taxonomy (browse_library overview/collections/tags)
and detects orphans (advanced_search) before any manage_* call; halts at Step 6, so no write
reaches the mock; action="set" never appears.
usage: check_ztp_profile.py <transcript.jsonl> <mock-log>"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, calls = evallib.tool_uses(sys.argv[1]), evallib.mock_calls(sys.argv[2])
fails = []
first_write = next((i for i, (_, t, _, _) in enumerate(calls) if t in ("manage_tags", "manage_collections")), len(calls))
views = {a.get("view") for _, t, a, _ in calls[:first_write] if t == "browse_library"}
for v in ("overview", "collections", "tags"):
    if v not in views: fails.append(f"browse_library(view={v!r}) did not run before any manage_* call")
if not any(t == "advanced_search" for _, t, _, _ in calls[:first_write]): fails.append("advanced_search (orphan detection) did not run before any manage_* call")
if any(k == "WRITE" for k, _, _, _ in calls): fails.append("a write reached the mock without the user's approval")
if any(t == "manage_tags" and a.get("action") == "set" for _, t, a, _ in calls): fails.append("manage_tags action='set' was attempted")
evallib.finish("check_ztp_profile", fails, f"tool_use: {len(uses)} · mock calls: {len(calls)} · views: {sorted(v for v in views if v)}")
