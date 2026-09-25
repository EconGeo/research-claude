#!/usr/bin/env python3
"""ledger.py — the cross-project improvement ledger (.claude/rules/meta-governance.md, User corrections).

Why it exists. A correction to a shared skill, agent or rule made in one paper project is
recorded by /checkpoint as one line in that project's SESSION_REPORT.md. Six projects, six
files, nothing reads them together — so the same correction is made again in the next project.
This file is the one place /checkpoint writes such candidates and /promote reads them from.
`show` flags any target named by REPEATED_AT distinct projects.

The ledger lives in the research-claude checkout (docs/improvement-ledger.md), found through
this script's own real path so that `.claude/scripts/ledger.py` in a project resolves to the
shared checkout. Under a pinned install that is a project-local clone; `add` prints the path it
wrote so the caller can see which.

Exit 0 = done. Exit 2 = usage or unknown id.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

REPEATED_AT = 2
HEADER = ("# Improvement ledger\n\n"
          "Append-only. Written by `/checkpoint` (one row per pipeline improvement candidate), "
          "read by `/promote`. A target named by " + str(REPEATED_AT) + " distinct projects is "
          "flagged REPEATED by `.claude/scripts/ledger.py show`. Status is `open`, `landed <sha>` or "
          "`declined: <reason>`. Notes are generic — no dataset, journal or paper nouns; this "
          "repo is public.\n\n"
          "| id | date | project | target | note | status |\n"
          "|---|---|---|---|---|---|\n")
ROW = re.compile(r"^\| (L-\d{3,}) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ((?:[^|]|\\\|)*) \| ([^|]*) \|\s*$")


def default_ledger() -> Path:
    return Path(__file__).resolve().parent.parent / "docs" / "improvement-ledger.md"


def esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ").strip()


def rows(path: Path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        m = ROW.match(line)
        if m:
            out.append(dict(id=m[1], date=m[2].strip(), project=m[3].strip(),
                            target=m[4].strip(), note=m[5].strip(), status=m[6].strip()))
    return out


def cmd_add(a) -> int:
    if "|" in a.project or "|" in a.target:
        print("ledger: '|' is not allowed in project or target", file=sys.stderr)
        return 2
    path = a.ledger
    existing = rows(path)
    n = max((int(r["id"][2:]) for r in existing), default=0) + 1
    rid = f"L-{n:03d}"
    date = a.date or dt.date.today().isoformat()
    target = re.sub(r"^(\./)?(\.claude/)?", "", a.target.strip())
    a.target = target
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(HEADER)
    with path.open("a") as f:
        f.write(f"| {rid} | {date} | {esc(a.project)} | {esc(a.target)} | {esc(a.note)} | open |\n")
    print(rid)
    print(f"ledger: {path}", file=sys.stderr)
    return 0


def cmd_show(a) -> int:
    rs = rows(a.ledger)
    if a.open:
        rs = [r for r in rs if r["status"] == "open"]
    if not rs:
        print("ledger: no rows")
        return 0
    by_target: dict[str, list] = {}
    for r in rs:
        by_target.setdefault(r["target"], []).append(r)
    for target, group in sorted(by_target.items(), key=lambda kv: (-len({r["project"] for r in kv[1]}), kv[0])):
        projects = {r["project"] for r in group}
        flag = "  REPEATED" if len(projects) >= REPEATED_AT else ""
        print(f"{target}  projects={len(projects)}  rows={len(group)}{flag}")
        for r in group:
            print(f"  {r['id']}  {r['date']}  {r['project']}  {r['status']}  — {r['note']}")
    return 0


def cmd_mark(a) -> int:
    path = a.ledger
    lines = path.read_text().splitlines(keepends=True) if path.exists() else []
    status = f"landed {a.value}" if a.what == "landed" else f"declined: {a.value}"
    hit = False
    for i, line in enumerate(lines):
        m = ROW.match(line)
        if m and m[1] == a.id:
            lines[i] = line[: m.start(6) - 1] + f" {esc(status)} |\n"
            hit = True
    if not hit:
        print(f"ledger: no row {a.id}", file=sys.stderr)
        return 2
    path.write_text("".join(lines))
    print(f"{a.id}: {status}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add"); p.add_argument("--ledger", type=Path, default=default_ledger()); p.add_argument("--project", required=True); p.add_argument("--target", required=True)
    p.add_argument("--note", required=True); p.add_argument("--date"); p.set_defaults(fn=cmd_add)
    p = sub.add_parser("show"); p.add_argument("--ledger", type=Path, default=default_ledger()); p.add_argument("--open", action="store_true"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("mark"); p.add_argument("--ledger", type=Path, default=default_ledger()); p.add_argument("id"); p.add_argument("what", choices=["landed", "declined"])
    p.add_argument("value"); p.set_defaults(fn=cmd_mark)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
