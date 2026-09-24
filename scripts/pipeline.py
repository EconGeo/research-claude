#!/usr/bin/env python3
"""pipeline.py — executable lifecycle for the research pipeline (stdlib, Python 3.9).

Reads .claude/rules/registry.yaml (the same file at the repo root, without the .claude/
prefix, when --root is the research-claude checkout itself), the project's CLAUDE.md
`manuscript:` declaration, quality_reports/pipeline_state.json and
quality_reports/agent_dispatch.jsonl. See .claude/rules/lifecycle.md for the contract.

`next` is where the driver starts: it reads the state file and the dispatch log together and
names the first component stage that is ready, treating a scored stage with no logged creator
completion as adopted work (see next_report).
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
        d = (e or {}).get("deductions")
        if d is not None and (isinstance(d, bool) or not isinstance(d, (int, float)) or d < 0):
            p.append(f"components.{c}: deductions must be a non-negative number when present")
    for a in (st.get("strikes") or {}):
        if a not in reg["agents"]: p.append(f"strikes.{a}: not a registry agent")
    return p

# ── score ───────────────────────────────────────────────────────────────────
def compute_overall(st, reg) -> Tuple[Optional[float], Dict[str, float]]:
    w = rl.component_weights(reg); scored = {c: e["score"] for c, e in st.get("components", {}).items()}
    used = {c: w[c] for c in scored if c in w}
    if not used: return None, {}
    tot = sum(used.values()); return round(sum(scored[c] * used[c] for c in used) / tot, 2), used

def deduction_note(entry: Dict[str, Any]) -> str:
    """What stands behind a score, for `score` and `next`.

    Critics start at 100, deduct per rubric and floor at 0 — so 185 points of deductions and
    817 both record as 0, and two floored papers read as equally far from 80 (observed on two
    adoptions, 2026-09-13). The unfloored total is the only thing that still ranks them. A
    floored score with no total is flagged rather than left silent: it is exactly the case
    where the ranking was lost."""
    d = entry.get("deductions")
    if d is None:
        return "  (floored — deductions not recorded)" if entry.get("score") == 0 else ""
    return f"  ({'floored; ' if entry.get('score') == 0 else ''}{d:g} deducted)"

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

HASH_LABEL_RE = re.compile(r"^#\|\s*label:\s*([A-Za-z0-9_-]+)", re.M)
BRACE_NAMED_LABEL_RE = re.compile(r'^```\{[a-zA-Z]+[^}\n]*?\blabel\s*=\s*["\']([A-Za-z0-9_-]+)["\']', re.M)
BRACE_POSITIONAL_LABEL_RE = re.compile(r"^```\{[a-zA-Z]+[ \t]+([A-Za-z0-9_-]+)\s*[,}]", re.M)

def chunk_labels(ms: Path) -> List[str]:
    """Every chunk label in the manuscript, in whichever of Quarto's three spellings a chunk
    uses: a `#\\| label:` option line, the brace-header positional form (`{r foo, ...}`), or the
    brace-header named form (`{r, label="foo"}`). `#\\| label:` alone undercounts by
    construction: tested against a real 80-chunk manuscript, 79 chunks carried their label in
    the brace header and only one (`setup`) used `#\\| label:` — so the pre-fix version returned
    a single label for the whole document (Phase 1.1)."""
    text = ms.read_text()
    return HASH_LABEL_RE.findall(text) + BRACE_NAMED_LABEL_RE.findall(text) + BRACE_POSITIONAL_LABEL_RE.findall(text)

# The subset of quarto_structure_check.py's finding kinds decidable from chunk code alone —
# label prefix, caption placement, the obsolete quarto.version hack — independent of whether
# prose or a render exist yet. `typed-ref`, `orphan-label` and `dangling-ref` are excluded: they
# depend on prose the writer has not drafted at `post coder` / `pre writer` time, so gating on
# them here would couple the coder stage to work that is not the coder's to close.
CHUNK_STRUCTURE_KINDS = {"label-prefix", "caption-in-r", "quarto-version-hack"}
CHUNK_FINDING_RE = re.compile(r":\d+: \[(" + "|".join(CHUNK_STRUCTURE_KINDS) + r")\] (.+)$")

def chunk_structure_findings(root: Path, ms: Path) -> List[str]:
    """The `chunk` predicate's `n >= min` count cannot fail on prefix correctness — a manuscript
    with 34 correct `tbl-*` chunks and one stray `tab-*` chunk still has ≥ 1 `tbl-*` label
    (Phase 1.2). This asks the linked project's own quarto_structure_check.py instead, the same
    script `/tools commit` already runs, so the two never disagree about what native Quarto
    structure means."""
    script = root / ".claude" / "scripts" / "quarto_structure_check.py"
    if not script.exists(): return ["quarto_structure_check.py: .claude/scripts/quarto_structure_check.py not linked"]
    p = subprocess.run([sys.executable, str(script), str(ms.relative_to(root))], cwd=root, capture_output=True, text=True)
    return [f"[{m.group(1)}] {m.group(2)}" for ln in p.stdout.splitlines() if (m := CHUNK_FINDING_RE.search(ln))]

SOURCE_CALL_RE = re.compile(r"(?<![.\w])source\s*\(")

def source_calls(ms: Path) -> List[int]:
    """INV-19b: no `source()` call inside any chunk — the one construct
    content-invariants.md attributed to the lint hook although the lint hook never checked
    for it (tested: seven prohibited constructs planted in one chunk, `source()` was the only
    one of seven lint-scripts.sh missed). Reuses qmd_chunks.py's own chunk-body extraction —
    its stated purpose is exactly this: line numbers identical to the .qmd source (Phase 1.4).
    Comment-only lines are skipped, matching lint-scripts.sh's convention for the sibling
    INV-19a checks."""
    import qmd_chunks
    lines = qmd_chunks.extract(ms.read_text().split("\n"))
    return [i + 1 for i, l in enumerate(lines) if not l.lstrip().startswith("#") and SOURCE_CALL_RE.search(l)]

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

RENDER_WARNING_RE = re.compile(r"WARNING.*?(?:crossref|cross-reference)", re.I)

def do_render(root: Path, target: Path) -> Tuple[bool, str]:
    """`returncode == 0` is not "the render is clean": tested on Quarto 1.9.37, a dangling
    `@tbl-`/`@fig-` produces `WARNING … Unable to resolve crossref @tbl-x` and still exits 0.
    Raw LaTeX citation/reference macros produce no warning at all — that case is not caught
    here; it needs quarto_structure_check.py's source-level `dangling-ref`/`label-prefix` checks, which the
    `chunk` predicate already wires in (Phase 1.2). This function closes the half the exit code
    silently passed: an unresolved cross-reference that DOES surface, in the log, as a warning
    quarto itself chose not to fail on (Phase 1.3)."""
    p = subprocess.run(["quarto", "render", str(target.relative_to(root))], cwd=root, capture_output=True, text=True)
    out = p.stdout + p.stderr
    lines = out.strip().splitlines()
    if p.returncode != 0:
        return False, lines[-1] if lines else ""
    warn = RENDER_WARNING_RE.search(out)
    if warn:
        return False, f"exit 0 but {warn.group(0).strip()}"
    return True, ""

def producer_hint(pred: Dict[str, Any], ok: bool) -> str:
    """The `— run `/skill`` tail on a failing predicate. Shared by run_preds() and the
    `any_of` branch of evaluate(): `producer` is declared PER PREDICATE, and an any_of's
    branches carry their own, so composing a description without consulting each branch's
    key silently drops exactly the hint the user needs (strategist declared /lit-position
    and /discover data on its two branches and printed neither)."""
    return f" — run `{pred['producer']}`" if (not ok and pred.get("producer")) else ""

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
        # record-score refuses a --report path that does not exist (Phase 2.3), so this can only
        # go missing after the fact — moved, cleaned up, or a project gate touched it. Either way
        # the state file's own audit trail would be pointing at nothing.
        report = ((st.get("components") or {}).get(comp) or {}).get("report")
        if report and not (root / report).is_file():
            return False, ran + f", but its recorded report {report} no longer exists on disk"
        return True, ran + f", {comp} scored at {at} (creator {a}, critic {c})"
    if t == "prose-check":
        script = root / ".claude" / "scripts" / "prose_number_check.py"
        if not script.exists(): return False, "prose-check: .claude/scripts/prose_number_check.py not linked"
        p = subprocess.run([sys.executable, str(script), str(ctx.ms.relative_to(root))], cwd=root, capture_output=True, text=True)
        return p.returncode == 0, "prose_number_check.py exit " + str(p.returncode)
    if t == "chunk":
        n = sum(1 for l in chunk_labels(ctx.ms) if fnmatch.fnmatch(l, pred["label_glob"]))
        ok = n >= int(pred["min"])
        desc = f"chunks {pred['label_glob']} ({n} found, need {pred['min']})"
        if not ok: return False, desc
        bad = chunk_structure_findings(root, ctx.ms)
        if bad: return False, desc + f"; but quarto_structure_check.py: {'; '.join(bad[:2])}" + (f" (+{len(bad)-2} more)" if len(bad) > 2 else "")
        return True, desc
    if t == "no-source":
        hits = source_calls(ctx.ms)
        if hits: return False, f"no-source: source() at line(s) {', '.join(str(h) for h in hits)} (INV-19)"
        return True, "no-source: clean (INV-19)"
    if t == "any_of":
        results = [(q, evaluate(q, ctx, post)) for q in pred["of"]]
        passed = any(ok for _, (ok, _d) in results)
        return passed, "any of: " + " | ".join(
            d + ("" if passed else producer_hint(q, ok)) for q, (ok, d) in results)
    return False, f"unknown predicate {t}"

def eval_preds(kind: str, agent: str, root: Path, reg) -> List[Tuple[bool, str]]:
    """Every verdict for `pre`/`post <agent>`, as (ok, line). `post` auto-appends `critic-ran`
    for any agent with a critic (see the predicate). Shared by run_preds() and next_report()."""
    e = reg["agents"][agent]; ctx = Ctx(root, reg, agent)
    preds = list(e["requires"] if kind == "pre" else e["produces"])
    if kind == "post" and rl.critic_of(reg, agent) and not any(p["type"] == "critic-ran" for p in preds):
        preds.append({"type": "critic-ran"})
    out: List[Tuple[bool, str]] = []
    for p in preds:
        ok, desc = evaluate(p, ctx, post=(kind == "post"))
        out.append((ok, desc + producer_hint(p, ok)))
    return out

def run_preds(kind: str, agent: str, root: Path, reg) -> int:
    if agent not in reg["agents"]: sys.exit(f"pipeline.py: {agent!r} is not in the registry")
    rc = 0
    for ok, line in eval_preds(kind, agent, root, reg):
        print(("ok      " if ok else "MISSING ") + line)
        rc |= 0 if ok else 1
    print(f"{kind} {agent}: " + ("PASS" if rc == 0 else "FAIL"))
    return rc

# ── next: where the driver starts ───────────────────────────────────────────
def stage_creators(reg, comp: str) -> List[str]:
    """The agents whose work a component scores — creators and infrastructure, never the critic
    that scores it and never the referees a component aggregates."""
    return [a for a, e in reg["agents"].items()
            if e.get("component") == comp and e.get("role") in ("creator", "infrastructure")]

def next_report(root: Path, reg) -> int:
    """One line per component stage, in the registry's component order, then `next: <stage>`.

    A stage is CLOSED when its component score postdates every completion its creators have in
    the dispatch log — or when it has a score and its creators have NO completion at all. That
    second case is adoption: the work exists, the registry's own critic scored it (record-score
    refuses any other), but it never ran under this driver, or ran on a machine whose gitignored
    log did not travel with the clone. Without it an in-progress paper reads as unstarted and
    `run` restarts at literature. It is a statement about the SCORE, not about the round: `post`
    remains the in-run gate, and a creator completion after the score reopens the stage (OPEN).

    The frontier is the last CLOSED stage. An unscored stage behind it is SKIPPED — reported,
    excluded from `overall` by renormalisation, never suggested and never faked. A conditional
    component is OPTIONAL and never suggested; the user opts in. `pre` is evaluated only until
    the first READY stage, because `pre` can render the manuscript, and a stage after the one
    about to be suggested has no claim on that cost (PENDING).
    """
    st = load_state(root); log = read_log(root)
    comps = list(reg["components"]); info: Dict[str, Tuple[Optional[str], str]] = {}
    for c in comps:
        creators = stage_creators(reg, c)
        entry = (st.get("components") or {}).get(c) or {}
        at = entry.get("at")
        last = {a: last_completion(log, a) for a in creators}
        newest_agent = max((a for a in creators if last[a]), key=lambda a: last[a], default=None)
        newest = last[newest_agent] if newest_agent else None
        if at is not None and (newest is None or at > newest):
            tail = (" (no creator completion logged — adopted or cloned; see "
                    ".claude/skills/pipeline/references/adopt.md)" if newest is None
                    else f" (creator {newest_agent} completed at {newest})")
            info[c] = ("CLOSED", f"{entry.get('score')} by {entry.get('critic')} at {at}" + deduction_note(entry) + tail)
        elif newest is not None:
            scorer = reg["components"][c].get("scored_by")
            d = f"{newest_agent} completed at {newest}; no {c} score after it — dispatch {scorer} and record-score"
            if at is None and st.get("sections") and scorer == (reg["agents"].get("writer") or {}).get("critic"):
                d += f" ({len(st['sections'])} section score(s) exist; a whole-manuscript score is needed)"
            info[c] = ("OPEN", d)
        else:
            info[c] = (None, "")
    # The frontier is the last CLOSED stage — only a score moves it. An OPEN round is
    # unfinished work the user started, so it is suggested ahead of any READY stage and no
    # `pre` is evaluated while one exists; but it does NOT move the frontier: a standalone
    # verifier run in a project with nothing scored would otherwise mark every earlier stage
    # SKIPPED on the strength of a log line (observed on a real project, 2026-09-10).
    closed = [i for i, c in enumerate(comps) if info[c][0] == "CLOSED"]
    frontier = closed[-1] if closed else -1
    opens = [c for c in comps if info[c][0] == "OPEN"]
    rows: List[Tuple[str, str, str]] = []; found: Optional[str] = opens[0] if opens else None; blocked = False
    for i, c in enumerate(comps):
        status, detail = info[c]; cond = bool(reg["components"][c].get("conditional"))
        if status in ("CLOSED", "OPEN"): rows.append((status, c, detail)); continue
        # Conditional first: behind the frontier or ahead of it, it is the user's opt-in, and
        # SKIPPED would present it as a gap to close.
        if cond:
            rows.append(("OPTIONAL", c, "conditional — never suggested; opt in from the driver")); continue
        if i < frontier:
            rows.append(("SKIPPED", c, f"unscored, behind the frontier ({comps[frontier]} is closed) — "
                                       "excluded from overall; run its stage to score it")); continue
        if found is not None:
            rows.append(("PENDING", c, "not evaluated — another stage is suggested first")); continue
        ready: Optional[str] = None; misses: List[str] = []
        for a in stage_creators(reg, c):
            res = eval_preds("pre", a, root, reg)
            if all(ok for ok, _ in res): ready = a; break
            misses.append(f"pre {a}: " + "; ".join(l for ok, l in res if not ok))
        if ready: rows.append(("READY", c, f"pre {ready}: PASS")); found = c
        else: rows.append(("BLOCKED", c, " | ".join(misses) or "no creator declared")); blocked = True
    for status, c, detail in rows: print(f"{status:9s} {c:12s} {detail}")
    if found:
        print(f"next: {found} ({', '.join(stage_creators(reg, found))})"); return 0
    if blocked:
        print("next: none — nothing is ready; see BLOCKED above"); return 1
    print("next: none — every component stage is closed"); return 0

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
    sub.add_parser("manuscript"); sub.add_parser("fresh"); sub.add_parser("next")
    for k in ("pre", "post"): sub.add_parser(k).add_argument("agent")
    sc = sub.add_parser("score"); sc.add_argument("--gate", choices=sorted(GATES))
    st = sub.add_parser("state"); st.add_argument("op", choices=["init", "validate", "show", "record-score", "strike", "set-blocked", "clear-blocked"])
    st.add_argument("args", nargs="*"); st.add_argument("--critic"); st.add_argument("--report"); st.add_argument("--scope")
    st.add_argument("--deductions", type=float, help="record-score: the critic's unfloored deduction total")
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
    if a.cmd == "next": return next_report(root, reg)
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
        for c, w in used.items(): print(f"{c:12s} {stt['components'][c]['score']:6.1f}  weight {w:5.1f}" + deduction_note(stt['components'][c]))
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
            if len(a.args) != 2 or not a.critic or not a.report: sys.exit("usage: state record-score <component> <score> --critic X --report P [--deductions N] [--scope section:NAME]")
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
            # A critic without Write can only get its report onto disk via the dispatching
            # skill (.claude/rules/agents.md §2). Accepting a --report path that does not exist lets a
            # stage close on a review that exists nowhere but a discarded subagent transcript —
            # the state file's own audit trail would be a lie (Phase 2.3).
            if not (root / a.report).is_file():
                print(f"record-score: --report {a.report} does not exist — save the critic's "
                      f"report before recording its score, not after"); return 1
            if a.deductions is not None:
                # The total must be the score's own arithmetic: a critic starts at 100 and floors at
                # 0. Anything else is a transcription slip between report and command line, and
                # recording it would put two disagreeing numbers in the replication record.
                if a.deductions < 0:
                    print("record-score: --deductions must be ≥ 0 (the total points deducted)"); return 1
                if abs(score - max(0.0, 100.0 - a.deductions)) > 0.05:
                    print(f"record-score: score {score:g} does not match --deductions {a.deductions:g} "
                          f"(expected {max(0.0, 100.0 - a.deductions):g} = max(0, 100 − deductions))"); return 1
            entry = {"score": score, "critic": a.critic, "report": a.report, "at": now()}
            if a.deductions is not None: entry["deductions"] = a.deductions
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
