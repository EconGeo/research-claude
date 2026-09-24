#!/usr/bin/env python3
"""check_refs.py — text criteria for scripts/check_fork.sh (stdlib, Python 3.9).

Each criterion scans the shipped tree and prints PASS/FAIL/WARN rows. A line ending in
'<!-- residue:prohibition -->' or '<!-- residue:historical -->' is exempt from
latex-residue, manuscript-model and deleted-things. A file whose first line is exactly
'<!-- residue:historical -->' is exempt in full. Vendored trees (zotpilot-skills/,
ai-audit/) are scanned for deleted-things only and reported as WARN.
"""
from __future__ import annotations
import argparse, fnmatch, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry_lib as rl

SHIP = ["agents", "skills", "rules", "references", "hooks", "templates", "seeds", "scripts"]
VENDORED = ["zotpilot-skills", "ai-audit"]
TEXT_SUFFIX = {".md", ".py", ".sh", ".json", ".R", ".qmd", ".yaml", ".yml", ".tex", ".bib", ""}
MARK = re.compile(r"<!-- residue:(prohibition|historical) -->\s*$")

LATEX_RESIDUE = re.compile(
    r"paper/tables|paper/figures|paper/sections|main\.tex|scripts/R/|00_master|"  # <!-- residue:prohibition -->
    r"\\cite[tp]?\{|\\input\{|\\label\{|\\ref\{|\\cref|latexmk|threeparttable|"  # <!-- residue:prohibition -->
    r"\\doublespacing|Bibliography_base|results_summary\.md|\.Rmd|bookdown|\\pause|\\only<")  # <!-- residue:prohibition -->
MANUSCRIPT_MODEL = [
    (re.compile(r"ggsave\("), "ggsave( — figures are fig- chunks"),  # <!-- residue:prohibition -->
    (re.compile(r"saveRDS\("), "saveRDS( — no intermediate objects outside scripts/acquire"),
    (re.compile(r"writeLines\([^)]*\.tex"), "writeLines to .tex"),
    (re.compile(r'dir\.create\("paper'), 'dir.create("paper'),  # <!-- residue:prohibition -->
]
DELETED_AGENTS = re.compile(r"\b(orchestrator|librarian-critic|librarian|guide-writer|rmd-coder-critic|domain-reviewer)\b", re.I)  # <!-- residue:prohibition -->
DELETED_SCRIPTS = re.compile(r"generate_(dashboard|html_report)\.py|(^|[^A-Za-z0-9_])guide/|clone .*clo-author|clo-author-upgrade")  # <!-- residue:prohibition -->
ABSENT_SKILLS = ["new-project", "review-paper", "audit-replication", "data-deposit", "audit-reproducibility",
                 "compile-latex", "prompt", "prompt-only", "interview-me", "research-ideation", "preregister",
                 "seven-pass-review", "devils-advocate", "promote-memory", "data-analysis", "obsidian-digest-sync"]
INV_RETIRED = {"INV-22"}
INV_REF = re.compile(r"\bINV-(\d{1,2})\b")
SLASH = re.compile(r"(?<![A-Za-z0-9_/.\-`])/([a-z][a-z0-9-]{2,})\b(?!/)")
# Slash tokens that are not skills: Claude Code built-ins, shell paths, this plan's own vocabulary.
SLASH_ALLOW = {"compact", "clear", "help", "init", "memory", "config", "permissions", "cost", "doctor", "status",
               "login", "logout", "model", "mcp", "agents", "hooks", "resume", "plan", "rewind", "export", "bug",
               "vim", "context", "loop", "schedule", "checkpoint", "tmp", "usr", "opt", "dev", "etc", "var", "bin",
               "home", "users", "private", "library", "applications", "system", "volumes", "workflows", "tasks",
               "artifacts", "code", "docs", "en", "api", "npm", "ajax", "libs", "gh-pages",
               # Verified false positives (2026-09-08, Task 0.5 red run) — not skill invocations:
               "detach",  # attach()/detach() R function pair in hooks/lint-scripts.sh
               "assumptions", "results", "proofs",
               # theory-output filename tails (bracket topic placeholder, name, dot-tex) in
               # skills/strategize/SKILL.md — path segments, not skill invocations
               "positioning",  # tail of the glob quality_reports/literature/*/positioning.md
               # (rules/permissions.md, rules/registry.yaml, skills/write/SKILL.md) — SLASH's
               # lookbehind excludes word chars/-/./`  but not `*`, so the glob's `*/positioning.md`
               # reads as a slash invocation. Fix round 1, Task 3b.8.
               "skill",  # scripts/registry_lib.py:137 "producer must be a /skill invocation" —
               # generic placeholder prose for "a slash-prefixed name", not a reference to a
               # skill literally named `skill` (no registry producer ever reads "/skill").
               # Fix round 2, Task 3b.8. A bare `/learn` candidate for this set was investigated
               # and rejected: skills/tools/SKILL.md:98 documents a real `/tools learn`
               # subcommand, so hooks/context-monitor.py's nudge text was corrected to say
               # `/tools learn` instead of being suppressed here.
               }
