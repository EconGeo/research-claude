#!/usr/bin/env python3
"""pipeline.py — executable lifecycle for the research pipeline (stdlib, Python 3.9).

Reads .claude/rules/registry.yaml (the same file at the repo root, without the .claude/
prefix, when --root is the research-claude checkout itself), the project's CLAUDE.md
`manuscript:` declaration, quality_reports/pipeline_state.json and
quality_reports/agent_dispatch.jsonl. See .claude/rules/lifecycle.md for the contract.
"""
from __future__ import annotations
import argparse, datetime as dt, fnmatch, glob, json, re, subprocess, sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry_lib as rl

STATE_REL = Path("quality_reports") / "pipeline_state.json"
LOG_REL = Path("quality_reports") / "agent_dispatch.jsonl"
GATES = {"commit": (80, None), "pr": (90, None), "submission": (95, 80)}

def now() -> str:
    """UTC with an explicit offset, fixed width, millisecond precision.

    `critic-ran` compares an `at` in pipeline_state.json (COMMITTED, shared across machines)
    against one in agent_dispatch.jsonl (gitignored, local). A local-time string with no offset
    would compare wrong across machines and would go backwards for an hour at every DST
    fall-back. Uniform width and a constant `+00:00` suffix keep lexicographic order == chronological order.

    What this does NOT fix: clock skew. Two machines disagreeing about `now` can still order
    a local dispatch-log entry against a committed state-file score wrongly, and in the
    fail-OPEN direction — a creator run on a slow clock can stamp earlier than an older
    committed score. UTC removes the timezone and DST halves of the problem, not that one.
    """
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")

# ── registry & manuscript ───────────────────────────────────────────────────
def find_registry(root: Path) -> Path:
    for c in (root / ".claude" / "rules" / "registry.yaml", root / "rules" / "registry.yaml"):
        if c.exists(): return c
    sys.exit("pipeline.py: no registry.yaml under .claude/rules/ or rules/")

def load_reg(root: Path) -> Dict[str, Any]:
    p = find_registry(root); return rl.load_yaml_subset(p.read_text())

def declared_manuscript(root: Path) -> Path:
    claude = root / "CLAUDE.md"
    if not claude.exists(): sys.exit("pipeline.py: CLAUDE.md not found — declare `manuscript: <file>.qmd` in it (D-8)")
    hits = re.findall(r"^manuscript:\s*(\S+\.qmd)\s*$", claude.read_text(), re.M)
    if len(hits) != 1:
        sys.exit(f"pipeline.py: CLAUDE.md must declare exactly one `manuscript: <file>.qmd` line (found {len(hits)})")
    m = root / hits[0]
    if not m.exists(): sys.exit(f"pipeline.py: declared manuscript {hits[0]} does not exist")
    return m

def rendered_output(ms: Path) -> Optional[Path]:
    cands = [ms.with_suffix(".pdf"), ms.with_suffix(".docx"), ms.with_suffix(".html")]
    ex = [c for c in cands if c.exists()]
    return max(ex, key=lambda p: p.stat().st_mtime) if ex else None

# ── state ───────────────────────────────────────────────────────────────────
def state_path(root: Path) -> Path: return root / STATE_REL

def empty_state(root: Path, ms: Path) -> Dict[str, Any]:
    return {"schema_version": 2, "project": root.name, "manuscript": str(ms.relative_to(root)), "updated": now(),
            "components": {}, "sections": {}, "strikes": {}, "blocked_by": None, "overall": None}

def load_state(root: Path) -> Dict[str, Any]:
    p = state_path(root)
    if not p.exists(): sys.exit("pipeline.py: no pipeline_state.json — run `pipeline.py state init`")
    return json.loads(p.read_text())

def save_state(root: Path, st: Dict[str, Any]) -> None:
    st["updated"] = now(); state_path(root).parent.mkdir(parents=True, exist_ok=True)
    state_path(root).write_text(json.dumps(st, indent=2) + "\n")

