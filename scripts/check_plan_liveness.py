#!/usr/bin/env python3
"""check_plan_liveness.py — WARN when a plan under docs/plans/ that still has an open ([ ])
checkbox has had no commit touch its path in --days days.

Coverage, stated plainly (closeout handoff §5 rule 3): this catches a plan literally nobody
has committed against — "hasn't moved," in the closeout handoff's own phrase. It does NOT
verify a recent commit did real task work: a commit that only edits this plan's own Progress
Log resets the clock the same as a commit that landed a task. That gap is real and not solved
here — always WARN, never a blocking gate, so a human reads and judges each hit.
"""
from __future__ import annotations
import argparse, re, subprocess, sys, time
from pathlib import Path

UNCHECKED = re.compile(r"^\s*-\s*\[ \]", re.M)

def last_commit_epoch(root: Path, rel: str):
    r = subprocess.run(["git", "log", "-1", "--format=%ct", "--", rel],
                        cwd=root, capture_output=True, text=True)
    ts = r.stdout.strip()
    return int(ts) if ts else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    root = Path(a.root).resolve()
    now = time.time()
    hits = []
    plans_dir = root / "docs" / "plans"
    for f in sorted(plans_dir.glob("*.md")) if plans_dir.is_dir() else []:
        text = f.read_text(errors="ignore")
        if not UNCHECKED.search(text):
            continue
        rel = str(f.relative_to(root))
        ts = last_commit_epoch(root, rel)
        if ts is None:
            continue
        age_days = (now - ts) / 86400
        if age_days > a.days:
            hits.append(f"{rel}: no commit in {age_days:.0f} days (has open checkboxes)")
    if hits:
        print("WARN [plan-liveness]")
        for h in hits:
            print(f"    {h}")
    else:
        print("PASS [plan-liveness]")
    sys.exit(0)

if __name__ == "__main__":
    main()