TOOLS_LINE = re.compile(r"^(allowed-)?tools:\s*(.*)$")

def shipped_files(root: Path, dirs):
    for d in dirs:
        p = root / d
        if not p.is_dir():
            continue
        for f in sorted(p.rglob("*")):
            if f.is_file() and f.suffix in TEXT_SUFFIX and ".git" not in f.parts:
                yield f

def lines_of(f: Path):
    try:
        text = f.read_text(errors="ignore")
    except OSError:
        return []
    lines = text.split("\n")
    if lines and lines[0].strip() == "<!-- residue:historical -->":
        return []
    return [(i + 1, ln) for i, ln in enumerate(lines) if not MARK.search(ln)]

def report(name, hits, warns=()):
    if hits:
        print(f"FAIL [{name}]")
        for h in hits: print(f"    {h}")
    else:
        print(f"PASS [{name}]")
    for w in warns: print(f"WARN [{name}] {w}")
    return 1 if hits else 0

def crit_latex_residue(root):
    hits = [f"{f.relative_to(root)}:{n}: {ln.strip()[:120]}"
            for f in shipped_files(root, SHIP) for n, ln in lines_of(f) if LATEX_RESIDUE.search(ln)]
    return report("latex-residue", hits)

def crit_manuscript_model(root):
    hits = []
    for f in shipped_files(root, SHIP):
        for n, ln in lines_of(f):
            for rx, why in MANUSCRIPT_MODEL:
                if rx.search(ln) and "scripts/acquire" not in ln:
                    hits.append(f"{f.relative_to(root)}:{n}: {why}")
    return report("manuscript-model", hits)

def crit_deleted_things(root):
    absent = re.compile(r"(?<![A-Za-z0-9_/.\-])/(" + "|".join(map(re.escape, ABSENT_SKILLS)) + r")(?![A-Za-z0-9_-])")
    inv22 = re.compile(r"\bINV-22\b")
    def scan(files):
        out = []
        for f in files:
            for n, ln in lines_of(f):
                if DELETED_AGENTS.search(ln) and "worker-critic" not in ln.lower():
                    out.append(f"{f.relative_to(root)}:{n}: deleted agent named")
                elif DELETED_SCRIPTS.search(ln):
                    out.append(f"{f.relative_to(root)}:{n}: deleted script/dir/upgrade path")
                elif absent.search(ln):
                    out.append(f"{f.relative_to(root)}:{n}: absent skill invoked")
                elif inv22.search(ln) and "RETIRED" not in ln and "retired" not in ln and not str(f).endswith("content-invariants.md"):
                    out.append(f"{f.relative_to(root)}:{n}: INV-22 cited as live")  # <!-- residue:prohibition -->
        return out
    hits = scan(shipped_files(root, SHIP))
    warns = scan(shipped_files(root, VENDORED))
    return report("deleted-things", hits, warns)

def crit_inv_refs(root):
    inv_file = root / "rules" / "content-invariants.md"
    defined = set(re.findall(r"\*\*INV-(\d{1,2})\.\*\*", inv_file.read_text())) if inv_file.exists() else set()
    hits = []
    for f in shipped_files(root, SHIP):
        if f == inv_file: continue
        for n, ln in lines_of(f):
            for m in INV_REF.finditer(ln):
                num = m.group(1); tag = f"INV-{num}"
                if num not in defined:
                    hits.append(f"{f.relative_to(root)}:{n}: {tag} is not defined")
                elif tag in INV_RETIRED and "RETIRED" not in ln and "retired" not in ln:
                    hits.append(f"{f.relative_to(root)}:{n}: {tag} is retired")
    return report("inv-refs", hits)