def validate_state(st: Dict[str, Any], reg: Dict[str, Any]) -> List[str]:
    p: List[str] = []
    if st.get("schema_version") != 2: p.append("schema_version must be 2 (legacy clo-author shape is not accepted)")
    for k, t in [("project", str), ("manuscript", str), ("updated", str), ("components", dict), ("sections", dict), ("strikes", dict)]:
        if not isinstance(st.get(k), t): p.append(f"{k} must be {t.__name__}")
    comps = set(reg["components"])
    for c, e in (st.get("components") or {}).items():
        if c not in comps: p.append(f"components.{c}: not a registry component")
        if not isinstance(e, dict) or not isinstance(e.get("score"), (int, float)) or not 0 <= e["score"] <= 100:
            p.append(f"components.{c}: score must be a number in 0..100")
        for k in ("critic", "report", "at"):
            if not isinstance((e or {}).get(k), str): p.append(f"components.{c}: {k} must be a string")
    for a in (st.get("strikes") or {}):
        if a not in reg["agents"]: p.append(f"strikes.{a}: not a registry agent")
    return p

# ── score ───────────────────────────────────────────────────────────────────
def compute_overall(st, reg) -> Tuple[Optional[float], Dict[str, float]]:
    w = rl.component_weights(reg); scored = {c: e["score"] for c, e in st.get("components", {}).items()}
    used = {c: w[c] for c in scored if c in w}
    if not used: return None, {}
    tot = sum(used.values()); return round(sum(scored[c] * used[c] for c in used) / tot, 2), used

# ── dispatch log ────────────────────────────────────────────────────────────
def read_log(root: Path) -> List[Dict[str, Any]]:
    p = root / LOG_REL
    if not p.exists(): return []
    out = []
    for ln in p.read_text().splitlines():
        try: out.append(json.loads(ln))
        except json.JSONDecodeError: continue
    return out

def append_log(root: Path, agent: str, source: str = "pipeline.py") -> None:
    p = root / LOG_REL; p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f: f.write(json.dumps({"at": now(), "agent": agent, "source": source}) + "\n")

def last_completion(log, agent) -> Optional[str]:
    ats = [e["at"] for e in log if e.get("agent") == agent]
    return max(ats) if ats else None

# ── predicates ──────────────────────────────────────────────────────────────
class Ctx:
    def __init__(self, root: Path, reg, agent: Optional[str]):
        self.root, self.reg, self.agent = root, reg, agent
        self._ms: Optional[Path] = None
    @property
    def ms(self) -> Path:
        if self._ms is None: self._ms = declared_manuscript(self.root)
        return self._ms

def chunk_labels(ms: Path) -> List[str]:
    return re.findall(r"^#\|\s*label:\s*([A-Za-z0-9_-]+)", ms.read_text(), re.M)

def headings(path: Path) -> List[str]:
    return [h.strip() for h in re.findall(r"^#{1,6}\s+(.+?)\s*(?:\{[^}]*\})?\s*$", path.read_text(), re.M)]

def is_fresh(root: Path, ms: Path) -> Tuple[bool, str]:
    """Every rendered output must be at least as new as every input.

    Deliberately checks the OLDEST output, not the newest. `rendered_output()`
    returns the newest of .pdf/.docx/.html for reporting, and freshness once used
    it — so a stale .docx passed as long as a newer .html sat beside it, and the
    `render` predicate then skipped rendering entirely. A gate whose job is to
    prove the manuscript still compiles was satisfied by an artifact of a format
    the project may not even publish.

    Failing closed costs a re-render when a leftover artifact from another format
    lingers; the message names the stale file so the fix is obvious (re-render, or
    delete the leftover). The alternative — trusting whichever file happens to be
    newest — silently certifies a deliverable nobody rebuilt.
    """
    outs = [c for c in (ms.with_suffix(".pdf"), ms.with_suffix(".docx"), ms.with_suffix(".html")) if c.exists()]
    if not outs: return False, "no rendered output"
    newest = ms.stat().st_mtime
    for f in (root / "data" / "raw").rglob("*"):
        if f.is_file(): newest = max(newest, f.stat().st_mtime)
    stale = [o for o in outs if o.stat().st_mtime < newest]
    if stale:
        return False, f"{', '.join(s.name for s in stale)} older than newest input"
    return True, f"{', '.join(o.name for o in outs)} vs newest input"

