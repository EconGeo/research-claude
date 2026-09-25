#!/usr/bin/env python3
"""check_verify_claims.py — /verify-claims: Phase 0 checks .claude/agents/claim-verifier.md
exists before the dispatch; the claim-verifier Agent prompt never contains the draft-only
sentinel; the report lands in quality_reports/verify_claims_*.md OR (skills/verify-claims/SKILL.md
Phase 4, and audit §6's own eval-inputs row for this skill, name no report file at all — "return
the report and let the user decide") a Post-Flight Verification summary with an outcome appears
in the transcript text; draft.md is not modified. The first live run (2026-09-25) wrote no report
file and produced a "## Post-Flight Verification — draft.md ... Outcome: FAIL" text block instead
— that is the documented mechanism, not a defect.
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
report_file = list(proj.glob("quality_reports/verify_claims_*.md"))
texts = [b.get("text", "") for content in evallib._messages(sys.argv[1]) for b in content if isinstance(b, dict) and b.get("type") == "text"]
report_text = any(re.search(r"post-flight verification", t, re.I) and re.search(r"outcome", t, re.I) for t in texts)
if not report_file and not report_text: fails.append("no verification report was produced (neither quality_reports/verify_claims_*.md nor a Post-Flight Verification summary in the transcript)")
for n, x, _ in uses:
    if n in ("Write", "Edit", "MultiEdit") and str(x.get("file_path", "")).endswith("draft.md"):
        fails.append(f"{n} modified draft.md"); break
porc = subprocess.run(["git", "-C", str(proj), "status", "--porcelain"], capture_output=True, text=True).stdout
if re.search(r"^\s*M\s+draft\.md", porc, re.M): fails.append("draft.md is modified on disk")
evallib.finish("check_verify_claims", fails, f"tool_use: {len(uses)} · verifier dispatched: {disp is not None}")
