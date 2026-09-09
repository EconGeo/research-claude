#!/usr/bin/env python3
"""Pass A - dependency graph over a pipeline tree.

Nodes: every shipped file. Edges: path references, agent dispatches, skill
invocations, rule citations. Reports dangling edges and orphan nodes.
Resolution is tried at BOTH the repo root and the referring file's directory,
because skills legitimately reference their own bundled files skill-relative.

Honours the repo's residue-marker convention, the same way check_refs.py and
check_paths.py do: a line ending in '<!-- residue:prohibition -->' or
'<!-- residue:historical -->' contributes no edges, and a file whose first line is
exactly '<!-- residue:historical -->' is skipped in full. A gate NAMES ABSENT THINGS
IN ORDER TO ASSERT THEIR ABSENCE; without the marker those assertions are dangling
edges for ever. The marker is per-line, so a genuinely broken reference elsewhere in
the same gate is still reported.
"""
import re, sys, json, pathlib, collections

ROOT = pathlib.Path(sys.argv[1]).resolve()
# Pick whichever base actually holds agents/ - research-claude keeps the pipeline
# at repo root and ALSO has its own .claude/ for working on itself.
CLAUDE = ROOT/".claude" if (ROOT/".claude"/"agents").is_dir() else ROOT
SHIP = ["agents","skills","rules","references","hooks","templates","scripts"]

# The lookbehind excludes `-` and word characters but deliberately ALLOWS `/`, so a
# skill-relative reference (<skill>/templates/<file>.md, the form every agent file uses) and a
# .claude/-prefixed one are both still seen — that is the detection check_paths.py's own
# lookbehind gives up. A tail match inside a longer directory name is not: zotpilot-skills/
# and master_supporting_docs/ are not references to skills/ or docs/.
PATH_RE  = re.compile(r'(?<![A-Za-z0-9_.-])(?:templates|references|scripts|agents|skills|rules|hooks|docs)/[A-Za-z0-9_./-]+\.(?:md|py|sh|json|R|qmd|tex|bib)')
AGENT_RE = re.compile(r'\b([a-z][a-z-]*-critic|librarian|orchestrator|guide-writer|coder|writer|explorer|strategist|theorist|storyteller|verifier|editor|data-engineer|domain-referee|methods-referee)\b', re.I)  # <!-- residue:prohibition -->
SKILL_RE = re.compile(r'(?<![A-Za-z0-9_/-])/([a-z][a-z0-9-]{2,})\b')
MARK     = re.compile(r'<!-- residue:(prohibition|historical) -->\s*$')
# Project-level paths: they exist in an INSTALLED project and never in this repo, so they can
# never resolve here and are not dangling edges. Mirrored from check_paths.py's sets of the
# same names, so the two tools agree on what "project-level" means. Only `scripts/acquire/`
# and the four templates entries can actually match — PATH_RE's leading alternation covers
# neither `data/` nor `quality_reports/` — but the sets are kept identical on purpose, so an
# addition on either side is obviously mirrored on the other.
EXEMPT_PREFIX = ("data/", "quality_reports/", "talks/", "explorations/", "scripts/acquire/",
                 "master_supporting_docs/", ".claude/state/", ".claude/settings", ".claude/pipeline.lock")
EXEMPT_EXACT = {"templates/quarto-preamble.tex", "templates/word-reference.docx",
                "templates/ai-use-log.md", "templates/apa.csl", "scripts/acquire"}
# Generic pipeline vocabulary that AGENT_RE matches but that names no agent. This has to be a
# set here and CANNOT be replaced by residue markers: AGENT_RE is case-insensitive, and
# "Worker-critic pairing" / "Worker-critic separation" is ordinary prose in four shipped
# SKILL.md files (analyze, discover, review, talk). check_refs.py carries the same exemption
# inline, in its DELETED_AGENTS scan.
AGENT_NOT_A_NAME = {"worker-critic"}

def shipped_files(base):
    out=[]
    for d in SHIP:
        p = base/d
        if not p.is_dir(): continue
        for f in p.rglob("*"):
            if f.is_file() and f.suffix in {".md",".py",".sh",".json",".R",".qmd"}:
                out.append(f)
    return out

files = shipped_files(CLAUDE) + ([] if CLAUDE==ROOT else shipped_files(ROOT))
roster = {p.stem for p in (CLAUDE/"agents").glob("*.md")} if (CLAUDE/"agents").is_dir() else set()
skills = {p.name for p in (CLAUDE/"skills").iterdir() if p.is_dir()} if (CLAUDE/"skills").is_dir() else set()

dangling_paths, agent_edges, skill_edges = [], collections.defaultdict(set), collections.defaultdict(set)
inbound = collections.Counter()

for f in files:
    try: txt = f.read_text(errors="ignore")
    except Exception: continue
    rel = f.relative_to(ROOT)
    lines = txt.split("\n")
    if lines and lines[0].strip() == "<!-- residue:historical -->":
        continue
    live = [ln for ln in lines if not MARK.search(ln)]
    scanned = "\n".join(live)
    for t in set(PATH_RE.findall(scanned)):
        if t.startswith(EXEMPT_PREFIX) or t in EXEMPT_EXACT: continue
        hit = None
        for base in (CLAUDE, ROOT, f.parent):
            if (base/t).exists(): hit = base/t; break
        if hit is None:
            dangling_paths.append((str(rel), t))
        else:
            inbound[str(hit.resolve())] += 1
    for a in {m.lower() for m in AGENT_RE.findall(scanned)}:
        if a in AGENT_NOT_A_NAME: continue
        agent_edges[a].add(str(rel))
    for s in set(SKILL_RE.findall(scanned)):
        if s in skills: skill_edges[s].add(str(rel))

report = {
  "root": str(ROOT),
  "counts": {"files": len(files), "agents": len(roster), "skills": len(skills)},
  "dangling_paths": sorted(dangling_paths),
  "agents_named_not_on_roster": sorted(a for a in agent_edges if a not in roster),
  "agents_on_roster_never_named_outside_own_file": sorted(
      a for a in roster if not (agent_edges.get(a,set()) - {f"agents/{a}.md", f".claude/agents/{a}.md"})),
  "skills_never_invoked_by_anything": sorted(s for s in skills if not skill_edges.get(s)),
  "orphan_files_no_inbound_reference": sorted(
      str(f.relative_to(ROOT)) for f in files
      if inbound[str(f.resolve())]==0 and f.name not in {"SKILL.md","README.md"}),
}
out = pathlib.Path(sys.argv[2])
out.write_text(json.dumps(report, indent=2))
c=report["counts"]
print(f"{ROOT.name}: {c['files']} files, {c['agents']} agents, {c['skills']} skills")
print(f"  dangling path refs        : {len(report['dangling_paths'])}")
print(f"  agents named, not on roster: {report['agents_named_not_on_roster']}")
print(f"  roster agents never dispatched anywhere: {report['agents_on_roster_never_named_outside_own_file']}")
print(f"  skills never invoked      : {report['skills_never_invoked_by_anything']}")
print(f"  orphan files (0 inbound)  : {len(report['orphan_files_no_inbound_reference'])}")