def crit_skill_refs(root):
    skills = set()
    for d in ["skills", "ai-audit/skills", "zotpilot-skills"]:
        p = root / d
        if p.is_dir():
            skills |= {c.name for c in p.iterdir() if c.is_dir() and (c / "SKILL.md").exists()}
    hits = []
    for f in shipped_files(root, SHIP):
        for n, ln in lines_of(f):
            for m in SLASH.finditer(ln):
                tok = m.group(1)
                if tok in skills or tok in SLASH_ALLOW: continue
                hits.append(f"{f.relative_to(root)}:{n}: /{tok} names no skill")
    return report("skill-refs", hits)

def crit_tool_name(root):
    hits = []
    for f in shipped_files(root, ["agents", "skills"]):
        for n, ln in lines_of(f):
            m = TOOLS_LINE.match(ln)
            if m and re.search(r"\bTask\b", m.group(2)):
                hits.append(f"{f.relative_to(root)}:{n}: Task in tools line (use Agent)")
    return report("tool-name", hits)

def crit_hooks_readme(root):
    readme = root / "hooks" / "README.md"
    hits = []
    if not readme.exists():
        return report("hooks-readme", ["hooks/README.md missing"])
    # Only rows whose first cell is a hook FILENAME are hook rows. The "Getting the
    # contract right" table below the hook table also leads with a backticked token —
    # an EVENT name — and without this the criterion hunts for a file called
    # hooks/PreToolUse and reports three hits that name nothing wrong.
    rows = [(n, e) for n, e in
            re.findall(r"^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|", readme.read_text(), re.M)
            if n.endswith((".py", ".sh"))]
    for name, event in rows:
        hook = root / "hooks" / name
        if not hook.exists():
            hits.append(f"hooks/README.md: row for {name} but hooks/{name} does not exist"); continue
        m = re.search(r"Hook Event:\s*([A-Za-z|]+)", hook.read_text(errors="ignore"))
        if not m:
            hits.append(f"hooks/{name}: no 'Hook Event: <Event>' line"); continue
        if event.split()[0].strip("*`") != m.group(1).split("|")[0]:
            hits.append(f"hooks/README.md: {name} row says '{event}', hook says '{m.group(1)}'")
        if event.lower().startswith("git"):
            hits.append(f"hooks/README.md: {name} is a git hook listed in the Claude hook table")
    return report("hooks-readme", hits)

def crit_hooks_wired_source(root):
    """hooks/README.md's table cell for Event states, per hook, whether it fires by direct
    settings.json wiring or 'via' another hook / the CLI. A directly-documented hook that
    seeds/settings.json never names is an unwired promise (hooks/README.md's own 'not a
    dormant feature' section, written after session-guard.py shipped exactly this way)."""
    readme = root / "hooks" / "README.md"
    settings = root / "seeds" / "settings.json"
    if not readme.exists():
        return report("hooks-wired-source", ["hooks/README.md missing"])
    if not settings.exists():
        return report("hooks-wired-source", ["seeds/settings.json missing"])
    settings_text = settings.read_text()
    rows = [(n, e) for n, e in
            re.findall(r"^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|", readme.read_text(), re.M)
            if n.endswith((".py", ".sh"))]
    hits = []
    for name, event in rows:
        if re.search(r"\bvia\b", event, re.I):
            continue
        if name not in settings_text:
            hits.append(f"hooks/{name}: README documents direct wiring ('{event.strip()}') "
                        f"but seeds/settings.json never names it")
    return report("hooks-wired-source", hits)