def do_render(root: Path, target: Path) -> Tuple[bool, str]:
    p = subprocess.run(["quarto", "render", str(target.relative_to(root))], cwd=root, capture_output=True, text=True)
    return p.returncode == 0, (p.stderr or p.stdout).strip().splitlines()[-1:] and (p.stderr or p.stdout).strip().splitlines()[-1] or ""

def evaluate(pred: Dict[str, Any], ctx: Ctx, post: bool = False) -> Tuple[bool, str]:
    t = pred["type"]; root = ctx.root
    if t == "path":
        n = len(glob.glob(str(root / pred["glob"]), recursive=True)); need = int(pred.get("min", 1))
        return n >= need, f"path {pred['glob']} ({n} found, need {need})"
    if t == "section":
        files = [ctx.ms] if pred["file"] == "manuscript" else [Path(p) for p in glob.glob(str(root / pred["file"]))]
        ok = any(pred["heading"] in headings(f) for f in files if f.exists())
        return ok, f"heading '{pred['heading']}' in {pred['file']}"
    if t == "score":
        st = json.loads(state_path(root).read_text()) if state_path(root).exists() else {"components": {}}
        if pred["component"] == "overall":
            ov, _ = compute_overall(st, ctx.reg); val = ov
        else:
            val = st.get("components", {}).get(pred["component"], {}).get("score")
        ok = val is not None and val >= float(pred["min"])
        return ok, f"{pred['component']} score ≥ {pred['min']} (have {val})"
    if t == "score-if-scored":
        # A component that HAS been scored must clear `min`; one never scored is ignored.
        # A MISSING state file is not "never scored" — defaulting to {} here would make the
        # predicate pass vacuously on any project that never ran `state init` (fail-open).
        desc = f"{pred['component']} score ≥ {pred['min']} if scored"
        sp = state_path(root)
        if not sp.exists():
            return False, desc + " — no pipeline_state.json (run `pipeline.py state init`)"
        st = json.loads(sp.read_text())
        val = st.get("components", {}).get(pred["component"], {}).get("score")
        if val is None:                                   # `is None`, never truthiness: 0.0 is a score
            return True, desc + " (never scored — not required yet)"
        return val >= float(pred["min"]), desc + f" (have {val})"
    if t == "fresh":
        ok, why = is_fresh(root, ctx.ms); return ok, f"fresh: {why}"
    if t == "render":
        targets = [ctx.ms] if not pred.get("file") else [Path(p) for p in glob.glob(str(root / pred["file"]))]
        if not targets: return False, f"render: nothing matches {pred.get('file')}"
        for tg in targets:
            if tg == ctx.ms and is_fresh(root, ctx.ms)[0]: continue          # render only when stale
            ok, why = do_render(root, tg)
            if not ok: return False, f"render {tg.name} failed: {why}"
        return True, "render exit 0"
    if t == "critic-ran":
        # Both halves of the lifecycle contract live here, because run_preds() AUTO-APPENDS this
        # predicate for every agent with a critic. A hand-maintained `score` entry in `produces`
        # can be forgotten for one agent; this cannot. The score half requires a score that
        # POSTDATES the creator — a score from an earlier round reviewed earlier work.
        crit = rl.critic_of(ctx.reg, ctx.agent or "")
        if not crit: return True, "no critic declared"
        log = read_log(root); a, c = last_completion(log, ctx.agent), last_completion(log, crit)
        if a is None or c is None or c <= a:
            return False, f"critic-ran: {crit} has not completed after {ctx.agent} (creator {a}, critic {c})"
        ran = f"critic-ran: {crit} after {ctx.agent}"
        comp = (ctx.reg["agents"].get(ctx.agent or "") or {}).get("component")
        if comp in (None, "none"):      # keyed on the COMPONENT, never on the agent's name
            return True, ran + " (component none — nothing to score)"
        sp = state_path(root)
        if not sp.exists():
            return False, ran + f", but there is no pipeline_state.json to carry the {comp} score (run `pipeline.py state init`)"
        st = json.loads(sp.read_text())
        at = ((st.get("components") or {}).get(comp) or {}).get("at")
        if at is None:
            if st.get("sections"):
                return False, (ran + f", but {comp} is unscored: {len(st['sections'])} score(s) are recorded under "
                               "`sections` (a section-scoped critic score), and a section draft does not close the "
                               f"{ctx.agent} stage — record a {comp} score with no --scope")
            return False, ran + f", but recorded no {comp} score"
        if at <= a:
            return False, (ran + f", but the {comp} score is from an earlier round: scored at {at}, "
                           f"{ctx.agent} completed at {a} — re-score after the creator's last completion")
        return True, ran + f", {comp} scored at {at} (creator {a}, critic {c})"
    if t == "prose-check":
        script = root / ".claude" / "scripts" / "prose_number_check.py"
        if not script.exists(): return False, "prose-check: .claude/scripts/prose_number_check.py not linked"
        p = subprocess.run([sys.executable, str(script), str(ctx.ms.relative_to(root))], cwd=root, capture_output=True, text=True)
        return p.returncode == 0, "prose_number_check.py exit " + str(p.returncode)
    if t == "chunk":
        n = sum(1 for l in chunk_labels(ctx.ms) if fnmatch.fnmatch(l, pred["label_glob"]))
        return n >= int(pred["min"]), f"chunks {pred['label_glob']} ({n} found, need {pred['min']})"
    if t == "any_of":
        results = [evaluate(q, ctx, post) for q in pred["of"]]
        return any(r[0] for r in results), "any of: " + " | ".join(r[1] for r in results)
    return False, f"unknown predicate {t}"

