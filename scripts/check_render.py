#!/usr/bin/env python3
"""check_render.py — post-render checks on the RENDERED output (write gate item 4).

Why it exists. Quarto fails silently: an unresolved `@ref` prints `?@name` and exits 0; a
table note wider than the text block clips words out of a sentence; an overwide table drops
a column; a declared `keywords:` never reaches the page; a `fig-` label in a manually-numbered
document prints a second number. `quarto_structure_check.py` reads the SOURCE. This reads the
PAGE, through `pdftotext`, and does what the authoring reference's post-render checklist asks
a human to do by eye — which two projects showed nobody does.

Usage: check_render.py <manuscript.pdf | rendered.txt> [--expect TEXT]... [--columns "Table N: a,b,c"]...
  --expect   a phrase that must appear (keywords line, a mandated note phrase); whitespace and
             ligatures are normalised, so a line wrap is not a miss.
  --columns  a table's caption prefix and its column headers; each header must appear after
             that caption and before the next "Table"/"Figure" caption.
Exit 0 = clean. Exit 1 = findings, one per line as KIND: detail. Exit 2 = cannot run.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

LIG = {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl", "\u2019": "'"}


def norm(s: str) -> str:
    for k, v in LIG.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s)


def cannot_run(msg: str) -> None:
    # NOTE (bug fix vs. the task-7 brief's `sys.exit(f"...")`): sys.exit() called with a
    # str argument prints it to stderr but exits with status 1, not 2 — verified by direct
    # execution. The documented interface (module docstring, this file) and
    # test_missing_input_exits_2 both require exit 2 for "cannot run", so errors here print
    # to stderr and exit 2 explicitly instead.
    print(f"check_render: {msg}", file=sys.stderr)
    sys.exit(2)


def load(path: Path) -> str:
    if not path.exists():
        cannot_run(f"{path} not found")
    if path.suffix.lower() == ".pdf":
        if not shutil.which("pdftotext"):
            cannot_run("pdftotext not on PATH (brew install poppler)")
        r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
        if r.returncode:
            cannot_run(f"pdftotext failed: {r.stderr.strip()}")
        return r.stdout
    return path.read_text(errors="replace")


def findings(text: str, expect: list[str], columns: list[str]) -> list[str]:
    out = []
    for m in re.finditer(r"\?@[\w:.-]+", text):
        out.append(f"UNRESOLVED: {m.group(0)}")
    for m in re.finditer(r"\\[A-Za-z]+\{", text):
        out.append(f"LITERAL_TEX: {m.group(0)}")
    for m in re.finditer(r"(?<![\w)])\*{1,2}(?=\S)[^*\n]{1,80}?(?<=\S)\*{1,2}(?!\w)", text):
        out.append(f"LITERAL_MD: {m.group(0)}")
    for m in re.finditer(r"</?(span|div|br|b|i|em|strong|sup|sub)\b[^>]*>", text):
        out.append(f"LITERAL_HTML: {m.group(0)}")
    for m in re.finditer(r"\b(Table|Figure)\s+(\d+[A-Za-z]?)\W{0,3}(Table|Figure)\s+\2\b", text):
        out.append(f"DOUBLED: {m.group(1)} {m.group(2)}")
    flat = norm(text)
    for e in expect:
        if norm(e) not in flat:
            out.append(f"MISSING: {e}")
    caps = list(re.finditer(r"^\s*(Table|Figure)\s+\d+[A-Za-z]?[:.]", text, flags=re.M))
    for spec in columns:
        head, _, cols = spec.partition(":")
        head = head.strip()
        block = None
        for i, c in enumerate(caps):
            if text[c.start():c.end()].strip().startswith(head):
                end = caps[i + 1].start() if i + 1 < len(caps) else len(text)
                block = norm(text[c.start():end]); break
        if block is None:
            out.append(f"COLUMN: {head}: caption not found"); continue
        for col in [c.strip() for c in cols.split(",") if c.strip()]:
            if norm(col) not in block:
                out.append(f"COLUMN: {head}: {col}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", type=Path)
    ap.add_argument("--expect", action="append", default=[])
    ap.add_argument("--columns", action="append", default=[])
    a = ap.parse_args()
    fs = findings(load(a.path), a.expect, a.columns)
    for f in fs:
        print(f)
    print(f"check_render: {len(fs)} finding(s)")
    return 1 if fs else 0


if __name__ == "__main__":
    sys.exit(main())