# ── artifact-paths (R-112) ──────────────────────────────────────────────────
# A path token under quality_reports/, with its placeholders: <x>, [x], {x} and {a,b} brace groups.
AP_TOKEN = re.compile(r"(?<![A-Za-z0-9_./-])quality_reports/(?:[A-Za-z0-9_.*/-]|<[^<>\s]*>|\[[^\[\]\s]*\]|\{[^{}\s]*\})*")
# Artifacts the registry deliberately does not declare. Each is written or read by a skill, hook or
# script, and nothing gates on it — so it can never contradict a `produces`. Add a row only with its
# reason; a skill path that CONTRADICTS a registry glob belongs in the skill, not here.
AP_ALLOW = {
    "quality_reports/pipeline_state.json":        "the state file itself (rules/logging.md)",
    "quality_reports/agent_dispatch.jsonl":       "the dispatch log (rules/logging.md)",
    "quality_reports/research_journal.md":        "narrative log written from the state (rules/logging.md)",
    "quality_reports/prose_number_allowlist.csv": "prose_number_check.py's per-project allowlist",
    "quality_reports/plans/*":                    "plans — records, not gated",
    "quality_reports/decisions/*":                "decision records — not gated",
    "quality_reports/research_spec_*.md":         "/discover interview output — not gated",
    "quality_reports/research_ideas_*.md":        "/discover ideate output — not gated (R-112)",
    "quality_reports/literature/*/zotero_seed.md": "/seed-papers output, read by /lit-position Step 0 — optional input",
    "quality_reports/pre_analysis_plan_*.md":     "/strategize pap output — strategy is scored from the critic report",
    "quality_reports/journal_recommendations_*.md": "/submit target output — not gated (R-112)",
    "quality_reports/quality_gate_*.md":          "/submit final gate summary — derived from `score --gate`",
    "quality_reports/referee_response_tracker.md": "/revise tracker — not gated (R-112)",
    "quality_reports/referee_response_*_*.md":    "/revise response letter — not gated",
    "quality_reports/reviews/replication_*_*.md": "/review --replicate report — records no score (R-106)",
    "quality_reports/claim_source_map_*.md":      "named only as retired INV-22's former artifact",
    "quality_reports/deposit_manifest_*.md":      "/submit deposit output — not gated (Phase 3.5)",
}

def _ap_expand(tok):
    """All concrete forms of a token: brace groups with commas expand; every other placeholder is `*`."""
    tok = tok.rstrip(".,;:)")
    m = re.search(r"\{([^{}]*,[^{}]*)\}", tok)
    if m:
        return [x for alt in m.group(1).split(",") for x in _ap_expand(tok[:m.start()] + alt + tok[m.end():])]
    return [re.sub(r"<[^<>]*>|\[[^\[\]]*\]|\{[^{}]*\}", "*", tok)]

def _ap_patterns(root):
    reg = rl.load_registry(root); files, dirs = set(), set()
    def walk(p):
        if p.get("type") == "path": files.add(p["glob"])
        if p.get("type") == "section" and p.get("file") != "manuscript": files.add(p["file"])
        for q in p.get("of") or []: walk(q)
    for e in reg["agents"].values():
        for p in (e.get("requires") or []) + (e.get("produces") or []): walk(p)
        dirs |= {w for w in (e.get("writes") or []) if str(w).startswith("quality_reports/")}
    return files, dirs

def crit_artifact_paths(root):
    """R-112's inverse check. The produces-path audit caught a MISSING declaration; it could not
    catch a skill naming a path its agent's registry entry does not declare, because the agent
    file being right let the skill's wrong path pass (/strategize, R-111). Every quality_reports/
    path in the shipped tree must match a registry glob, be a directory prefix of one, or be an
    AP_ALLOW artifact."""
    files, dirs = _ap_patterns(root)
    allow = set(AP_ALLOW)
    hits = []
    for f in shipped_files(root, SHIP):
        for n, ln in lines_of(f):
            for m in AP_TOKEN.finditer(ln):
                for t in _ap_expand(m.group(0)):
                    last = t.rsplit("/", 1)[-1]
                    if t.endswith("/") or "." not in last:          # a directory, or a dir-name stem
                        ok = any(p.startswith(t) or fnmatch.fnmatchcase(p[:len(t)], t)
                                 for p in files | dirs | allow)
                    else:
                        ok = any(fnmatch.fnmatchcase(t, p) for p in files | allow)
                    if not ok:
                        hits.append(f"{f.relative_to(root)}:{n}: {m.group(0).rstrip('.,;:)')} matches no registry glob")
    return report("artifact-paths", hits)

