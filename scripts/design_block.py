#!/usr/bin/env python3
"""design_block.py — the manuscript's `design:` front-matter block (spec §4, §0.13).

The design lock hashes the block's NORMALISED TEXT, not a parse: stdlib has no YAML parser, and
text is what an edit changes. Normalising drops comments, blank lines, trailing whitespace and
CR, so cosmetic edits keep the hash and any value edit changes it. Known limit: a ` #` inside a
quoted value is read as a comment.

Amendments (spec §0.9) are recorded once, as CSV rows (date, field, old, new, reason) that the
manuscript's `tbl-design-changes` chunk renders, plus a readable Markdown entry with the diff.
"""
from __future__ import annotations
import csv, difflib, hashlib, json, re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LOCK_REL = Path("quality_reports") / "design_lock.json"
AMEND_CSV_REL = Path("quality_reports") / "design_amendments.csv"
AMEND_MD_REL = Path("quality_reports") / "design_amendments.md"
AMEND_FIELDS = ["date", "field", "old", "new", "reason"]
RERUN_FIELDS = ("inference", "sample", "treatment")
_TOP = re.compile(r"^design:\s*(#.*)?$")
_KEY = re.compile(r"^\s*([A-Za-z0-9_.-]+):(?:\s|$)")
_OUTCOME = re.compile(r"(?:^|[{,\s])outcome:\s*([^,}\s]+)")

def front_matter_lines(text: str) -> Optional[List[Tuple[int, str]]]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return [(n + 1, lines[n]) for n in range(1, i)]
    return None

def _block_lines(text: str) -> Optional[List[Tuple[int, str]]]:
    fm = front_matter_lines(text)
    if fm is None:
        return None
    out: List[Tuple[int, str]] = []; inside = False
    for n, ln in fm:
        if not inside:
            if _TOP.match(ln): inside = True; out.append((n, "design:"))
            continue
        if ln.strip() == "" or ln.lstrip().startswith("#"):
            out.append((n, "")); continue
        if not ln.startswith((" ", "\t")):
            break
        out.append((n, ln))
    if not inside:
        return None
    while out and out[-1][1] == "":
        out.pop()
    return out

def design_block(text: str) -> Optional[str]:
    b = _block_lines(text)
    return None if b is None else "\n".join(l for _, l in b)

def design_span(text: str) -> Optional[Tuple[int, int]]:
    b = _block_lines(text)
    return None if b is None else (b[0][0], b[-1][0])

def _normalise(block: str) -> List[str]:
    keep = []
    for ln in block.split("\n"):
        ln = re.sub(r"\s+#.*$", "", ln.replace("\t", "  ")).rstrip()
        if ln.strip():
            keep.append(ln)
    return keep

def design_hash(text: str) -> Optional[str]:
    b = design_block(text)
    return None if b is None else hashlib.sha256("\n".join(_normalise(b)).encode()).hexdigest()

def _paths(block: str) -> List[Tuple[str, str]]:
    """(dotted key path, normalised line) per line; a list item takes its parent's path."""
    out: List[Tuple[str, str]] = []; stack: List[Tuple[int, str]] = []
    for ln in _normalise(block):
        indent = len(ln) - len(ln.lstrip(" ")); m = _KEY.match(ln)
        item = ln.lstrip() == "-" or ln.lstrip().startswith("- ")
        # YAML allows a block list at the same indent as its parent key; such an item belongs to
        # that key, so only a strictly deeper stack entry is popped for a list item.
        floor = indent + 1 if item else indent  # pop entries deeper than (list) or at (key) this indent
        while stack and stack[-1][0] >= floor:
            stack.pop()
        parents = [k for _, k in stack]
        if item:
            out.append((".".join(parents), ln))
        elif m:
            out.append((".".join(parents + [m.group(1)]), ln)); stack.append((indent, m.group(1)))
        else:
            out.append((".".join(parents), ln))
    return out

