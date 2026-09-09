#!/usr/bin/env python3
"""check_paths.py — D-4 path gate for check_fork.sh (stdlib, Python 3.9).

Every pipeline path in a shipped file must be `.claude/`-prefixed and resolve through the
table in RESOLVE. Bare pipeline paths (templates/X, skills/X, ...) fail unless they are in
the project-level exempt set. --list prints the full inventory (Stage 3 uses it).
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

SHIP = ["agents", "skills", "rules", "references", "hooks", "templates", "seeds", "scripts"]
VENDORED = ["zotpilot-skills", "submodules/ai-audit"]
RESOLVE = {
    "skills":     ["skills", "submodules/ai-audit/skills", "zotpilot-skills"],
    "agents":     ["agents", "submodules/ai-audit/agents"],
    "rules":      ["rules", "submodules/ai-audit/rules"],
    "references": ["references"],
    "templates":  ["templates"],
    "scripts":    ["scripts"],
    "hooks":      ["hooks"],
}
EXEMPT_PREFIX = ("data/", "quality_reports/", "talks/", "explorations/", "scripts/acquire/",
                 "master_supporting_docs/", ".claude/state/", ".claude/settings", ".claude/pipeline.lock")
EXEMPT_EXACT = {"templates/quarto-preamble.tex", "templates/word-reference.docx",
                "templates/ai-use-log.md", "templates/apa.csl"}
# A path token: optional .claude/ prefix, one of the pipeline dirs, then a file-ish tail.
PATH_RE = re.compile(r"(?<![A-Za-z0-9_./-])((?:\.claude/)?(?:skills|agents|rules|references|templates|scripts|hooks)/[A-Za-z0-9_./-]*[A-Za-z0-9_])")
MARK = re.compile(r"<!-- residue:(prohibition|historical) -->\s*$")

def files(root, dirs):
    for d in dirs:
        p = root / d
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix in {".md", ".py", ".sh", ".json", ".R", ".qmd", ".yaml", ".tex"} and ".git" not in f.parts:
                    yield f

def shipped_scripts(root):
    p = root / "scripts" / "SHIPPED"
    return {ln.strip() for ln in p.read_text().splitlines() if ln.strip()} if p.exists() else set()

def resolve(root, ref, shipped):
    tail = ref[len(".claude/"):]
    top, _, rest = tail.partition("/")
    for base in RESOLVE.get(top, []):
        if (root / base / rest).exists():
            if top == "scripts" and rest not in shipped:
                return False
            return True
    return False

def check(root, dirs, warn=False):
    shipped = shipped_scripts(root)
    rows = []
    for f in files(root, dirs):
        text = f.read_text(errors="ignore")
        lines = text.split("\n")
        if lines and lines[0].strip() == "<!-- residue:historical -->":
            continue
        for i, ln in enumerate(lines, 1):
            if MARK.search(ln): continue
            for m in PATH_RE.finditer(ln):
                ref = m.group(1)
                if ref.startswith(EXEMPT_PREFIX) or ref in EXEMPT_EXACT: continue
                # a skill's own relative path is NOT exempt (D-4: rewrite skill-relative references too)
                if ref.startswith(".claude/"):
                    status = "ok" if resolve(root, ref, shipped) else "UNRESOLVED"
                else:
                    status = "UNPREFIXED"
                rows.append((str(f.relative_to(root)), i, ref, status))
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True); ap.add_argument("--list", action="store_true")
    a = ap.parse_args(); root = Path(a.root).resolve()
    rows = check(root, SHIP)
    bad = [r for r in rows if r[3] != "ok"]
    if a.list:
        for r in rows: print(f"{r[0]}:{r[1]}: {r[2]} -> {r[3]}")
        print(f"total={len(rows)} unresolved={sum(r[3]=='UNRESOLVED' for r in rows)} unprefixed={sum(r[3]=='UNPREFIXED' for r in rows)}")
    if bad:
        print("FAIL [path-resolves]")
        for r in bad: print(f"    {r[0]}:{r[1]}: {r[2]} ({r[3]})")
    else:
        print("PASS [path-resolves]")
    for r in check(root, VENDORED):
        if r[3] != "ok": print(f"WARN [path-resolves] vendored {r[0]}:{r[1]}: {r[2]} ({r[3]})")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
