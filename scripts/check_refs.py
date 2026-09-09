#!/usr/bin/env python3
"""check_refs.py — text criteria for scripts/check_fork.sh (stdlib, Python 3.9).

Each criterion scans the shipped tree and prints PASS/FAIL/WARN rows. A line ending in
'<!-- residue:prohibition -->' or '<!-- residue:historical -->' is exempt from
latex-residue, manuscript-model and deleted-things. A file whose first line is exactly
'<!-- residue:historical -->' is exempt in full. Vendored trees (zotpilot-skills/,
ai-audit/) are scanned for deleted-things only and reported as WARN.
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

SHIP = ["agents", "skills", "rules", "references", "hooks", "templates", "seeds", "scripts"]
VENDORED = ["zotpilot-skills", "ai-audit"]
TEXT_SUFFIX = {".md", ".py", ".sh", ".json", ".R", ".qmd", ".yaml", ".yml", ".tex", ".bib", ""}
MARK = re.compile(r"<!-- residue:(prohibition|historical) -->\s*$")

LATEX_RESIDUE = re.compile(
    r"paper/tables|paper/figures|paper/sections|main\.tex|scripts/R/|00_master|"
    r"\\cite[tp]?\{|\\input\{|\\label\{|\\ref\{|\\cref|latexmk|threeparttable|"
    r"\\doublespacing|Bibliography_base|results_summary\.md|\.Rmd|bookdown|\\pause|\\only<")
MANUSCRIPT_MODEL = [
    (re.compile(r"ggsave\("), "ggsave( — figures are fig- chunks"),
    (re.compile(r"saveRDS\("), "saveRDS( — no intermediate objects outside scripts/acquire"),
    (re.compile(r"writeLines\([^)]*\.tex"), "writeLines to .tex"),
    (re.compile(r'dir\.create\("paper'), 'dir.create("paper'),
]
DELETED_AGENTS = re.compile(r"\b(orchestrator|librarian-critic|librarian|guide-writer|rmd-coder-critic|domain-reviewer)\b", re.I)
DELETED_SCRIPTS = re.compile(r"generate_(dashboard|html_report)\.py|(^|[^A-Za-z0-9_])guide/|clone .*clo-author|clo-author-upgrade")
ABSENT_SKILLS = ["new-project", "review-paper", "audit-replication", "data-deposit", "audit-reproducibility",
                 "compile-latex", "prompt", "prompt-only", "interview-me", "research-ideation", "preregister",
                 "seven-pass-review", "devils-advocate", "promote-memory", "data-analysis"]
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
               "strong", "div",  # </strong>, </div> — HTML closing tags in rules/html-dashboard.md
               "detach",  # attach()/detach() R function pair in hooks/lint-scripts.sh
               "assumptions", "results", "proofs",
               # theory-output filename tails (bracket topic placeholder, name, dot-tex) in
               # skills/strategize/SKILL.md — path segments, not skill invocations
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
    absent = re.compile(r"(?<![A-Za-z0-9_/.\-])/(" + "|".join(map(re.escape, ABSENT_SKILLS)) + r")\b")
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
                    out.append(f"{f.relative_to(root)}:{n}: INV-22 cited as live")
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
    rows = re.findall(r"^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|", readme.read_text(), re.M)
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

CRITERIA = {
    "latex-residue": crit_latex_residue, "manuscript-model": crit_manuscript_model,
    "deleted-things": crit_deleted_things, "inv-refs": crit_inv_refs, "skill-refs": crit_skill_refs,
    "tool-name": crit_tool_name, "hooks-readme": crit_hooks_readme,
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
