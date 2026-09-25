#!/usr/bin/env python3
"""check_seed_papers.py — /seed-papers: two search_topic calls with distinct queries reach the mock
(Step 3); the run halts at Step 4's wait, so no get_paper_details, no bibliography_base.bib /
zotero_seed.md write, no mock write. usage: check_seed_papers.py <transcript.jsonl> <mock-log>"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, calls = evallib.tool_uses(sys.argv[1]), evallib.mock_calls(sys.argv[2])
fails = []
queries = {a.get("query", "") for _, t, a, _ in calls if t == "search_topic"}
if len(queries) < 2: fails.append(f"fewer than two distinct search_topic queries reached the mock: {sorted(queries)}")
if any(t == "get_paper_details" for _, t, _, _ in calls): fails.append("get_paper_details was called before the user picked rows")
if any(k == "WRITE" for k, _, _, _ in calls): fails.append("a write reached the mock")
for n, x, _ in uses:
    fp = str(x.get("file_path", ""))
    if n in ("Write", "Edit", "MultiEdit") and (fp.endswith("bibliography_base.bib") or fp.endswith("zotero_seed.md")):
        fails.append(f"{n} wrote {fp} before the user replied"); break
if any(("bibliography_base.bib" in c or "zotero_seed.md" in c) and (">" in c or "tee" in c) for c in evallib.bash(uses)):
    fails.append("a Bash redirect wrote the seed files before the user replied")
evallib.finish("check_seed_papers", fails, f"tool_use: {len(uses)} · mock calls: {len(calls)} · search_topic queries: {len(queries)}")