def crit_promote_vendor_warn(root):
    """`/promote` Step 2's `git status` pathspec never lists a VENDORED tree, so an edit made
    through a project's link into one is invisible to it — and the matching `sync-*.sh`'s
    `rm -rf` then destroys it with no warning ever surfacing (Phase 3.2). Every entry in
    VENDORED must get its own warning in skills/promote/SKILL.md, not just one of them."""
    f = root / "skills" / "promote" / "SKILL.md"
    if not f.exists(): return report("promote-vendor-warn", ["skills/promote/SKILL.md missing"])
    lines = f.read_text().splitlines()
    hits = [f"skills/promote/SKILL.md: no line warns about vendored tree {v!r}"
            for v in VENDORED if not any(v in ln and re.search(r"vendor", ln, re.I) for ln in lines)]
    return report("promote-vendor-warn", hits)

def crit_promote_register_check(root):
    """D-2, D-3 and D-18 were all the same shape: a mechanism correctly retired or introduced,
    whose purpose nobody re-homed, found only because a 2026-09-23 audit went looking three months
    later (Phase 4.3). `/promote` is the moment a change lands upstream for everyone — it must
    prompt whoever is promoting to check the divergence register, not just document that the
    register exists somewhere."""
    f = root / "skills" / "promote" / "SKILL.md"
    if not f.exists(): return report("promote-register-check", ["skills/promote/SKILL.md missing"])
    text = f.read_text()
    hits = []
    if "clo-author-divergences.md" not in text:
        hits.append("skills/promote/SKILL.md: does not reference docs/decisions/clo-author-divergences.md")
    if not re.search(r"before committ", text, re.I):
        hits.append("skills/promote/SKILL.md: no step ties the register to the upstream commit — "
                     "a bare mention of the file is not a checklist step")
    return report("promote-register-check", hits)

WRITE_CAPABLE_TOOLS = {"Write", "Edit", "NotebookEdit"}
NO_WRITE_MARKER = re.compile(r"do\s+not\s+(write|edit)\b", re.I)

def _agent_tools(root, name):
    """Resolve an agent's own .md file across both roster directories (rl.AGENT_DIRS) and
    return (path, full text, tools set) — or (None, "", set()) if no file exists anywhere."""
    for d in rl.AGENT_DIRS:
        f = root / d / f"{name}.md"
        if f.exists():
            text = f.read_text(errors="ignore")
            m = re.search(r"^(?:allowed-)?tools:\s*(.*)$", text, re.M)
            tools = {tok.strip() for tok in m.group(1).split(",")} if m else set()
            return f, text, tools
    return None, "", set()

def crit_writes_tools(root):
    """Phase 2.1 of the 2026-09-23 repair plan fixed nine agents by hand: declared to write a
    path in registry.yaml, with no Write/Edit tool and no instruction that the dispatching
    skill writes on their behalf, so the write silently never happened. This is the check that
    should have existed to catch it. An agent whose own .md file cannot be resolved is skipped —
    that is registry-complete's job (pipeline.py registry check), not this criterion's."""
    reg = rl.load_registry(root)
    hits = []
    for name, e in reg["agents"].items():
        writes = e.get("writes") or []
        if not writes:
            continue
        f, text, tools = _agent_tools(root, name)
        if f is None:
            continue
        if tools & WRITE_CAPABLE_TOOLS:
            continue
        if NO_WRITE_MARKER.search(text):
            continue
        hits.append(f"{f.relative_to(root)}: registry.yaml declares writes: {writes} but this "
                    f"agent has no write-capable tool and no 'do not write/edit' disclaimer")
    return report("writes-tools", hits)

CRITERIA = {
    "latex-residue": crit_latex_residue, "manuscript-model": crit_manuscript_model,
    "deleted-things": crit_deleted_things, "inv-refs": crit_inv_refs, "skill-refs": crit_skill_refs,
    "tool-name": crit_tool_name, "hooks-readme": crit_hooks_readme, "hooks-wired-source": crit_hooks_wired_source,
    "artifact-paths": crit_artifact_paths, "promote-vendor-warn": crit_promote_vendor_warn,
    "promote-register-check": crit_promote_register_check, "writes-tools": crit_writes_tools,
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--criterion", choices=sorted(CRITERIA) + ["all"], default="all")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    names = sorted(CRITERIA) if a.criterion == "all" else [a.criterion]
    rc = 0
    for n in names:
        rc |= CRITERIA[n](root)
    sys.exit(rc)

if __name__ == "__main__":
    main()
