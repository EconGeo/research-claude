#!/usr/bin/env python3
"""context_bill.py — static token-cost audit of the shipped skill/agent/rule tree.

Two questions this answers that context-monitor.py's live 40/55/65/80/90% hook nudges
(.claude/hooks/context-monitor.py) do not: which skill's frontmatter description is
costing every session tokens before it is ever invoked (every skill's name+description
loads into the "Available skills" listing at session start, whether or not the skill
runs), and which shipped file is heaviest if something does read it in full. Adopted from
garrytan/gstack's `gstack-context-bill` ("token cost auditor for installed skill tree").

Token counts are approximate: bytes // 4, the same rough-and-ready heuristic this repo's
CLAUDE.md editing conventions assume elsewhere — good enough to RANK files against each
other, not a claim about exact tokenizer output.
"""
from __future__ import annotations
import argparse, json, os, re, sys
from pathlib import Path
from typing import Any, Dict, List

SHIP = ["agents", "skills", "rules", "hooks", "references", "templates"]
SKIP_DIRS = {"__pycache__", ".git"}

def est_tokens(size_bytes: int) -> int:
    return size_bytes // 4

def iter_files(d: Path):
    """Walk `d` for files, descending into symlinked directories.

    A linked project (see `shared-pipeline.md`) has `.claude/skills/<name>` as a symlink
    to a real directory elsewhere, not a real directory itself. `Path.rglob` does not
    descend into a symlinked subdirectory, which would silently drop every linked skill
    from the audit in exactly the setup this tool exists to audit."""
    paths: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(d, followlinks=True):
        dirnames[:] = [dn for dn in dirnames if dn not in SKIP_DIRS]
        for fn in filenames:
            paths.append(Path(dirpath) / fn)
    for p in sorted(paths):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p

def frontmatter_description(skill_md: Path) -> str:
    """Extract the `description:` value from a SKILL.md's YAML frontmatter, including the
    `>` folded-block form (.claude/skills/checkpoint/SKILL.md uses it) — a plain regex on
    the first line alone would silently return an empty string for every folded skill."""
    text = skill_md.read_text(errors="replace")
    m = re.search(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return ""
    lines = m.group(1).splitlines()
    for i, line in enumerate(lines):
        km = re.match(r"^description:\s*(.*)$", line)
        if not km:
            continue
        rest = km.group(1).strip()
        if rest and rest not in (">", "|", ">-", "|-"):
            return rest
        # Folded/literal block scalar: consume subsequent indented lines.
        collected = []
        for cont in lines[i + 1:]:
            if cont.strip() == "" or cont.startswith((" ", "\t")):
                collected.append(cont.strip())
            else:
                break
        return " ".join(c for c in collected if c)
    return ""

def scan(root: Path) -> Dict[str, Any]:
    claude = root / ".claude" if (root / ".claude" / "agents").is_dir() else root
    directories: Dict[str, Dict[str, int]] = {}
    all_files: List[Dict[str, Any]] = []
    for name in SHIP:
        d = claude / name
        if not d.is_dir():
            continue
        total_bytes = 0
        for f in iter_files(d):
            size = f.stat().st_size
            total_bytes += size
            all_files.append({"path": str(f.relative_to(claude)), "bytes": size,
                               "est_tokens": est_tokens(size)})
        directories[name] = {"bytes": total_bytes, "est_tokens": est_tokens(total_bytes)}

    skills: List[Dict[str, Any]] = []
    skills_dir = claude / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            desc = frontmatter_description(skill_md)
            resident_bytes = len(skill_dir.name.encode()) + len(desc.encode())
            skill_total_bytes = sum(f.stat().st_size for f in iter_files(skill_dir))
            skills.append({
                "name": skill_dir.name,
                "resident_est_tokens": est_tokens(resident_bytes),
                "est_tokens": est_tokens(skill_total_bytes),
            })
    skills.sort(key=lambda s: s["est_tokens"], reverse=True)

    all_files.sort(key=lambda f: f["bytes"], reverse=True)
    return {"root": str(root), "directories": directories, "skills": skills,
            "files": all_files}

def print_summary(report: Dict[str, Any], top: int) -> None:
    print(f"{report['root']}: context bill\n")
    print("By shipped directory:")
    for name, d in sorted(report["directories"].items(), key=lambda kv: -kv[1]["est_tokens"]):
        print(f"  {name:<12} ~{d['est_tokens']:>7,} tokens  ({d['bytes']:,} bytes)")
    total = sum(d["est_tokens"] for d in report["directories"].values())
    print(f"  {'TOTAL':<12} ~{total:>7,} tokens\n")

    resident_total = sum(s["resident_est_tokens"] for s in report["skills"])
    print(f"Always-resident skill-description budget (loaded every session, "
          f"~{resident_total:,} tokens across {len(report['skills'])} skills loaded into "
          f"every session's skill listing):")
    for s in sorted(report["skills"], key=lambda s: -s["resident_est_tokens"])[:top]:
        print(f"  {s['name']:<28} ~{s['resident_est_tokens']:>5,} tokens")
    print()

    print(f"Largest files (full-read cost if invoked):")
    for i, f in enumerate(report["files"][:top], 1):
        print(f"  {i}. {f['path']:<50} ~{f['est_tokens']:>6,} tokens")

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Static token-cost audit of the shipped tree (agents, skills, rules, hooks). "
                    "Prints a summary; writes the full JSON report if --json is given.")
    ap.add_argument("root", nargs="?", default=str(Path(__file__).resolve().parents[1]),
                     help="tree to audit (default: the research-claude checkout holding this script)")
    ap.add_argument("--top", type=int, default=15, help="how many entries per ranked list (default 15)")
    ap.add_argument("--json", metavar="OUT", help="write the full report as JSON here")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        ap.error(f"root is not a directory: {root}")
    report = scan(root)
    print_summary(report, args.top)
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
