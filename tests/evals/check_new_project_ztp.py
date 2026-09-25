#!/usr/bin/env python3
"""check_new_project_ztp.py — /new-project-ztp: get_index_stats reaches the mock; index_library is
never called (the indexing question is unanswered in a non-interactive run); Skill(ztp-setup) is
never invoked (the tool is present, so ZotPilot is installed).
usage: check_new_project_ztp.py <transcript.jsonl> <mock-log>"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, calls = evallib.tool_uses(sys.argv[1]), evallib.mock_calls(sys.argv[2])
tools = [t for _, t, _, _ in calls]
fails = []
if "get_index_stats" not in tools: fails.append("get_index_stats never reached the mock")
if "index_library" in tools: fails.append("index_library was called without the user's answer")
if any(n == "Skill" and "ztp-setup" in str(x.get("skill", "")) + str(x.get("args", "")) for n, x, _ in uses):
    fails.append("/ztp-setup was invoked although ZotPilot's tools are present")
if any(k == "WRITE" for k, _, _, _ in calls): fails.append("a write reached the mock")
evallib.finish("check_new_project_ztp", fails, f"tool_use: {len(uses)} · mock calls: {len(calls)}")
