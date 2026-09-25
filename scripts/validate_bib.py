#!/usr/bin/env python3
"""validate_bib.py — `/tools validate-bib` as a script (audit 2026-09-15 P5, tools row).

Cross-references every citation key in the declared manuscript and `talks/*.qmd` against the
.bib file the manuscript YAML's `bibliography:` field names. Quarto cross-reference prefixes
(`@fig-`, `@tbl-`, `@eq-`, `@sec-`, …) are not citations and are excluded; so are e-mail
addresses (an `@` preceded by a word character).

Exit 0: MISSING and DUPLICATE both empty (UNUSED is informational — Zotero is the source of
truth for what has been read, and the .bib is exported from it, so an uncited entry is normal
mid-draft). Exit 1: a MISSING or DUPLICATE key. Exit 2: cannot run (no manuscript, no .bib).

usage: validate_bib.py [--root DIR] [--manuscript FILE]
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

CROSSREF = ("fig", "tbl", "eq", "sec", "thm", "lem", "cor", "def", "lst", "exm", "prp", "nte", "tip", "wrn", "imp", "cnj", "exr", "sol", "rem")
CITE = re.compile(r"(?<![A-Za-z0-9_.])-?@\{?([A-Za-z][A-Za-z0-9_:.-]*[A-Za-z0-9])")
ENTRY = re.compile(r"^@[A-Za-z]+\s*\{\s*([^,\s]+)", re.M)


def declared_manuscript(root: Path) -> Path:
    claude = root / "CLAUDE.md"
    if not claude.exists(): sys.exit("validate_bib: CLAUDE.md not found — declare `manuscript: <file>.qmd` in it")
    hits = re.findall(r"^manuscript:\s*(\S+\.qmd)\s*$", claude.read_text(), re.M)
    if len(hits) != 1: sys.exit(f"validate_bib: CLAUDE.md must declare exactly one `manuscript:` line (found {len(hits)})")
    m = root / hits[0]
    if not m.exists(): sys.exit(f"validate_bib: declared manuscript {hits[0]} does not exist")
    return m


def bib_from_yaml(ms: Path) -> str:
    text = ms.read_text()
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    front = m.group(1) if m else ""
    b = re.search(r"^bibliography:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", front, re.M)
    return b.group(1).strip() if b else "references.bib"


def cited_keys(paths) -> set:
    keys = set()
    for p in paths:
        for k in CITE.findall(p.read_text()):
            if k.split("-", 1)[0] in CROSSREF and "-" in k: continue
            keys.add(k)
    return keys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--manuscript", type=Path)
    a = ap.parse_args(argv)
    root = a.root.resolve()
    ms = (root / a.manuscript) if a.manuscript else declared_manuscript(root)
    bib_name = bib_from_yaml(ms)
    bib = (ms.parent / bib_name) if not Path(bib_name).is_absolute() else Path(bib_name)
    if not bib.is_file():
        print(f"validate_bib: {bib_name} (from `bibliography:` in {ms.name}) not found at {bib}"); return 2
    sources = [ms] + sorted((root / "talks").glob("*.qmd")) if (root / "talks").is_dir() else [ms]
    cited = cited_keys(sources)
    entries = ENTRY.findall(bib.read_text())
    keys = set(entries)
    dups = sorted({k for k in entries if entries.count(k) > 1})
    missing = sorted(cited - keys); unused = sorted(keys - cited)
    print(f"validate_bib: {len(sources)} source(s) · {len(cited)} cited key(s) · {bib_name}: {len(keys)} entr{'y' if len(keys)==1 else 'ies'}")
    def block(title, ks): print(title); print("\n".join("  " + k for k in ks) if ks else "  (none)")
    block("MISSING (cited, not in .bib):", missing)
    block("UNUSED (in .bib, never cited — informational):", unused)
    block("DUPLICATE keys in .bib:", dups)
    ok = not missing and not dups
    print("validate_bib: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
