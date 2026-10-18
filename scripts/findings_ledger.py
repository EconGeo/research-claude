#!/usr/bin/env python3
"""findings_ledger.py — file I/O for the finding ledger, the rulings log and the questions file.

Spec §0.8 and §6. The files are Markdown tables under fixed headers, written only through this
module (pipeline.py `ledger`, `ruling`, `question`); design-guard and protect-files deny agents
every other write. Stdlib only, Python 3.9.
"""
from __future__ import annotations
import datetime as dt, os, re
from pathlib import Path
from typing import Dict, List, Optional

LEDGER_REL = Path("quality_reports") / "findings_ledger.md"
RULINGS_REL = Path("quality_reports") / "rulings_log.md"
QUESTIONS_REL = Path("quality_reports") / "questions_for_author.md"

STATUS_RE = re.compile(r"^(open|closed (?:[0-9a-f]{7,40}|pending)|declined: .+|proposal: (pending|accepted|rejected))$")
BLOCKING = re.compile(r"^(open|proposal: pending|proposal: accepted)$")
_SPLIT = re.compile(r"(?<!\\)\|")
LEDGER_COLS = ["id", "created", "creator", "report", "location", "finding", "status", "guard"]
RULINGS_COLS = ["date", "by", "decision", "alternative", "reason"]

def today() -> str:
    return dt.date.today().isoformat()

def _template(name: str) -> str:
    """Templates ship in `templates/` next to `scripts/`; resolve through symlinks so a project's
    `.claude/scripts/` link finds the repo's copy."""
    return (Path(os.path.realpath(__file__)).parent.parent / "templates" / name).read_text()

def _esc(s: str) -> str:
    return " ".join(str(s).split()).replace("|", r"\|")

def _unesc(s: str) -> str:
    return s.strip().replace(r"\|", "|")

def _row_line(vals: List[str]) -> str:
    return "| " + " | ".join(_esc(v) for v in vals) + " |"

def _ensure(path: Path, template: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_template(template))

def _parse(path: Path, cols: List[str]):
    """(lines, [(line_index, row dict)]) for the table rows after the separator line."""
    lines = path.read_text().split("\n"); out = []; seen_sep = False
    for i, ln in enumerate(lines):
        if not seen_sep:
            seen_sep = bool(re.match(r"^\|\s*-{3}", ln)); continue
        if not ln.startswith("|"): continue
        cells = [_unesc(c) for c in _SPLIT.split(ln)[1:-1]]
        cells += [""] * (len(cols) - len(cells))
        out.append((i, dict(zip(cols, cells))))
    return lines, out

def _cols_for(path: Path) -> List[str]:
    return RULINGS_COLS if Path(path).name == "rulings_log.md" else LEDGER_COLS

def rows(path) -> List[Dict[str, str]]:
    path = Path(path)
    if not path.exists(): return []
    return [r for _, r in _parse(path, _cols_for(path))[1]]

def _append(path: Path, template: str, vals: List[str]) -> None:
    _ensure(path, template)
    txt = path.read_text()
    if not txt.endswith("\n"): txt += "\n"
    path.write_text(txt + _row_line(vals) + "\n")

def add(path, creator: str, report: str, location: str, finding: str, status: str = "open") -> str:
    path = Path(path)
    if not STATUS_RE.match(status): raise ValueError(f"bad ledger status {status!r}")
    nums = [int(m.group(1)) for r in rows(path) if (m := re.match(r"^F-(\d+)$", r["id"]))]
    fid = f"F-{max(nums, default=0) + 1:03d}"
    _append(path, "findings-ledger.md", [fid, today(), creator, report, location, finding, status, ""])
    return fid

def set_status(path, fid: str, status: str, guard: Optional[str] = None) -> None:
    path = Path(path)
    if not STATUS_RE.match(status): raise ValueError(f"bad ledger status {status!r}")
    if not path.exists(): raise KeyError(fid)
    lines, parsed = _parse(path, LEDGER_COLS)
    for i, r in parsed:
        if r["id"] == fid:
            r["status"] = status
            if guard is not None: r["guard"] = guard
            lines[i] = _row_line([r[c] for c in LEDGER_COLS]); path.write_text("\n".join(lines)); return
    raise KeyError(fid)

def blocking(path, creator: str) -> List[Dict[str, str]]:
    return [r for r in rows(path) if r["creator"] == creator and BLOCKING.match(r["status"])]

def add_ruling(path, by: str, decision: str, alternative: str, reason: str) -> None:
    _append(Path(path), "rulings-log.md", [today(), by, decision, alternative, reason])

def add_question(path, text: str, blocks: str) -> None:
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Questions for the author\n\nHard stops a session could not decide; the author answers, then the stage resumes.\n")
    txt = path.read_text()
    if not txt.endswith("\n"): txt += "\n"
    path.write_text(txt + f"\n## {today()} — blocks {blocks}\n\n{text.strip()}\n")
