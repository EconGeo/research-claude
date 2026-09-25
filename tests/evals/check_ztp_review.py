#!/usr/bin/env python3
"""check_ztp_review.py — /ztp-review stays local-first: search_topic before search_papers, get_notes
called (Step 5), no search_academic_databases, no writes.
usage: check_ztp_review.py <transcript.jsonl> <mock-log>"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, calls = evallib.tool_uses(sys.argv[1]), evallib.mock_calls(sys.argv[2])
tools = [t for _, t, _, _ in calls]
fails = []
def idx(t): return tools.index(t) if t in tools else None
if idx("search_topic") is None: fails.append("search_topic never reached the mock")
elif idx("search_papers") is not None and idx("search_papers") < idx("search_topic"): fails.append("search_papers ran before search_topic")
if "get_notes" not in tools: fails.append("get_notes was never called (Step 5: note integration)")
if "search_academic_databases" in tools: fails.append("search_academic_databases was called — the review must stay local")
if any(k == "WRITE" for k, _, _, _ in calls): fails.append("a write reached the mock")
evallib.finish("check_ztp_review", fails, f"tool_use: {len(uses)} · mock calls: {len(calls)}")