def check_entry(text: str, name: str) -> Optional[str]:
    want = f"design.checks.{name}"
    hits = [ln.strip() for p, ln in _paths(design_block(text) or "") if p == want or p.startswith(want + ".")]
    return " ".join(hits) if hits else None

def has_check(text: str, name: str) -> bool:
    return check_entry(text, name) is not None

def check_field(text: str, name: str, key: str) -> Optional[str]:
    m = re.search(rf"(?:^|[{{,\s]){re.escape(key)}:\s*\"?([^,}}\"\s]+)", check_entry(text, name) or "")
    return m.group(1) if m else None

def check_number(text: str, name: str, key: str) -> Optional[float]:
    v = check_field(text, name, key)
    try:
        return float(v) if v is not None else None
    except ValueError:
        return None

def _short(path: str) -> str:
    return path[len("design."):] if path.startswith("design.") else path

def amendment_rows(old_block: str, new_block: str, date: str, reason: str) -> List[Dict[str, str]]:
    old, new = _paths(old_block), _paths(new_block)
    rows = []
    sm = difflib.SequenceMatcher(None, [l for _, l in old], [l for _, l in new], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        field = _short(new[j1][0] if j2 > j1 else old[i1][0])
        rows.append({"date": date, "field": field,
                     "old": " / ".join(l.strip() for _, l in old[i1:i2]),
                     "new": " / ".join(l.strip() for _, l in new[j1:j2]), "reason": reason})
    return rows

def _outcomes(block: str) -> Dict[str, str]:
    return {p: m.group(1) for p, ln in _paths(block) if (m := _OUTCOME.search(ln))}

def needs_rerun(rows: List[Dict[str, str]], old_block: str, new_block: str) -> bool:
    """Spec §0.10: an amendment touching the inference rule, sample, treatment or an outcome
    re-runs the power and size explorations."""
    if any(r["field"].split(".")[0] in RERUN_FIELDS for r in rows):
        return True
    return _outcomes(old_block) != _outcomes(new_block)

def checks_changed(rows: List[Dict[str, str]]) -> bool:
    return any(r["field"].split(".")[0] == "checks" for r in rows)

def append_amendments(root: Path, rows: List[Dict[str, str]], heading: str, diff: Optional[str] = None) -> None:
    csv_path = root / AMEND_CSV_REL; csv_path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not csv_path.exists()
    with csv_path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=AMEND_FIELDS)
        if fresh: w.writeheader()
        w.writerows(rows)
    md = root / AMEND_MD_REL
    if not md.exists():
        md.write_text("# Design amendments\n\nAppend-only. Written by `pipeline.py design sign` and "
                      "`design seed-amendment`; the manuscript's `tbl-design-changes` chunk renders the CSV.\n")
    body = "".join(f"- `{r['field']}`: {r['old'] or '(none)'} → {r['new'] or '(none)'}\n" for r in rows)
    reason = rows[0]["reason"] if rows else ""
    with md.open("a") as f:
        f.write(f"\n## {heading}\n\n- reason: {reason}\n{body}" + (f"\n```diff\n{diff}\n```\n" if diff else ""))

def amendment_count(root: Path) -> int:
    p = root / AMEND_CSV_REL
    return sum(1 for _ in csv.DictReader(p.open())) if p.exists() else 0

def manuscript_path(root: Path) -> Optional[Path]:
    c = root / "CLAUDE.md"
    if not c.exists():
        return None
    hits = re.findall(r"^manuscript:\s*(\S+\.qmd)\s*$", c.read_text(errors="ignore"), re.M)
    return (root / hits[0]).resolve() if len(hits) == 1 else None

def read_lock(root: Path) -> Optional[dict]:
    p = root / LOCK_REL
    return json.loads(p.read_text()) if p.exists() else None

def write_lock(root: Path, lock: dict) -> None:
    p = root / LOCK_REL; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(lock, indent=2) + "\n")
