#!/usr/bin/env python3
"""render_registry.py — render rules/permissions.md from rules/registry.yaml.
  python3 scripts/render_registry.py --root .            # write
  python3 scripts/render_registry.py --root . --check    # exit 1 if the file differs
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry_lib as rl

def pred(p) -> str:
    t = p["type"]
    if t == "path":    s = f"`{p['glob']}`" + (f" (≥{p['min']})" if p.get("min", 1) != 1 else "")
    elif t == "section": s = f"heading **{p['heading']}** in `{p['file']}`"
    elif t == "score":   s = f"{p['component']} score ≥ {p['min']}"
    elif t == "score-if-scored": s = f"{p['component']} score ≥ {p['min']} if the component has been scored"
    elif t == "fresh":   s = "rendered output fresh"
    elif t == "render":  s = "`quarto render` exit 0" + (f" for `{p['file']}`" if p.get("file") else "")
    elif t == "critic-ran": s = ("paired critic completed after the creator, **and** the creator's component "
                                 "carries a score recorded after that completion (no component: log only)")
    elif t == "prose-check": s = "`prose_number_check.py` exit 0"
    elif t == "chunk":   s = f"≥{p['min']} chunk(s) labelled `{p['label_glob']}`"
    elif t == "any_of":  s = "any of: " + "; ".join(pred(q) for q in p["of"])
    else: s = t
    if p.get("producer"): s += f" — produced by `{p['producer']}`"
    return s

def render(reg) -> str:
    L = ["# Permission Registry (rendered — do not edit)", "",
         "Rendered from `.claude/rules/registry.yaml` by this repo's `render_registry.py` (a",
         "maintainer-only tool, not shipped to projects). `check_fork.sh` fails if this file",
         "differs from the render. The YAML is what `pipeline.py`, the gate and `/pipeline`",
         "read; this file exists so the registry is readable in a linked project.", "",
         f"**Limits:** {reg['limits']['rounds_per_pair']} rounds per pair, {reg['limits']['rounds_overall']} overall, "
         f"{reg['limits']['verification_retries']} verification retries.", "", "## Components", "",
         "| Component | Weight | Scored by | Conditional |", "|---|---|---|---|"]
    for c, s in reg["components"].items():
        L.append(f"| {c} | {s['weight']} | {s['scored_by']} | {'yes' if s.get('conditional') else 'no'} |")
    L += ["", "## Agents", ""]
    for a, e in reg["agents"].items():
        L += [f"### {a}", "",
              f"- **ROLE:** {e['role']} ({e['kind']}) · **PARALLEL_GROUP:** {e['parallel_group']}",
              "- **REQUIRES:** " + ("nothing beyond the research idea" if not e["requires"] else ""),]
        for p in e["requires"]: L.append(f"  - {pred(p)}")
        L.append("- **PRODUCES:**")
        for p in e["produces"]: L.append(f"  - {pred(p)}")
        # `critic-ran` is auto-appended by pipeline.py's run_preds() and is never declared in the
        # YAML, so without this it is the one gate that binds every creator and appears nowhere in
        # the rendered contract. Render it where it is evaluated.
        if e["critic"] not in (None, "none"):
            L.append(f"  - {pred({'type': 'critic-ran'})} — *appended by `post`, not declared*")
        L += [f"- **CRITIC:** {e['critic']}", f"- **ESCALATION_TARGET:** {e['escalation_target']}",
              f"- **QUALITY_WEIGHT:** {e['quality_weight']} ({e['component']})" + (f" — scored under {e['scored_under']}" if e.get("scored_under") else ""),
              f"- **CONDITIONAL:** {'yes' if e['conditional'] else 'no'}",
              "- **WRITES:** " + ", ".join(f"`{w}`" for w in e["writes"]), ""]
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--check", action="store_true")
    a = ap.parse_args(); root = Path(a.root)
    out = render(rl.load_registry(root)); dest = root / "rules" / "permissions.md"
    if a.check:
        same = dest.exists() and dest.read_text() == out
        print("PASS [registry-rendered]" if same else "FAIL [registry-rendered] rules/permissions.md differs from the render of registry.yaml")
        sys.exit(0 if same else 1)
    dest.write_text(out); print(f"wrote {dest}")

if __name__ == "__main__": main()