def run_preds(kind: str, agent: str, root: Path, reg) -> int:
    if agent not in reg["agents"]: sys.exit(f"pipeline.py: {agent!r} is not in the registry")
    e = reg["agents"][agent]; ctx = Ctx(root, reg, agent)
    preds = list(e["requires"] if kind == "pre" else e["produces"])
    if kind == "post" and rl.critic_of(reg, agent) and not any(p["type"] == "critic-ran" for p in preds):
        preds.append({"type": "critic-ran"})
    rc = 0
    for p in preds:
        ok, desc = evaluate(p, ctx, post=(kind == "post"))
        hint = f" — run `{p['producer']}`" if (not ok and p.get("producer")) else ""
        print(("ok      " if ok else "MISSING ") + desc + hint)
        rc |= 0 if ok else 1
    print(f"{kind} {agent}: " + ("PASS" if rc == 0 else "FAIL"))
    return rc

# ── registry check (check_fork criteria) ────────────────────────────────────
AUTH_PAIR = re.compile(r"^\|\s*(lit-position|explorer|strategist|theorist|coder|data-engineer|writer|storyteller)\s*\|\s*[a-z-]+-critic\s*\|", re.M)
AUTH_ARROW = re.compile(r"\b(lit-position|explorer|strategist|theorist|coder|data-engineer|writer|storyteller)\b\s*(\([^)]{0,40}\)\s*)?(→|->|↔)\s*[a-z-]+-critic\b", re.I)
AUTH_WEIGHT = re.compile(r"(QUALITY_WEIGHT|\bweight)\s*[:=|]\s*\d|\b\d+(\.\d+)?%\s*(of\s+)?(weight|\((literature|data|strategy|theory|code|manuscript|replication))", re.I)
AUTH_ALLOW = {"rules/registry.yaml", "rules/permissions.md", "rules/quality.md"}  # <!-- residue:prohibition -->
# The marker above is check_paths.py's convention, reused here (precedent: audit_graph.py's
# AGENT_RE line): these three strings are runtime values compared against
# `str(f.relative_to(root))`, which is repo-root-relative by construction — never `.claude/`-
# prefixed — so D-4's shipped-path-prefix rule does not apply to this set literal.

