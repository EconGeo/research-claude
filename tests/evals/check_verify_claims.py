#!/usr/bin/env python3
"""check_verify_claims.py — /verify-claims: Phase 0 checks .claude/agents/claim-verifier.md
exists before the dispatch; the claim-verifier Agent prompt never contains the draft-only
sentinel; the report lands in quality_reports/verify_claims_*.md; draft.md is not modified.
usage: check_verify_claims.py <transcript.jsonl> <project-dir> <sentinel>"""
import re, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj, sentinel = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
fails = []
disp = evallib.agent(uses, "claim-verifier")
pre = evallib.first(uses, lambda n, a: "claim-verifier.md" in (str(a.get("file_path", "")) + str(a.get("command", "")) + str(a.get("pattern", "")) + str(a.get("path", ""))))
if disp is None: fails.append("claim-verifier was never dispatched")
else:
    if pre is None or pre > disp: fails.append("the agent file .claude/agents/claim-verifier.md was not checked before the dispatch (Phase 0)")
    if sentinel in str(uses[disp][1].get("prompt", "")): fails.append("the verifier's prompt contains draft text (the sentinel) — the fork must not see the draft")
if not list(proj.glob("quality_reports/verify_claims_*.md")): fails.append("no quality_reports/verify_claims_*.md report was written")
for n, x, _ in uses:
    if n in ("Write", "Edit", "MultiEdit") and str(x.get("file_path", "")).endswith("draft.md"):
        fails.append(f"{n} modified draft.md"); break
porc = subprocess.run(["git", "-C", str(proj), "status", "--porcelain"], capture_output=True, text=True).stdout
if re.search(r"^\s*M\s+draft\.md", porc, re.M): fails.append("draft.md is modified on disk")
evallib.finish("check_verify_claims", fails, f"tool_use: {len(uses)} · verifier dispatched: {disp is not None}")
