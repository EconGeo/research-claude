#!/usr/bin/env python3
"""check_single_manuscript.py — core rule 1 in the shipped tree (stdlib, Python 3.9).

One manuscript holds all estimation, so no shipped R code may `source(` a script or
`readRDS(` a results/output file. Scanned: every shipped `.R`, `.R.txt` (whole file), the
`{r}` chunks of every Quarto (or R Markdown) file, and the `r`/`{r ...}` fences of every `.md`. R comments
are not code. A line carrying `residue:prohibition` (a deliberate example of what not to
write) is skipped. Exit 1 on any hit.
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

SHIP = ["agents", "skills", "rules", "references", "hooks", "templates", "seeds", "scripts"]
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})\s*(\S*)")
R_INFO_RE = re.compile(r"^(r|\{r\b.*\}?)$", re.I)
BAD = [(re.compile(r"(?<![\w.])source\s*\("), "source("),
       (re.compile(r"(?<![\w.])readRDS\s*\([^)]*(output|results)", re.I), "readRDS of a results file")]
MARK = "residue:prohibition"

def strip_comment(line: str) -> str:
    """Drop an R comment: the first `#` outside a string literal."""
    quote = None; esc = False
    for i, ch in enumerate(line):
        if esc: esc = False; continue
        if ch == "\\": esc = True; continue
        if quote:
            if ch == quote: quote = None
        elif ch in "\"'`": quote = ch
        elif ch == "#": return line[:i]
    return line

def code_lines(path: Path):
    """Yield (lineno, text) for the R code of one file."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    name = path.name
    if name.endswith(".R") or name.endswith(".R.txt"):
        yield from enumerate(lines, 1); return
    in_fence = False; is_r = False; marker = ""
    for n, line in enumerate(lines, 1):
        m = FENCE_RE.match(line)
        if not in_fence and m:
            in_fence, marker, is_r = True, m.group(1), bool(R_INFO_RE.match(m.group(2)))
            continue
        if in_fence and m and m.group(1)[0] == marker[0] and len(m.group(1)) >= len(marker) and not m.group(2):
            in_fence = False; continue
        if in_fence and is_r:
            yield n, line

def wanted(path: Path) -> bool:
    n = path.name
    return n.endswith((".R", ".R.txt", ".qmd", ".Rmd", ".md"))  # scans R Markdown, never ships it <!-- residue:prohibition -->

def check(root: Path, dirs=SHIP):
    hits = []
    for d in dirs:
        base = root / d
        if not base.is_dir(): continue
        for f in sorted(base.rglob("*")):
            if not f.is_file() or ".git" in f.parts or not wanted(f): continue
            for n, line in code_lines(f):
                if MARK in line: continue
                code = strip_comment(line)
                for rx, label in BAD:
                    if rx.search(code):
                        hits.append(f"{f.relative_to(root)}:{n}: {label} — {line.strip()}")
    return hits

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    a = ap.parse_args(argv)
    hits = check(Path(a.root))
    if hits:
        print("FAIL [single-manuscript] shipped R code sources a script or reads a results file (core rule 1):")
        for h in hits: print(f"    {h}")
        return 1
    print("PASS [single-manuscript]")
    return 0

if __name__ == "__main__":
    sys.exit(main())