def registry_check(root: Path) -> int:
    rc = 0; reg = rl.load_registry(root)
    probs = rl.validate_registry(reg)
    roster = {p.stem for p in (root / "agents").glob("*.md")}
    for a, e in reg["agents"].items():
        if e.get("kind") == "agent" and a not in roster: probs.append(f"{a}: declared but agents/{a}.md missing")
    for a in roster:
        if a not in reg["agents"]: probs.append(f"agents/{a}.md exists but is not declared")
    print("PASS [registry-complete]" if not probs else "FAIL [registry-complete]"); [print(f"    {p}") for p in probs]; rc |= bool(probs)
    hits = []
    for d in ["agents", "skills", "rules", "references", "hooks", "templates", "seeds"]:
        for f in sorted((root / d).rglob("*.md")) if (root / d).is_dir() else []:
            rel = str(f.relative_to(root))
            if rel in AUTH_ALLOW: continue
            for i, ln in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                if "residue:historical" in ln: continue
                if AUTH_PAIR.search(ln) or AUTH_ARROW.search(ln) or AUTH_WEIGHT.search(ln):
                    hits.append(f"{rel}:{i}: {ln.strip()[:100]}")
    print("PASS [registry-authority]" if not hits else "FAIL [registry-authority]"); [print(f"    {h}") for h in hits]; rc |= bool(hits)
    p = subprocess.run([sys.executable, str(root / "scripts" / "render_registry.py"), "--root", str(root), "--check"], capture_output=True, text=True)
    print(p.stdout.strip()); rc |= p.returncode != 0
    wp = rl.weights_report(reg, (root / "rules" / "quality.md").read_text() if (root / "rules" / "quality.md").exists() else "")
    print("PASS [weights-sum]" if not wp else "FAIL [weights-sum]"); [print(f"    {w}") for w in wp]; rc |= bool(wp)
    pa = rl.parse_agree(root); print(f"{pa} [registry-parse-agree]" + (" (PyYAML not importable)" if pa == "SKIP" else "")); rc |= pa == "FAIL"
    return int(rc)

# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manuscript"); sub.add_parser("fresh")
    for k in ("pre", "post"): sub.add_parser(k).add_argument("agent")
    sc = sub.add_parser("score"); sc.add_argument("--gate", choices=sorted(GATES))
    st = sub.add_parser("state"); st.add_argument("op", choices=["init", "validate", "show", "record-score", "strike", "set-blocked", "clear-blocked"])
    st.add_argument("args", nargs="*"); st.add_argument("--critic"); st.add_argument("--report"); st.add_argument("--scope")
    sub.add_parser("conflicts").add_argument("agents", nargs="+")
    sub.add_parser("registry").add_argument("op", choices=["check"])
    lg = sub.add_parser("log"); lg.add_argument("agent"); lg.add_argument("--source", default="skill")
    a = ap.parse_args(); root = Path(a.root).resolve()
    if a.cmd == "registry": return registry_check(root)
    reg = load_reg(root)
    if a.cmd == "manuscript": print(declared_manuscript(root).relative_to(root)); return 0
    if a.cmd == "fresh":
        ok, why = is_fresh(root, declared_manuscript(root)); print(("fresh: " if ok else "STALE: ") + why); return 0 if ok else 1
    if a.cmd in ("pre", "post"): return run_preds(a.cmd, a.agent, root, reg)
    if a.cmd == "log": append_log(root, a.agent, a.source); return 0
    if a.cmd == "conflicts":
        ws = {}
        for ag in a.agents:
            if ag not in reg["agents"]: sys.exit(f"unknown agent {ag}")
            ws[ag] = set(reg["agents"][ag]["writes"])
        clashes = [(x, y, ws[x] & ws[y]) for i, x in enumerate(a.agents) for y in a.agents[i + 1:] if ws[x] & ws[y]]
        for x, y, s in clashes: print(f"CONFLICT {x} ∩ {y}: {sorted(s)}")
        print("conflicts: " + ("none" if not clashes else f"{len(clashes)}")); return 1 if clashes else 0
    if a.cmd == "score":
        stt = load_state(root); ov, used = compute_overall(stt, reg)
        for c, w in used.items(): print(f"{c:12s} {stt['components'][c]['score']:6.1f}  weight {w:5.1f}")
        print(f"overall={ov if ov is not None else 'n/a'}")
        if a.gate:
            need, per = GATES[a.gate]; ok = ov is not None and ov >= need and (per is None or all(e["score"] >= per for e in stt["components"].values()))
            print(f"gate {a.gate}: " + ("PASS" if ok else "FAIL")); return 0 if ok else 1
        return 0
    if a.cmd == "state":
        if a.op == "init":
            ms = declared_manuscript(root)
            if state_path(root).exists(): print("pipeline_state.json already exists — left untouched"); return 0
            save_state(root, empty_state(root, ms)); print(f"wrote {STATE_REL}"); return 0
        stt = load_state(root)
        if a.op == "validate":
            probs = validate_state(stt, reg); [print(f"    {p}") for p in probs]
            print("state: " + ("valid" if not probs else "INVALID")); return 1 if probs else 0
        if a.op == "show": print(json.dumps(stt, indent=2)); return 0
        if a.op == "record-score":
            if len(a.args) != 2 or not a.critic or not a.report: sys.exit("usage: state record-score <component> <score> --critic X --report P [--scope section:NAME]")
            comp, score = a.args[0], float(a.args[1])
            if comp not in reg["components"] or not 0 <= score <= 100: print("record-score: bad component or score"); return 1
            # The registry already knows which critic owns each component, so honour it.
            # Without this, `record-score code 100 --critic coder` is accepted and `post coder`
            # then passes on a creator that scored itself — the exact thing
            # .claude/rules/agents.md names as an invariant: creators never self-score.
            owner = reg["components"][comp].get("scored_by")
            if owner and a.critic != owner:
                print(f"record-score: {comp} is scored by {owner}, not {a.critic} "
                      f"(see .claude/rules/registry.yaml)"); return 1
            entry = {"score": score, "critic": a.critic, "report": a.report, "at": now()}
            if a.scope and a.scope.startswith("section:"):
                stt["sections"][a.scope.split(":", 1)[1]] = entry
            else:
                entry["rounds"] = stt["components"].get(comp, {}).get("rounds", 0) + 1; stt["components"][comp] = entry
            stt["overall"], _ = compute_overall(stt, reg); save_state(root, stt); print(f"recorded {comp}={score}"); return 0
        if a.op == "strike":
            cr = a.args[0]; n = stt["strikes"].get(cr, 0) + 1; stt["strikes"][cr] = n; save_state(root, stt)
            lim = int(reg["limits"]["rounds_per_pair"])
            print(f"{cr}: strike {n} of {lim}" + (f" — ESCALATE to {reg['agents'][cr]['escalation_target']}" if n >= lim else "")); return 0
        if a.op == "set-blocked": stt["blocked_by"] = " ".join(a.args); save_state(root, stt); return 0
        if a.op == "clear-blocked": stt["blocked_by"] = None; save_state(root, stt); return 0
    return 2

if __name__ == "__main__":
    sys.exit(main())
