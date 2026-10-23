# Design lock and prose binding — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A paper proceeds only on a design the author has signed in chat and that has passed
power and size checks, all of it recorded in the manuscript's own front matter. Every
result-describing word is generated from, or guarded by, the model objects. A re-estimation
mechanically reopens the reviews it invalidates and blocks manuscript commits until they are
re-scored. Every design change is recorded once and disclosed by a generated table; changing a
model after seeing results is normal practice, and the pipeline records it rather than treating
it as a defect. Reviews converge through a finding ledger, and unattended runs log their rulings.

**Architecture:**
- The design lives in a `design:` front-matter block of the single `.qmd`. The lock is a hash of
  that block's normalised text, kept in `quality_reports/design_lock.json`.
- The author approves signing or unlocking in chat with one exact line. A `UserPromptSubmit` hook
  turns that line into a one-time token; `pipeline.py design sign|unlock` refuses without a fresh,
  unused token for the block as it stands. A PreToolUse hook (`design-guard`) stops agents from
  editing a signed block, from writing the lock, token or record files, and from running
  sign/unlock without a token.
- Every amendment is appended to `quality_reports/design_amendments.csv` (and a readable `.md`);
  a `tbl-design-changes` chunk renders the CSV in the paper.
- Claim helpers (base R, `rc_` prefix) are pasted into the setup chunk from a template. They key
  every chunk cache on the design and data hashes, and write a results fingerprint that hashes
  every fitted model object in the environment, found by class.
- `pipeline.py` compares that fingerprint against every score. A stale manuscript score blocks
  manuscript commits through a git pre-commit hook (`hooks/git/pre-commit`), except the commit that lands
  the re-estimation. It also owns the finding ledger, the rulings log and the questions file.

**Tech Stack:** Python 3.9 stdlib (the `scripts/pipeline.py` convention), bash, base R plus
`rmarkdown`, Quarto/knitr, pytest/unittest.

**Spec:** `docs/superpowers/specs/2026-10-12-design-lock-and-prose-binding-design.md`. Its §0
("Author rulings, 2026-10-17") overrides every other section; this plan follows §0 throughout.

## Global Constraints

- **One manuscript (core rule 1).** No results file, no analysis script and no `source()` in any
  shipped manuscript code. Helpers are pasted into the setup chunk, never sourced. Power and size
  checks live in `explorations/`, never in the manuscript (`rules/readable-code.md` §5).
- **Python scripts:** stdlib only, Python 3.9 (`pipeline.py` header). No PyYAML.
- **Shipped R (helpers, fixture, rule snippets) follows `rules/readable-code.md`:** every exported
  name carries the `rc_` prefix; no base/builtin name is assigned at top level, and none is used
  as a local name either (`~/.claude/references/r-naming.md`; run its grep on every shipped `.R`,
  `.R.txt` and `.qmd` before committing); no `sapply()`, no `T`/`F`, no `==` on floats, no
  `print()` for status; every `stopifnot()` carries a message; no wording scanners in R.
- **Significance convention, fixed (spec §0.2):** `*` p ≤ 0.10, `**` p ≤ 0.05, `***` p ≤ 0.01.
  "Statistically significant" means p ≤ 0.10 and the prose states the level. The design block
  carries no α and no verdict words. A journal profile that forbids stars or mandates other
  cutoffs wins for that journal.
- **Post-results changes are standard practice (spec §0.1).** No "results seen" field, flag or
  record anywhere; no text that treats a change after estimation as a defect. Pre-analysis-plan
  templates stay for papers that have an actual PAP.
- **Live evals:** never pass, add or raise a timeout (`EVAL_TIMEOUT=0` / `LIVE_TIMEOUT=0`). A slow
  run is left to finish and diagnosed afterwards.
- **Nothing project-specific ships:** no project, journal or dataset name under
  `agents/ skills/ rules/ hooks/ templates/ seeds/ scripts/`, or in the fixture.
- **`./scripts/check_fork.sh` must exit 0** at Task 0 and after every task that touches the
  shipped tree. A red check is fixed in the task that caused it.
- **Every new `quality_reports/` path named in the shipped tree** has an `AP_ALLOW` row in
  `scripts/check_refs.py` (Task 1 adds them all), or `artifact-paths` fails.
- **Commits:** never `--no-verify`. Local commits only; no push. Each commit message ends with the
  trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Work in the git worktree** `.claude/worktrees/design-lock`, never on the linked working copy
  (`~/Academic/research-claude`): every save there is live in all six papers. Merge to `main`
  only in Task 16.
- **Hooks fail open on internal error** (the existing hook convention). The `pipeline.py`
  predicates and `commit-check` fail closed.
- **The git hooks ship as `hooks/git/pre-commit` and `hooks/git/post-commit`,** installed with
  `core.hooksPath = .claude/hooks/git`. Every Claude-hook auditor, test and wiring script skips
  `hooks/git/`.
- **Core rules are numbered from 13:** `rules/core.md` on `main` holds rules 1–12 (12 = readable
  code). Re-read it before editing.

## Review Focus

1. **A manuscript with no `design:` block** (a paper not yet retrofitted). The design-lock
   predicate passes as `NOT-RETROFITTED`; the stricter wording gate is off; staleness is off (no
   fingerprint). The surface scans (title, abstract, math, notes, letter) and the threshold
   warning apply to every paper. Once a `design_lock.json` exists, every check fails closed.
   Tests: Tasks 3, 7, 8 and 12.
2. **The author token** (Task 2). Only a whole line reading `approve design sign` or
   `approve design unlock: <reason>` counts, outside code fences and quotes, exactly once per
   message. The token is bound to the block's hash at approval, expires after 30 minutes, is
   revoked by the author's next message, and is spent by one successful command. Agents cannot
   write it (design-guard, protect-files). Known limit: a Bash command that builds the token path
   from fragments evades the text match; the hash binding and one-message lifetime bound the
   damage. Unverified: whether a `claude -p` prompt fires `UserPromptSubmit`; live-eval prompts
   must never contain an approval line.
3. **Front-matter noise:** CRLF line endings, tabs, comments, blank lines. The design hash ignores
   comments, trailing whitespace and CRLF, and changes on any value change. Test: Task 1.
4. **An edit to YAML outside the `design:` block while locked** (title, date, format) is allowed.
   Test: Task 4.
5. **The fingerprint** hashes every fitted model object in the global environment, found by class,
   including a `fixest_multi` and a robustness model named in no hypothesis; it stops when a
   hypothesis `spec:` names a missing object. Test: Task 5.
6. **The re-estimation commit.** A commit whose staged `render_fingerprint.json` differs from
   HEAD's in `estimates_hash`, `data_hash` or `design_hash` passes while stale (with a WARN); every
   other manuscript commit is refused while the manuscript score is stale. Stale strategy and
   referee scores reopen their stages (`post`, `next`, score gates) but never block a commit
   (author ruling 2026-10-17).
   Tests: Task 12. Tested: in a checkout where `core.hooksPath` names a missing directory (a
   fresh worktree without the links), git commits run no hook and exit 0, so `check_install`
   fails `git-hooks-path` there.
7. **A commit in a repo with no declared manuscript, or one that doesn't stage the manuscript or
   the fingerprint.** `commit-check` exits 0 fast. Test: Task 12.
8. **Rulings.** A ledger decline or a proposal accept/reject always writes a rulings-log row; a
   change to `design:` and a contradiction of a recorded author decision are hard stops written to
   `questions_for_author.md`. Tests: Task 9.

---

### Task 0: Worktree and baseline

**Files:** none (environment).

- [ ] **Step 1:** Confirm the worktree: `git -C .claude/worktrees/design-lock status` shows branch
  `feat/design-lock-prose-binding`, rebased on `main`. Every later path in this plan is relative
  to the worktree root. If the worktree is missing, create it with superpowers:using-git-worktrees.
- [ ] **Step 2:** Record the baseline.

```bash
python3 -m pytest -q tests 2>&1 | tail -3 > /tmp/dl_baseline_pytest.txt
./scripts/check_fork.sh > /tmp/dl_baseline_fork.txt 2>&1; echo "check_fork exit $?"
```

Expected: `check_fork exit 0`. Note the pytest pass count. If `check_fork.sh` is not green, stop
and report: this plan requires exit 0 throughout.

---

### Task 1: `design_block.py` — extract, normalise, hash and diff the design block

**Files:**
- Create: `scripts/design_block.py`
- Modify: `scripts/SHIPPED` (add `design_block.py`)
- Modify: `scripts/check_refs.py` (`AP_ALLOW`: one row per artifact this plan introduces)
- Test: `tests/test_design_block.py`

**Interfaces:**
- Produces:
  - `front_matter_lines(text) -> Optional[List[Tuple[int, str]]]`: (1-based line number, line)
    for each line between the opening `---` and the closing `---`/`...`.
  - `design_block(text) -> Optional[str]`: raw block text starting at `design:`.
  - `design_span(text) -> Optional[Tuple[int, int]]`: first and last file line of the block.
  - `design_hash(text) -> Optional[str]`: sha256 hex of the normalised block, None without one.
  - `check_entry(text, name) -> Optional[str]`, `has_check(text, name) -> bool`,
    `check_field(text, name, key) -> Optional[str]`,
    `check_number(text, name, key) -> Optional[float]`: read `design.checks.<name>`.
  - `amendment_rows(old_block, new_block, date, reason) -> List[Dict[str, str]]`, keys
    `date, field, old, new, reason`; `needs_rerun(rows, old_block, new_block) -> bool`;
    `checks_changed(rows) -> bool`.
  - `append_amendments(root, rows, heading, diff=None) -> None`; `amendment_count(root) -> int`.
  - `manuscript_path(root) -> Optional[Path]` (the one `manuscript:` line of CLAUDE.md).
  - `LOCK_REL`, `AMEND_CSV_REL`, `AMEND_MD_REL`, `AMEND_FIELDS`; `read_lock(root)`,
    `write_lock(root, lock)`.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/test_design_block.py
import csv, pathlib, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import design_block as db

BASE = """---
title: "T"
design:
  inference: {rule: cluster-robust, cluster: region, id: INF-1}   # field standard
  treatment:
    definition: "first permit issued under the new rule"
    date: 2020-01-01
    source: {cite: key2024, page: 12, quote: "the rule took effect"}
  sample: ["units observed before and after the rule"]
  hypotheses:
    H1: {estimand: "ATT", outcome: y, spec: m_h1, direction: negative}
  checks:
    power: {mde: 0.02, target_effect: 0.03, file: explorations/power.qmd}
    size: {rejection_at_0.10: 0.104, reps: 500, file: explorations/size.qmd}
format: pdf
---

Body text.
"""

class TestBlock(unittest.TestCase):
    def test_extracts_block_only(self):
        b = db.design_block(BASE)
        self.assertTrue(b.startswith("design:"))
        self.assertNotIn("format:", b); self.assertNotIn("title:", b)
    def test_span(self):
        self.assertEqual(db.design_span(BASE), (3, 14))
    def test_no_front_matter_or_block(self):
        self.assertIsNone(db.design_block("Body only\n"))
        self.assertIsNone(db.design_hash("---\ntitle: x\n---\n"))
    def test_hash_ignores_comments_ws_crlf(self):
        h = db.design_hash(BASE)
        noisy = BASE.replace("   # field standard", "").replace("\n", "\r\n")
        noisy = noisy.replace("  hypotheses:", "\n  # note\n  hypotheses:").replace("date: 2020-01-01", "date: 2020-01-01   ")
        self.assertEqual(db.design_hash(noisy), h)
    def test_hash_changes_on_value(self):
        self.assertNotEqual(db.design_hash(BASE.replace("cluster: region", "cluster: state")), db.design_hash(BASE))
    def test_edit_outside_block_keeps_hash(self):
        self.assertEqual(db.design_hash(BASE.replace('title: "T"', 'title: "U"')), db.design_hash(BASE))
    def test_no_alpha_or_verdicts_needed(self):
        self.assertNotIn("alpha", BASE); self.assertNotIn("verdicts", BASE)
        self.assertIsNotNone(db.design_hash(BASE))
    def test_checks(self):
        self.assertTrue(db.has_check(BASE, "power")); self.assertTrue(db.has_check(BASE, "size"))
        self.assertFalse(db.has_check(BASE.replace("    size:", "    sizz:"), "size"))
        self.assertEqual(db.check_field(BASE, "power", "file"), "explorations/power.qmd")
        self.assertEqual(db.check_number(BASE, "size", "rejection_at_0.10"), 0.104)
        self.assertEqual(db.check_number(BASE, "power", "target_effect"), 0.03)
        self.assertIsNone(db.check_number(BASE, "power", "nothing"))
    def test_amendment_rows_name_the_field(self):
        new = db.design_block(BASE.replace("cluster: region", "cluster: state"))
        rows = db.amendment_rows(db.design_block(BASE), new, "2026-10-20", "cluster at state level")
        self.assertEqual(len(rows), 1); r = rows[0]
        self.assertEqual(r["field"], "inference")
        self.assertIn("cluster: region", r["old"]); self.assertIn("cluster: state", r["new"])
        self.assertEqual((r["date"], r["reason"]), ("2026-10-20", "cluster at state level"))
    def test_needs_rerun(self):
        old = db.design_block(BASE)
        for a, b in (("cluster: region", "cluster: state"), ('"units observed', '"units always observed'),
                     ("date: 2020-01-01", "date: 2020-07-01"), ("outcome: y,", "outcome: y2,")):
            new = db.design_block(BASE.replace(a, b))
            self.assertTrue(db.needs_rerun(db.amendment_rows(old, new, "d", "r"), old, new), a)
        new = db.design_block(BASE.replace('estimand: "ATT"', 'estimand: "ATT, all cohorts"'))
        self.assertFalse(db.needs_rerun(db.amendment_rows(old, new, "d", "r"), old, new))
    def test_append_amendments_csv_and_md(self):
        r = pathlib.Path(tempfile.mkdtemp())
        rows = [{"date": "2026-10-20", "field": "inference", "old": "a, b", "new": "c | d", "reason": "why"}]
        db.append_amendments(r, rows, heading="Amendment — 2026-10-20", diff="-a\n+c")
        got = list(csv.DictReader((r / db.AMEND_CSV_REL).open()))
        self.assertEqual(list(got[0].keys()), db.AMEND_FIELDS); self.assertEqual(got[0]["new"], "c | d")
        self.assertEqual(db.amendment_count(r), 1)
        md = (r / db.AMEND_MD_REL).read_text(); self.assertIn("Amendment — 2026-10-20", md); self.assertIn("```diff", md)
    def test_manuscript_path_and_lock_roundtrip(self):
        r = pathlib.Path(tempfile.mkdtemp())
        self.assertIsNone(db.manuscript_path(r))
        (r / "CLAUDE.md").write_text("manuscript: m.qmd\n"); self.assertEqual(db.manuscript_path(r), (r / "m.qmd").resolve())
        self.assertIsNone(db.read_lock(r))
        db.write_lock(r, {"status": "signed", "hash": "abc"}); self.assertEqual(db.read_lock(r)["hash"], "abc")

if __name__ == "__main__": unittest.main()
```

- [ ] **Step 2:** Run `python3 -m pytest -q tests/test_design_block.py`. Expected: FAIL with
  `ModuleNotFoundError: design_block`.
- [ ] **Step 3: Implement.**

```python
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
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parents = [k for _, k in stack]
        if m:
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
```

- [ ] **Step 4:** In `scripts/check_refs.py`, add to `AP_ALLOW`, one row each with its reason:
  `quality_reports/design_lock.json` ("design lock — written only by `pipeline.py design`"),
  `quality_reports/design_amendments.csv` and `.md` ("design amendment record — rendered by
  `tbl-design-changes`"), `quality_reports/render_fingerprint.json` ("results fingerprint — written
  by the manuscript's `fingerprint` chunk"), `quality_reports/cold_render.json` ("`pipeline.py
  render --cold` receipt"), `quality_reports/findings_ledger.md` ("finding ledger — `pipeline.py
  ledger`"), `quality_reports/rulings_log.md` ("rulings log — `pipeline.py ruling add`"),
  `quality_reports/questions_for_author.md` ("hard-stop questions — `pipeline.py question add`"),
  `quality_reports/critic_inputs/*.md` ("`pipeline.py critic-context` file — round 2+ context").
- [ ] **Step 5:** Run `python3 -m pytest -q tests/test_design_block.py tests/test_check_refs.py`.
  Expected: all pass (12 in the new file). If `test_span` fails, check the arithmetic: the block
  runs from file line 3 (`design:`) to line 14 (the `size:` line). Fix the code, not the test.
- [ ] **Step 6: Commit.**

```bash
echo design_block.py >> scripts/SHIPPED
git add scripts/design_block.py scripts/SHIPPED scripts/check_refs.py tests/test_design_block.py
git commit -m "design_block.py: extract, hash and diff the manuscript design block; amendment CSV

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: The author's chat approval — `author_token.py` and the `design-token` hook

**Files:**
- Create: `scripts/author_token.py`; add it to `scripts/SHIPPED`
- Create: `hooks/design-token.py` (UserPromptSubmit)
- Modify: `scripts/wire_guard_hooks.py` (`WANTED` gains the hook; a `None` matcher writes a group
  with no `matcher` key; any hook under `git/` is refused)
- Modify: `seeds/settings.json` (a `UserPromptSubmit` group), `seeds/gitignore`
  (`.claude/state/design_token.json`), `scripts/check_install.sh` (`gitignore-covers` adds that
  line), `hooks/README.md` (one row)
- Test: `tests/test_design_token.py`, `tests/test_wire_guard_hooks.py`

**Interfaces:**
- Produces:
  - `TOKEN_REL = .claude/state/design_token.json`; `TTL = 30 minutes`.
  - `approval(prompt) -> Optional[Tuple[str, Optional[str]]]`: `("sign", None)` or
    `("unlock", reason)`.
  - `issue(root, op, reason, design_hash, now=None)`, `revoke_unused(root)`,
    `check(root, op, design_hash, reason=None, now=None) -> Tuple[bool, str]` (`reason=None`
    skips the unlock-reason comparison, for design-guard's pre-check), `consume(...)` (same
    signature; marks the token used on success).
  - Token JSON: `{op, reason, design_hash, issued_at, used_at}`.

**What counts as approval (exact rule; quoted in `rules/core.md` rule 13 and the hook docstring):**
- A line of the author's own message that, after trimming whitespace and ignoring case, reads
  exactly `approve design sign` or `approve design unlock: <reason>`, optionally followed by one
  `.`. The unlock reason is required and is recorded verbatim.
- Lines inside a fenced code block, and lines starting with `>`, are not read. Any other text on
  the line ("please approve design sign", "don't approve design sign") means it does not count.
- Exactly one approval line per message; two or more issue nothing.
- **Fresh** means: issued by the author's most recent message (every message without an approval
  line revokes an unused token), at most 30 minutes old, unused, for the requested operation, and
  for the `design:` block whose hash was recorded at approval. **One use:** a successful
  `design sign` or `design unlock` writes `used_at`; a used token never validates again.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/test_design_token.py
import datetime as dt, json, pathlib, shutil, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests")); sys.path.insert(0, str(ROOT / "scripts"))
from test_guard_hooks import ProjectCase
from test_design_block import BASE
import author_token as tok, design_block as dsb
HOOK = ROOT / "hooks" / "design-token.py"
T0 = dt.datetime(2026, 10, 20, 12, 0, tzinfo=dt.timezone.utc)

class TestApprovalGrammar(unittest.TestCase):
    def test_exact_lines(self):
        self.assertEqual(tok.approval("approve design sign"), ("sign", None))
        self.assertEqual(tok.approval("Looks right.\n  Approve design sign.  \n"), ("sign", None))
        self.assertEqual(tok.approval("approve design unlock: cluster at state level"),
                         ("unlock", "cluster at state level"))
    def test_not_approvals(self):
        for msg in ("approve design unlock", "please approve design sign", "> approve design sign",
                    "```\napprove design sign\n```", "I approve the design sign-off",
                    "approve design sign\napprove design sign", "don't approve design sign yet", ""):
            self.assertIsNone(tok.approval(msg), msg)

class TestTokenRules(unittest.TestCase):
    def setUp(self): self.r = pathlib.Path(tempfile.mkdtemp())
    def tearDown(self): shutil.rmtree(self.r)
    def test_one_use(self):
        tok.issue(self.r, "sign", None, "h", now=T0)
        self.assertTrue(tok.consume(self.r, "sign", "h", now=T0)[0])
        ok, why = tok.consume(self.r, "sign", "h", now=T0); self.assertFalse(ok); self.assertIn("already used", why)
    def test_expiry(self):
        tok.issue(self.r, "sign", None, "h", now=T0)
        ok, why = tok.check(self.r, "sign", "h", now=T0 + dt.timedelta(minutes=31)); self.assertFalse(ok); self.assertIn("expired", why)
    def test_op_hash_and_reason_must_match(self):
        tok.issue(self.r, "unlock", "why", "h", now=T0)
        self.assertFalse(tok.check(self.r, "sign", "h", now=T0)[0])
        self.assertIn("different design block", tok.check(self.r, "unlock", "other", reason="why", now=T0)[1])
        self.assertIn("reason", tok.check(self.r, "unlock", "h", reason="not why", now=T0)[1])
        self.assertTrue(tok.check(self.r, "unlock", "h", reason="why", now=T0)[0])
    def test_missing(self):
        ok, why = tok.check(self.r, "sign", "h"); self.assertFalse(ok); self.assertIn("no author token", why)

class TestHook(ProjectCase):
    def setUp(self): super().setUp(); self.ms.write_text(BASE)
    def prompt(self, text):
        return self.run_hook(HOOK, {"hook_event_name": "UserPromptSubmit", "prompt": text})
    def token(self):
        p = self.proj / tok.TOKEN_REL
        return json.loads(p.read_text()) if p.exists() else None
    def test_issues_on_approval(self):
        out = self.prompt("approve design sign")
        self.assertEqual(self.token()["op"], "sign"); self.assertEqual(self.token()["design_hash"], dsb.design_hash(BASE))
        self.assertIn("design-token", out)
    def test_next_message_revokes_unused(self):
        self.prompt("approve design sign"); self.prompt("actually, wait")
        self.assertIsNone(self.token())
    def test_used_token_kept_as_record(self):
        self.prompt("approve design sign"); tok.consume(self.proj, "sign", dsb.design_hash(BASE))
        self.prompt("thanks"); self.assertIsNotNone(self.token()["used_at"])
    def test_no_claude_md_is_silent(self):
        (self.proj / "CLAUDE.md").unlink(); self.assertEqual(self.prompt("approve design sign"), "")

if __name__ == "__main__": unittest.main()
```

  `tests/test_wire_guard_hooks.py`: `wire({"hooks": {}})` adds a `UserPromptSubmit` group with no
  `matcher` key holding `design-token.py`; a second `wire()` adds nothing; a `WANTED` entry naming
  `git/pre-commit` raises `ValueError`.
- [ ] **Step 2:** Run `python3 -m pytest -q tests/test_design_token.py tests/test_wire_guard_hooks.py`.
  Expected: FAIL (`ModuleNotFoundError: author_token`).
- [ ] **Step 3: Implement** `scripts/author_token.py`.

```python
#!/usr/bin/env python3
"""author_token.py — the author's one-time approval for `pipeline.py design sign|unlock` (spec §0.3).

The author approves in chat; hooks/design-token.py (UserPromptSubmit) turns the approval line
into this token, and `design sign|unlock` refuses without a fresh one. An unattended run has no
author message, so it cannot sign or unlock. The approval grammar and the freshness rules are
stated in rules/core.md rule 13; keep the two in step.
"""
from __future__ import annotations
import datetime as dt, json, re
from pathlib import Path
from typing import Optional, Tuple

TOKEN_REL = Path(".claude") / "state" / "design_token.json"
TTL = dt.timedelta(minutes=30)
APPROVAL_RE = re.compile(r"^approve design (sign|unlock)(?:\s*:\s*(\S.*?))?\.?$", re.I)
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")

def _now(now: Optional[dt.datetime]) -> dt.datetime:
    return now or dt.datetime.now(dt.timezone.utc)

def approval(prompt: str) -> Optional[Tuple[str, Optional[str]]]:
    found = []; in_fence = False
    for raw in (prompt or "").replace("\r\n", "\n").split("\n"):
        if FENCE_RE.match(raw):
            in_fence = not in_fence; continue
        m = None if in_fence else APPROVAL_RE.match(raw.strip())
        if m:
            found.append((m.group(1).lower(), (m.group(2) or "").strip() or None))
    if len(found) != 1:
        return None
    op, reason = found[0]
    if op == "unlock" and not reason:
        return None
    return op, (reason if op == "unlock" else None)

def _path(root: Path) -> Path:
    return root / TOKEN_REL

def _read(root: Path) -> Optional[dict]:
    p = _path(root)
    return json.loads(p.read_text()) if p.exists() else None

def issue(root: Path, op: str, reason: Optional[str], design_hash: Optional[str], now: Optional[dt.datetime] = None) -> None:
    p = _path(root); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"op": op, "reason": reason, "design_hash": design_hash,
                             "issued_at": _now(now).isoformat(), "used_at": None}, indent=2) + "\n")

def revoke_unused(root: Path) -> None:
    t = _read(root)
    if t is not None and t.get("used_at") is None:
        _path(root).unlink()

def check(root: Path, op: str, design_hash: Optional[str], reason: Optional[str] = None,
          now: Optional[dt.datetime] = None) -> Tuple[bool, str]:
    t = _read(root)
    if t is None:
        return False, f"no author token — the author approves in chat with the line `approve design {op}`" + (": <reason>`" if op == "unlock" else "`")
    if t.get("used_at"):
        return False, f"the author token was already used at {t['used_at']} — the author approves again in chat"
    if t.get("op") != op:
        return False, f"the author approved `design {t.get('op')}`, not `design {op}`"
    if _now(now) - dt.datetime.fromisoformat(t["issued_at"]) > TTL:
        return False, "the author token expired (30 minutes) — the author approves again in chat"
    if t.get("design_hash") != design_hash:
        return False, "the author approved a different design block — show the author the block as it stands and ask again"
    # reason=None skips this comparison (design-guard's pre-check); the CLI always passes --reason.
    if op == "unlock" and reason is not None and " ".join(reason.split()) != " ".join((t.get("reason") or "").split()):
        return False, f"--reason must be the author's reason, verbatim: {t.get('reason')!r}"
    return True, t["issued_at"]

def consume(root: Path, op: str, design_hash: Optional[str], reason: Optional[str] = None,
            now: Optional[dt.datetime] = None) -> Tuple[bool, str]:
    ok, why = check(root, op, design_hash, reason, now)
    if ok:
        t = _read(root); t["used_at"] = _now(now).isoformat()
        _path(root).write_text(json.dumps(t, indent=2) + "\n")
    return ok, why
```

  `hooks/design-token.py`:

```python
#!/usr/bin/env python3
"""design-token.py — UserPromptSubmit: the author's chat approval becomes a one-time token.

Spec §0.3. A line `approve design sign` or `approve design unlock: <reason>` in the author's own
message issues .claude/state/design_token.json for the design block as it stands now; any other
message revokes an unused token. `pipeline.py design sign|unlock` spends it. Never blocks a
prompt. Fails open on internal error.

Hook Event: UserPromptSubmit
"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import author_token as tok
import design_block as dsb

def main() -> int:
    payload = json.load(sys.stdin)
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")).resolve()
    if not (root / "CLAUDE.md").exists():
        return 0
    found = tok.approval(payload.get("prompt", ""))
    if found is None:
        tok.revoke_unused(root); return 0
    op, reason = found
    ms = dsb.manuscript_path(root)
    tok.issue(root, op, reason, dsb.design_hash(ms.read_text()) if ms and ms.exists() else None)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext":
        f"design-token: the author approved `design {op}` in this message. The token is good for one "
        "`pipeline.py design " + op + "` this turn, for the design block exactly as it stands now."}}))
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception: sys.exit(0)
```

  - `scripts/wire_guard_hooks.py`: add `("UserPromptSubmit", None, "design-token.py")` to
    `WANTED`. In `wire()`, a `None` matcher finds or creates a group with no `matcher` key (never
    `"matcher": null`). At module load, `if any(h.startswith("git/") for _, _, h in WANTED): raise
    ValueError("hooks/git/ holds git hooks, not Claude hooks")`.
  - `seeds/settings.json`: a `"UserPromptSubmit"` array with one group (no matcher) running
    `"$CLAUDE_PROJECT_DIR"/.claude/run-hook.sh design-token.py`, timeout 5.
  - `seeds/gitignore`: under "Local-only Claude state", add `.claude/state/design_token.json`.
    `scripts/check_install.sh` section 8: add the same line to the `gitignore-covers` list.
  - `hooks/README.md`: row `design-token.py | UserPromptSubmit | Turns the author's chat approval
    line into a one-time token for \`pipeline.py design sign|unlock\`; revokes an unused token on the
    next message. Never blocks`.
- [ ] **Step 4: Verify the payload shape live.** Unverified until run: that the `UserPromptSubmit`
  payload carries the message as `prompt`. In a scratch project wired with the seed, run
  `claude -p "approve design sign"` (no timeout) and confirm `.claude/state/design_token.json`
  appears; if it does not, read the hooks reference, fix the key and record the result as
  `tested:` in the hook docstring. Never put an approval line in a live-eval prompt.
- [ ] **Step 5:** Run `python3 -m pytest -q tests/test_design_token.py tests/test_wire_guard_hooks.py tests/test_check_install.py tests/test_check_refs.py && ./scripts/check_fork.sh >/dev/null; echo $?`.
  Expected: all pass; `0`.
- [ ] **Step 6: Commit.**

```bash
echo author_token.py >> scripts/SHIPPED
git add scripts/author_token.py scripts/SHIPPED hooks/design-token.py hooks/README.md scripts/wire_guard_hooks.py \
  seeds/settings.json seeds/gitignore scripts/check_install.sh tests/test_design_token.py tests/test_wire_guard_hooks.py
git commit -m "design-token hook: the author's chat approval issues a one-time token for design sign|unlock

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `pipeline.py design status|sign|unlock|seed-amendment` and the `design-lock` predicate

**Files:**
- Modify: `scripts/pipeline.py` (new `design` subcommand; new predicate in `evaluate`)
- Modify: `scripts/registry_lib.py` (`PRED_TYPES` += `"design-lock"`)
- Modify: `scripts/render_registry.py` (`pred()` case for `design-lock`), then re-render
  `rules/permissions.md`
- Modify: `rules/registry.yaml` (`- type: design-lock` in the `requires` of `coder` and `writer`)
- Modify: `rules/lifecycle.md` (predicate table: a `design-lock` row and the missing `no-source`
  row)
- Test: `tests/test_design_lock.py`

**Interfaces:**
- Consumes: Task 1 (`design_hash`, `design_block`, `check_*`, `amendment_rows`, `needs_rerun`,
  `checks_changed`, `append_amendments`, `read_lock`, `write_lock`), Task 2 (`consume`).
- Produces:
  - `design_state(root, ms) -> Tuple[str, str]`; status is one of `NOT-RETROFITTED`, `UNSIGNED`,
    `SIGNED`, `CHANGED`, `UNLOCKED`.
  - `design status`: exit 0 only for `SIGNED` or `NOT-RETROFITTED`.
  - `design sign --signer NAME`: needs a fresh `sign` token. Refuses unless `checks.power` and
    `checks.size` are present, each names an existing `file:` under `explorations/`, the MDE is no
    larger than `|target_effect|`, and the size rejection rate at 0.10 is within 0.07–0.13. After
    an unlock it appends the amendment rows (CSV) and entry (MD), and refuses an amendment that
    touches the inference rule, sample, treatment or an outcome unless `design.checks` changed too.
  - `design unlock --reason TEXT`: needs a fresh `unlock` token whose reason equals `TEXT`.
  - `design seed-amendment --date --field --old --new --reason`: only while `UNSIGNED` (retrofit,
    spec §8 step 1).
  - Predicate `{type: design-lock}`: passes on `SIGNED` or `NOT-RETROFITTED`.
  - Lock JSON: `{status, hash, block, signed_at, signer, approved_at}`, plus `reason` and
    `unlocked_at` while unlocked.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/test_design_lock.py
import csv, json, pathlib, shutil, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
PIPE = ROOT / "scripts" / "pipeline.py"
sys.path.insert(0, str(ROOT / "tests")); sys.path.insert(0, str(ROOT / "scripts"))
from test_design_block import BASE
import author_token as tok, design_block as dsb

def run(*a, root):
    p = subprocess.run([sys.executable, str(PIPE), "--root", str(root), *a], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

class DesignCase(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
        (self.t / "CLAUDE.md").write_text("manuscript: m.qmd\n")
        (self.t / "rules").mkdir(); shutil.copy(ROOT / "rules" / "registry.yaml", self.t / "rules" / "registry.yaml")
        (self.t / "explorations").mkdir()
        for f in ("power.qmd", "size.qmd"): (self.t / "explorations" / f).write_text("---\ntitle: check\n---\n")
        self.ms = self.t / "m.qmd"; self.ms.write_text(BASE)
    def tearDown(self): shutil.rmtree(self.t)
    def approve(self, op, reason=None):        # stands in for hooks/design-token.py
        tok.issue(self.t, op, reason, dsb.design_hash(self.ms.read_text()))
    def sign(self):
        self.approve("sign"); return run("design", "sign", "--signer", "author", root=self.t)
    def unlock(self, reason):
        self.approve("unlock", reason); return run("design", "unlock", "--reason", reason, root=self.t)
    def edit(self, old, new):
        self.ms.write_text(self.ms.read_text().replace(old, new))
    def status(self):
        return run("design", "status", root=self.t)

    def test_not_retrofitted_passes(self):
        self.ms.write_text("---\ntitle: x\n---\nbody\n")
        rc, out = self.status(); self.assertEqual(rc, 0); self.assertIn("NOT-RETROFITTED", out)
    def test_unsigned_fails(self):
        rc, out = self.status(); self.assertEqual(rc, 1); self.assertIn("UNSIGNED", out)
    def test_sign_refused_without_token(self):
        rc, out = run("design", "sign", "--signer", "author", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("no author token", out)
    def test_sign_then_signed_and_token_spent(self):
        rc, out = self.sign(); self.assertEqual(rc, 0, out)
        self.assertIn("SIGNED", self.status()[1])
        self.assertIsNotNone(json.loads((self.t / tok.TOKEN_REL).read_text())["used_at"])
    def test_token_for_another_block_refused(self):
        self.approve("sign"); self.edit("cluster: region", "cluster: state")
        rc, out = run("design", "sign", "--signer", "author", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("different design block", out)
    def test_sign_requires_checks(self):
        for old, new, msg in (("    size:", "    sizz:", "checks.size missing"),
                              ("explorations/size.qmd", "explorations/nope.qmd", "does not exist"),
                              ("rejection_at_0.10: 0.104", "rejection_at_0.10: 0.164", "outside"),
                              ("mde: 0.02", "mde: 0.05", "exceeds")):
            with self.subTest(msg=msg):
                self.ms.write_text(BASE.replace(old, new)); self.approve("sign")
                rc, out = run("design", "sign", "--signer", "a", root=self.t)
                self.assertEqual(rc, 1); self.assertIn(msg, out)
    def test_changed_after_sign_fails(self):
        self.sign(); self.edit("cluster: region", "cluster: state")
        rc, out = self.status(); self.assertEqual(rc, 1); self.assertIn("CHANGED", out)
    def test_unlock_needs_token_with_the_authors_reason(self):
        self.sign()
        rc, out = run("design", "unlock", "--reason", "cluster at state level", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("already used", out)       # the sign token is spent
        self.approve("unlock", "cluster at state level")
        rc, out = run("design", "unlock", "--reason", "something else", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("reason", out)
    def test_amendment_writes_csv_and_md(self):
        self.sign(); self.assertEqual(self.unlock("cluster at state level")[0], 0)
        self.assertIn("UNLOCKED", self.status()[1])
        self.edit("cluster: region", "cluster: state")
        self.edit("rejection_at_0.10: 0.104", "rejection_at_0.10: 0.098")   # inference changed: checks re-run
        rc, out = self.sign(); self.assertEqual(rc, 0, out)
        rows = list(csv.DictReader((self.t / dsb.AMEND_CSV_REL).open()))
        self.assertEqual(list(rows[0].keys()), ["date", "field", "old", "new", "reason"])
        self.assertEqual([r["field"] for r in rows], ["inference", "checks.size"])
        self.assertIn("cluster: region", rows[0]["old"]); self.assertIn("cluster: state", rows[0]["new"])
        self.assertEqual(rows[0]["reason"], "cluster at state level")
        md = (self.t / dsb.AMEND_MD_REL).read_text()
        self.assertIn("cluster at state level", md); self.assertIn("+  inference:", md)
    def test_amendment_touching_sample_needs_new_checks(self):
        self.sign(); self.unlock("drop units with gaps")
        self.edit('"units observed', '"units always observed')
        rc, out = self.sign(); self.assertEqual(rc, 1); self.assertIn("re-run the power and size", out)
        self.edit("rejection_at_0.10: 0.104", "rejection_at_0.10: 0.101")
        rc, out = self.sign(); self.assertEqual(rc, 0, out)
    def test_seed_amendment_only_before_first_signing(self):
        args = ("design", "seed-amendment", "--date", "2025-03-01", "--field", "treatment.date",
                "--old", "2019-06-01", "--new", "2020-01-01", "--reason", "statute effective date")
        self.assertEqual(run(*args, root=self.t)[0], 0)
        self.assertEqual(dsb.amendment_count(self.t), 1)
        self.sign(); rc, out = run(*args, root=self.t); self.assertEqual(rc, 1); self.assertIn("first signing", out)
    def test_pre_coder_blocks_unsigned(self):
        rc, out = run("pre", "coder", root=self.t); self.assertIn("design-lock", out); self.assertEqual(rc, 1)

if __name__ == "__main__": unittest.main()
```

- [ ] **Step 2:** Run `python3 -m pytest -q tests/test_design_lock.py`. Expected: FAIL
  (`invalid choice: 'design'`).
- [ ] **Step 3: Implement.** Add to `scripts/pipeline.py`, after `critic_inputs`:

```python
import design_block as dsb, author_token as tok, difflib

def design_state(root: Path, ms: Path) -> Tuple[str, str]:
    h = dsb.design_hash(ms.read_text()); lock = dsb.read_lock(root)
    if lock is None:
        return ("NOT-RETROFITTED", "no design: block and no lock") if h is None else \
               ("UNSIGNED", "design: block present, never signed — the author approves in chat (`approve design sign`)")
    if h is None:
        return "CHANGED", "design_lock.json exists but the manuscript has no design: block"
    if lock.get("status") == "unlocked":
        return "UNLOCKED", f"amendment open since {lock.get('unlocked_at')}: {lock.get('reason')}"
    if h != lock.get("hash"):
        return "CHANGED", "design: block differs from the signed lock — restore it, or the author approves `design unlock` in chat first"
    return "SIGNED", f"signed {lock.get('signed_at')} by {lock.get('signer')}"

def design_check_problems(root: Path, text: str) -> List[str]:
    probs: List[str] = []
    for name in ("power", "size"):
        if not dsb.has_check(text, name):
            probs.append(f"design.checks.{name} missing — run it in explorations/ and record the result"); continue
        f = dsb.check_field(text, name, "file")
        if not f: probs.append(f"design.checks.{name} names no file:")
        elif not f.startswith("explorations/"): probs.append(f"design.checks.{name}.file {f} is not under explorations/")
        elif not (root / f).is_file(): probs.append(f"design.checks.{name}.file {f} does not exist")
    mde, target = dsb.check_number(text, "power", "mde"), dsb.check_number(text, "power", "target_effect")
    if mde is None or target is None: probs.append("design.checks.power needs numeric mde and target_effect")
    elif mde > abs(target): probs.append(f"power: MDE {mde} exceeds |target_effect| {abs(target)}")
    rej = dsb.check_number(text, "size", "rejection_at_0.10")
    if rej is None: probs.append("design.checks.size needs a numeric rejection_at_0.10")
    elif round(abs(rej - 0.10), 10) > 0.03: probs.append(f"size: rejection rate {rej} at the 10% level is outside 0.07–0.13")
    return probs

def design_cmd(root: Path, a) -> int:
    ms = declared_manuscript(root); text = ms.read_text(); st, why = design_state(root, ms)
    if a.op == "status":
        print(f"design: {st} — {why}"); return 0 if st in ("SIGNED", "NOT-RETROFITTED") else 1
    if a.op == "seed-amendment":
        if not all((a.date, a.field, a.old, a.new, a.reason)):
            sys.exit("usage: design seed-amendment --date YYYY-MM-DD --field F --old O --new N --reason R")
        if st != "UNSIGNED": print(f"design seed-amendment: refused — only before the first signing (status {st})"); return 1
        dsb.append_amendments(root, [{"date": a.date, "field": a.field, "old": a.old, "new": a.new, "reason": a.reason}],
                              heading=f"Amendment (seeded at retrofit) — {a.date}")
        print("design: amendment seeded"); return 0
    if a.op == "sign":
        if not a.signer: sys.exit("usage: design sign --signer NAME")
        new_block = dsb.design_block(text)
        if new_block is None: print("design sign: no design: block in the manuscript front matter"); return 1
        probs = design_check_problems(root, text)
        if probs: print("design sign: refused — " + "; ".join(probs)); return 1
        if st == "SIGNED": print("design sign: already signed and unchanged"); return 0
        if st == "CHANGED": print("design sign: refused — the block changed without `design unlock`"); return 1
        lock = dsb.read_lock(root) or {}; rows: List[Dict[str, str]] = []
        if st == "UNLOCKED":
            rows = dsb.amendment_rows(lock["block"], new_block, now()[:10], lock["reason"])
            if dsb.needs_rerun(rows, lock["block"], new_block) and not dsb.checks_changed(rows):
                print("design sign: refused — the amendment touches the inference rule, sample, treatment or an "
                      "outcome; re-run the power and size explorations and record the new results in design.checks"); return 1
        ok, msg = tok.consume(root, "sign", dsb.design_hash(text))
        if not ok: print(f"design sign: refused — {msg}"); return 1
        if rows:
            diff = "\n".join(difflib.unified_diff(dsb._normalise(lock["block"]), dsb._normalise(new_block),
                                                  "signed", "amended", lineterm="", n=0))
            dsb.append_amendments(root, rows, heading=f"Amendment — {now()[:10]} (re-signed by {a.signer})", diff=diff)
        dsb.write_lock(root, {"status": "signed", "hash": dsb.design_hash(text), "block": new_block,
                              "signed_at": now(), "signer": a.signer, "approved_at": msg})
        print(f"design: SIGNED" + (f" — {len(rows)} amendment row(s) recorded" if rows else "")); return 0
    if a.op == "unlock":
        if not a.reason: sys.exit("usage: design unlock --reason TEXT (the author's reason, verbatim)")
        if st != "SIGNED": print(f"design unlock: refused — status is {st}"); return 1
        ok, msg = tok.consume(root, "unlock", dsb.design_hash(text), reason=a.reason)
        if not ok: print(f"design unlock: refused — {msg}"); return 1
        lock = dsb.read_lock(root); lock.update({"status": "unlocked", "reason": a.reason, "unlocked_at": now()})
        dsb.write_lock(root, lock)
        print("design: UNLOCKED — edit the design: block, show it to the author, who approves `design sign` in chat"); return 0
    return 2
```

  Wire it into `main()`:

```python
    ds = sub.add_parser("design"); ds.add_argument("op", choices=["status", "sign", "unlock", "seed-amendment"])
    for flag in ("--signer", "--reason", "--date", "--field", "--old", "--new"): ds.add_argument(flag)
    ...
    if a.cmd == "design": return design_cmd(root, a)
```

  Add the predicate to `evaluate()` before `any_of`:

```python
    if t == "design-lock":
        st, why = design_state(root, ctx.ms)
        return st in ("SIGNED", "NOT-RETROFITTED"), f"design-lock: {st} — {why}"
```

  - `scripts/registry_lib.py`: add `"design-lock"` to `PRED_TYPES`.
  - `scripts/render_registry.py` `pred()`: `elif t == "design-lock": s = "the manuscript's
    \`design:\` block is signed and unchanged (or the project has none yet)"`. Then run
    `python3 scripts/render_registry.py --root .` to rewrite `rules/permissions.md`.
  - `rules/registry.yaml`: append `      - type: design-lock` to the `requires:` list of `coder`
    and of `writer`, matching the neighbouring indentation.
  - `rules/lifecycle.md` predicate table: rows `design-lock` ("the `design:` block is signed and
    unchanged, or the manuscript has no `design:` block and no lock exists") and `no-source` ("no
    `source()` call inside any chunk (INV-19b)").
- [ ] **Step 4:** Run
  `python3 -m pytest -q tests/test_design_lock.py tests/test_pipeline.py tests/test_registry_lib.py && python3 scripts/pipeline.py registry check && ./scripts/check_fork.sh >/dev/null; echo $?`.
  Expected: all pass; `registry-complete` and `registry-rendered` PASS; `0`. `test_pipeline` stays
  green because the fixture is NOT-RETROFITTED until Task 15.
- [ ] **Step 5: Commit.**

```bash
git add scripts/pipeline.py scripts/registry_lib.py scripts/render_registry.py rules/permissions.md \
  rules/registry.yaml rules/lifecycle.md tests/test_design_lock.py
git commit -m "pipeline.py design sign|unlock|status|seed-amendment; author token required; design-lock predicate

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `design-guard` hook, and protect-files covering Bash

**Files:**
- Create: `hooks/design-guard.py`
- Modify: `hooks/protect-files.sh` (eight new patterns; a Bash branch)
- Modify: `scripts/wire_guard_hooks.py` (`WANTED` += `("PreToolUse", "Write|Edit|Bash",
  "design-guard.py")`; a `widen()` step turns an `Edit|Write` group whose hooks include
  `protect-files.sh` into `Edit|Write|Bash`)
- Modify: `seeds/settings.json` (design-guard in the existing `Write|Edit|Bash` group; the
  protect-files matcher becomes `Edit|Write|Bash`)
- Modify: `hooks/README.md` (a design-guard row; the protect-files row says it now covers Bash)
- Test: `tests/test_design_guard.py`, `tests/test_protect_files.py` (cases),
  `tests/test_wire_guard_hooks.py` (cases)

**Interfaces:**
- Consumes: Task 1 (`design_hash`, `read_lock`, `manuscript_path`), Task 2 (`check`), and the
  payload shape of the existing hooks (`tests/test_guard_hooks.py`).
- Produces: a hook that denies
  - (a) an Edit/Write leaving the manuscript's design hash different from a `signed` lock;
  - (b) a Bash command running `pipeline.py … design sign|unlock` without a fresh token for that
    operation (`author_token.check`);
  - (c) a Bash in-place write to the manuscript while the design is signed;
  - (d) any Edit/Write of `design_lock.json`, `design_token.json`, `design_amendments.csv`,
    `design_amendments.md`, `render_fingerprint.json`, `cold_render.json`, `findings_ledger.md` or
    `rulings_log.md` (creation included — these are written only by `pipeline.py` or the render),
    and any Bash command naming `design_token`.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/test_design_guard.py
import pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests")); sys.path.insert(0, str(ROOT / "scripts"))
from test_guard_hooks import ProjectCase
from test_design_block import BASE
import author_token as tok, design_block as db
HOOK = ROOT / "hooks" / "design-guard.py"

class TestDesignGuard(ProjectCase):
    def setUp(self):
        super().setUp(); self.ms.write_text(BASE)
    def sign(self):
        db.write_lock(self.proj, {"status": "signed", "hash": db.design_hash(BASE)})
    def edit(self, old, new, path=None):
        return self.run_hook(HOOK, {"hook_event_name": "PreToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": str(path or self.ms), "old_string": old, "new_string": new}})
    def write(self, path, content="x"):
        return self.run_hook(HOOK, {"hook_event_name": "PreToolUse", "tool_name": "Write",
            "tool_input": {"file_path": str(path), "content": content}})
    def bash(self, cmd):
        return self.run_hook(HOOK, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}})

    def test_unsigned_project_allows_design_edits(self):
        self.assertFalse(self.denied(self.edit("cluster: region", "cluster: state")))
    def test_signed_blocks_design_edit(self):
        self.sign(); self.assertTrue(self.denied(self.edit("cluster: region", "cluster: state")))
    def test_signed_allows_title_and_body(self):
        self.sign()
        self.assertFalse(self.denied(self.edit('title: "T"', 'title: "U"')))
        self.assertFalse(self.denied(self.edit("Body text.", "New body.")))
    def test_signed_blocks_write_changing_block(self):
        self.sign(); self.assertTrue(self.denied(self.write(self.ms, BASE.replace("region", "state"))))
    def test_unlocked_status_allows(self):
        db.write_lock(self.proj, {"status": "unlocked", "hash": db.design_hash(BASE)})
        self.assertFalse(self.denied(self.edit("cluster: region", "cluster: state")))
    def test_sign_and_unlock_need_a_token(self):
        cmds = ("python3 .claude/scripts/pipeline.py design sign --signer me",
                "cd x && python3 .claude/scripts/pipeline.py --root . design unlock --reason r")
        for c in cmds: self.assertTrue(self.denied(self.bash(c)), c)
        tok.issue(self.proj, "sign", None, db.design_hash(BASE))
        self.assertFalse(self.denied(self.bash(cmds[0])))
        self.assertTrue(self.denied(self.bash(cmds[1])))                       # a sign token is not an unlock token
        self.assertFalse(self.denied(self.bash("python3 .claude/scripts/pipeline.py design status")))
    def test_record_files_are_pipeline_only(self):
        for rel in ("quality_reports/design_lock.json", ".claude/state/design_token.json",
                    "quality_reports/design_amendments.csv", "quality_reports/render_fingerprint.json",
                    "quality_reports/findings_ledger.md", "quality_reports/rulings_log.md"):
            self.assertTrue(self.denied(self.write(self.proj / rel)), rel)
        self.assertTrue(self.denied(self.bash("python3 -c \"open('.claude/state/design_token.json','w')\"")))
    def test_bash_inplace_write_blocked_when_signed(self):
        self.sign()
        self.assertTrue(self.denied(self.bash("sed -i '' 's/region/state/' manuscript_p.qmd")))
        self.assertFalse(self.denied(self.bash("grep cluster manuscript_p.qmd")))

if __name__ == "__main__": unittest.main()
```

  - `tests/test_protect_files.py`: `echo x > quality_reports/pipeline_state.json` and
    `rm quality_reports/design_lock.json` are denied (exit 2); `cat quality_reports/pipeline_state.json`
    is allowed.
  - `tests/test_wire_guard_hooks.py`: a settings file whose protect-files group has matcher
    `Edit|Write` comes out `Edit|Write|Bash`; a second run changes nothing.
- [ ] **Step 2:** Run `python3 -m pytest -q tests/test_design_guard.py`. Expected: FAIL (no hook
  file).
- [ ] **Step 3: Implement** `hooks/design-guard.py`.

```python
#!/usr/bin/env python3
"""design-guard.py — PreToolUse (Write|Edit|Bash): the signed design block is the author's.

Spec §4, §0.3. Once quality_reports/design_lock.json says `signed`, no agent edit may change the
manuscript's `design:` front-matter block. `design sign|unlock` run only with the author's
one-time token, issued by hooks/design-token.py from an approval line in the author's own chat
message. The lock, the token and the record files are written only by pipeline.py or the render.
Bash writes to the manuscript are refused while signed (use Edit, which this hook can evaluate).
Fails open on internal error.

Hook Event: PreToolUse
"""
import json, os, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import author_token as tok
import design_block as db

SIGN_RE = re.compile(r"pipeline\.py\b[^\n;&|]*\bdesign\s+(sign|unlock)\b")
INPLACE_RE = r"(sed\s+-i|perl\s+-[a-z]*i|>>?|\btee\b|\bcp\b|\bmv\b)[^\n;&|]*{name}"
PIPELINE_ONLY = {"design_lock.json", "design_token.json", "design_amendments.csv", "design_amendments.md",
                 "render_fingerprint.json", "cold_render.json", "findings_ledger.md", "rulings_log.md"}

def deny(msg):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
        "permissionDecision": "deny", "permissionDecisionReason": "design-guard: " + msg}}))

def main() -> int:
    payload = json.load(sys.stdin); root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")).resolve()
    tool = payload.get("tool_name", ""); ti = payload.get("tool_input") or {}
    cmd = ti.get("command", "") if tool == "Bash" else ""
    if tool in ("Edit", "Write") and Path(ti.get("file_path", "")).name in PIPELINE_ONLY:
        deny(f"{Path(ti['file_path']).name} is written only by pipeline.py or the render."); return 0
    if "design_token" in cmd:
        deny("the author token is written only by the design-token hook."); return 0
    ms = db.manuscript_path(root)
    text = ms.read_text() if ms and ms.exists() else ""
    m = SIGN_RE.search(cmd)
    if m:
        ok, why = tok.check(root, m.group(1), db.design_hash(text))
        if not ok: deny(f"`design {m.group(1)}` needs the author's approval in chat: {why}")
        return 0
    lock = db.read_lock(root)
    if not ms or not ms.exists() or not lock or lock.get("status") != "signed": return 0
    if tool == "Bash":
        if re.search(INPLACE_RE.format(name=re.escape(ms.name)), cmd):
            deny(f"the design is signed; edit {ms.name} with the Edit tool so the design block can be checked.")
        return 0
    if tool not in ("Edit", "Write") or Path(ti.get("file_path", "")).resolve() != ms: return 0
    if tool == "Write": new = ti.get("content", "")
    else:
        old, rep = ti.get("old_string", ""), ti.get("new_string", "")
        new = text.replace(old, rep) if ti.get("replace_all") else text.replace(old, rep, 1)
    if db.design_hash(new) != lock.get("hash"):
        deny("this edit changes the signed design: block. Ask the author to approve in chat with "
             "`approve design unlock: <reason>`; then run `pipeline.py design unlock --reason \"<reason>\"`.")
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception: sys.exit(0)
```

  The hook pre-checks the token's operation, age, use and block hash; `pipeline.py` re-checks
  everything, including the unlock reason, when it spends the token.

  In `hooks/protect-files.sh`:
  - Add to `PROTECTED_PATTERNS`: `design_lock.json`, `design_token.json`, `design_amendments.csv`,
    `design_amendments.md`, `render_fingerprint.json`, `cold_render.json`, `findings_ledger.md`,
    `rulings_log.md`.
  - Replace the "no file path → allow" exit with a Bash branch:

  ```bash
  if [ "$TOOL" = "Bash" ]; then
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
    for PATTERN in "${PROTECTED_PATTERNS[@]}"; do
      ERE=$(printf '%s' "$PATTERN" | sed -e 's/\./\\./g' -e 's/\*/.*/g')
      if echo "$CMD" | grep -Eq "(>|>>|\btee\b|sed -i|\bcp\b|\bmv\b|\brm\b)[^;&|]*${ERE}"; then
        echo "Protected file named in a shell write: $PATTERN" >&2; exit 2
      fi
    done
    exit 0
  fi
  ```

  - `seeds/settings.json`: the protect-files matcher becomes `Edit|Write|Bash`; design-guard
    joins the `Write|Edit|Bash` group.
  - `scripts/wire_guard_hooks.py`: add design-guard to `WANTED`; add `widen(settings) -> int`,
    called from `__main__` after `wire()`, and print the sum of both counts.
  - `hooks/README.md`: the design-guard row; the protect-files row adds "and shell writes to them".
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_design_guard.py tests/test_protect_files.py tests/test_guard_hooks.py tests/test_wire_guard_hooks.py && ./scripts/check_fork.sh >/dev/null; echo $?`.
  Expected: all pass; `0`.
- [ ] **Step 5: Commit.**

```bash
git add hooks/design-guard.py hooks/protect-files.sh hooks/README.md scripts/wire_guard_hooks.py seeds/settings.json \
  tests/test_design_guard.py tests/test_protect_files.py tests/test_wire_guard_hooks.py
git commit -m "design-guard: signed design block, lock and record files are pipeline-only; sign/unlock need the token

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Claim helpers template (base R)

**Files:**
- Create: `templates/claims-helpers.R.txt`
- Create: `tests/r/test_claims_helpers.R`
- Create: `tests/test_claims_helpers.py` (pytest wrapper; skips when `Rscript` is missing)

**Interfaces:**
- Produces, as R objects in the manuscript's global env after the setup chunk:
  - `rc_model_classes`: `c("lm", "glm", "fixest", "fixest_multi", "feols", "felm", "ivreg", "plm",
    "lm_robust")`; a project extends it in its setup chunk, below the paste.
  - `rc_design(qmd) -> list` (stops without a block, or when a hypothesis lacks one `spec:`);
  - `rc_num(x, digits = 2)`, `rc_pct(x, digits = 1)`;
  - `rc_sig(p)` → "statistically significant at the 1% level" / "…5% level" / "…10% level" /
    "not statistically significant";
  - `rc_stars(p)` → `"***"` / `"**"` / `"*"` / `""` (p ≤ 0.01 / 0.05 / 0.10);
  - `rc_dir(b, up, down)`; `rc_cmp(a, b, more, less, same = NULL, tol = 0)`;
  - `rc_design_hash(design_spec)`, `rc_data_hash(data_dirs = c("data/raw", "data/derived"))`;
  - `rc_fingerprint(design_spec = design, classes = rc_model_classes,
    path = "quality_reports/render_fingerprint.json")`.
  - Every helper calls `stop()` on NA, NULL or a non-finite value. The fingerprint JSON is
    `{"estimates_hash", "data_hash", "design_hash", "models": [...]}`, with no timestamp so that it
    changes only when the estimates, data or design do.

- [ ] **Step 1: Write the failing R test.**

```r
# tests/r/test_claims_helpers.R — run: Rscript tests/r/test_claims_helpers.R <repo-root>
repo_root <- commandArgs(trailingOnly = TRUE)[[1]]
eval(parse(file.path(repo_root, "templates", "claims-helpers.R.txt")))  # test harness only; manuscripts paste
design_qmd <- tempfile(fileext = ".qmd")
writeLines(c("---", "title: t", "design:", "  hypotheses:", "    H1: {outcome: mpg, spec: m_h1}", "---", "x"), design_qmd)
design <- rc_design(design_qmd)
expect_error_matching <- function(expr, pattern) {
  message_seen <- tryCatch({ expr; NULL }, error = function(e) conditionMessage(e))
  if (is.null(message_seen) || !grepl(pattern, message_seen)) stop("expected error /", pattern, "/, got: ", message_seen)
}
stopifnot("1% level" = rc_sig(0.004) == "statistically significant at the 1% level",
          "5% boundary is inclusive" = rc_sig(0.05) == "statistically significant at the 5% level",
          "10% boundary is inclusive" = rc_sig(0.10) == "statistically significant at the 10% level",
          "above 10%" = rc_sig(0.11) == "not statistically significant",
          "stars" = identical(c(rc_stars(0.01), rc_stars(0.05), rc_stars(0.1), rc_stars(0.2)), c("***", "**", "*", "")),
          "direction" = rc_dir(-1, "rose", "fell") == "fell" && rc_dir(2, "rose", "fell") == "rose",
          "comparison" = rc_cmp(3, 2, "larger", "smaller") == "larger",
          "comparison tie" = rc_cmp(2, 2.0001, "larger", "smaller", same = "the same", tol = 0.01) == "the same",
          "numbers" = rc_num(1234.567) == "1,234.57" && rc_pct(0.0312) == "3.1%")
expect_error_matching(rc_num(NA_real_), "not one finite number")
expect_error_matching(rc_sig(NaN), "not one finite number")
expect_error_matching(rc_sig(1.2), "not a probability")
expect_error_matching(rc_dir(0, "u", "d"), "exactly 0")
expect_error_matching(rc_num(c(1, 2)), "not one finite number")
fingerprint_path <- tempfile(fileext = ".json")
expect_error_matching(rc_fingerprint(path = fingerprint_path), "m_h1")          # missing spec object
m_h1 <- lm(mpg ~ wt, data = mtcars)
rc_fingerprint(path = fingerprint_path); fp_main <- readLines(fingerprint_path)
m_robust <- lm(mpg ~ wt + hp, data = mtcars)                                    # named in no hypothesis
rc_fingerprint(path = fingerprint_path); fp_with_robust <- readLines(fingerprint_path)
m_robust <- lm(mpg ~ wt + hp + qsec, data = mtcars)
rc_fingerprint(path = fingerprint_path); fp_robust_changed <- readLines(fingerprint_path)
stopifnot("an added model changes the fingerprint" = !identical(fp_main, fp_with_robust),
          "a re-estimated robustness model changes the fingerprint" = !identical(fp_with_robust, fp_robust_changed),
          "models are listed" = any(grepl('"models": \\["m_h1", "m_robust"\\]', fp_robust_changed)))
m_h1 <- "not a model"
expect_error_matching(rc_fingerprint(path = fingerprint_path), "not a fitted model")
if (requireNamespace("fixest", quietly = TRUE)) {
  m_h1 <- fixest::feols(mpg ~ wt | cyl, data = mtcars)
  m_multi <- fixest::feols(c(mpg, hp) ~ wt, data = mtcars)
  rc_fingerprint(path = fingerprint_path)
  stopifnot("fixest_multi is fingerprinted" = any(grepl("m_multi", readLines(fingerprint_path))))
}
hash_before <- rc_design_hash(design); design$hypotheses$H1$outcome <- "hp"
stopifnot("design hash moves with the design" = hash_before != rc_design_hash(design))
data_dir <- tempfile(); dir.create(data_dir); writeLines("a,b\n1,2", file.path(data_dir, "x.csv"))
hash_data <- rc_data_hash(data_dir); writeLines("a,b\n1,3", file.path(data_dir, "x.csv"))
stopifnot("data hash moves with the data" = hash_data != rc_data_hash(data_dir))
expect_error_matching(rc_design(tempfile()), "")
cat("claims-helpers: OK\n")
```

```python
# tests/test_claims_helpers.py
import pathlib, shutil, subprocess, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
@unittest.skipUnless(shutil.which("Rscript"), "Rscript not installed")
class TestClaimsHelpers(unittest.TestCase):
    def test_r_suite(self):
        r = subprocess.run(["Rscript", str(ROOT / "tests" / "r" / "test_claims_helpers.R"), str(ROOT)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn("claims-helpers: OK", r.stdout)
```

- [ ] **Step 2:** Run `python3 -m pytest -q tests/test_claims_helpers.py`. Expected: FAIL (file
  not found).
- [ ] **Step 3: Implement** `templates/claims-helpers.R.txt`.

```r
# ---- claims helpers: paste into the setup chunk (cache: false), below the library() calls ----
# Source of truth: research-claude templates/claims-helpers.R.txt. Do not edit here; re-paste.
# Every result word in prose comes from these (or from an inline if, or sits in a sentence with a
# stopifnot() guard), so the word changes when the model does.
# Significance convention: * p <= 0.10, ** p <= 0.05, *** p <= 0.01.

# Classes the fingerprint treats as fitted models. Extend below the paste, never by editing here.
rc_model_classes <- c("lm", "glm", "fixest", "fixest_multi", "feols", "felm", "ivreg", "plm", "lm_robust")

rc_design <- function(qmd) {
  design_spec <- rmarkdown::yaml_front_matter(qmd)$design
  if (is.null(design_spec)) stop("rc_design: no `design:` block in the front matter of ", qmd, call. = FALSE)
  if (length(design_spec$hypotheses) == 0) stop("rc_design: design$hypotheses is empty", call. = FALSE)
  has_spec <- vapply(design_spec$hypotheses, function(h) is.character(h$spec) && length(h$spec) == 1, logical(1))
  if (!all(has_spec)) {
    stop("rc_design: each hypothesis needs one `spec:` naming its model object: ",
         paste(names(design_spec$hypotheses)[!has_spec], collapse = ", "), call. = FALSE)
  }
  design_spec
}

.rc_ok <- function(x, helper) {
  if (is.null(x) || length(x) != 1 || !is.numeric(x) || !is.finite(x)) {
    stop(sprintf("%s: value is %s, not one finite number - fix the model, do not type the word", helper,
                 if (is.null(x)) "NULL" else paste(format(x), collapse = ", ")), call. = FALSE)
  }
  invisible(x)
}

rc_num <- function(x, digits = 2) {
  .rc_ok(x, "rc_num")
  formatC(x, format = "f", digits = digits, big.mark = ",")
}

rc_pct <- function(x, digits = 1) {
  .rc_ok(x, "rc_pct")
  paste0(formatC(100 * x, format = "f", digits = digits), "%")
}

rc_sig <- function(p) {
  .rc_ok(p, "rc_sig")
  if (p < 0 || p > 1) stop("rc_sig: p = ", p, " is not a probability", call. = FALSE)
  if (p <= 0.01) return("statistically significant at the 1% level")
  if (p <= 0.05) return("statistically significant at the 5% level")
  if (p <= 0.10) return("statistically significant at the 10% level")
  "not statistically significant"
}

rc_stars <- function(p) {
  .rc_ok(p, "rc_stars")
  if (p <= 0.01) return("***")
  if (p <= 0.05) return("**")
  if (p <= 0.10) return("*")
  ""
}

rc_dir <- function(b, up, down) {
  .rc_ok(b, "rc_dir")
  switch(as.character(sign(b)), "1" = up, "-1" = down,
         stop("rc_dir: estimate is exactly 0; no direction word applies", call. = FALSE))
}

rc_cmp <- function(a, b, more, less, same = NULL, tol = 0) {
  .rc_ok(a, "rc_cmp"); .rc_ok(b, "rc_cmp")
  if (abs(a - b) <= tol) {
    if (is.null(same)) stop("rc_cmp: values equal within tol and no `same` word given", call. = FALSE)
    return(same)
  }
  if (a > b) more else less
}

.rc_md5 <- function(txt) {
  hash_file <- tempfile(); on.exit(unlink(hash_file))
  writeLines(txt, hash_file); unname(tools::md5sum(hash_file))
}

rc_design_hash <- function(design_spec) .rc_md5(paste(deparse(design_spec), collapse = "\n"))

rc_data_hash <- function(data_dirs = c("data/raw", "data/derived")) {
  data_files <- sort(unlist(lapply(data_dirs[dir.exists(data_dirs)], list.files, recursive = TRUE, full.names = TRUE)))
  .rc_md5(paste(data_files, unname(tools::md5sum(data_files)), collapse = "\n"))
}

# One line per fitted model: name, N, and every coefficient with its standard error.
.rc_model_digest <- function(model_name, fit) {
  if (inherits(fit, "fixest_multi")) {
    parts <- as.list(fit)
    return(paste(vapply(seq_along(parts), function(i) .rc_model_digest(paste0(model_name, "[[", i, "]]"), parts[[i]]), ""),
                 collapse = "\n"))
  }
  coefs <- stats::coef(fit); std_errors <- sqrt(diag(as.matrix(stats::vcov(fit))))
  paste(model_name, stats::nobs(fit), paste(names(coefs), signif(coefs, 10), signif(std_errors, 10), collapse = ";"))
}

rc_fingerprint <- function(design_spec = design, classes = rc_model_classes,
                           path = "quality_reports/render_fingerprint.json") {
  spec_names <- unique(vapply(design_spec$hypotheses, function(h) h$spec, ""))
  absent <- spec_names[!vapply(spec_names, exists, logical(1), envir = globalenv(), inherits = FALSE)]
  if (length(absent) > 0) stop("rc_fingerprint: hypothesis spec object(s) not found: ", paste(absent, collapse = ", "), call. = FALSE)
  not_models <- spec_names[!vapply(spec_names, function(n) inherits(get(n, envir = globalenv()), classes), logical(1))]
  if (length(not_models) > 0) {
    stop("rc_fingerprint: spec object(s) not a fitted model of a class in rc_model_classes: ",
         paste(not_models, collapse = ", "), call. = FALSE)
  }
  model_names <- Filter(function(n) inherits(get(n, envir = globalenv()), classes), sort(ls(globalenv())))
  model_digests <- vapply(model_names, function(n) .rc_model_digest(n, get(n, envir = globalenv())), "")
  dir.create(dirname(path), showWarnings = FALSE, recursive = TRUE)
  writeLines(sprintf('{\n  "estimates_hash": "%s",\n  "data_hash": "%s",\n  "design_hash": "%s",\n  "models": [%s]\n}',
                     .rc_md5(model_digests), rc_data_hash(), rc_design_hash(design_spec),
                     paste0('"', model_names, '"', collapse = ", ")), path)
  invisible(path)
}
# ---- end claims helpers ----
```

  Notes for the reviewer: `.rc_model_digest` calls itself only to unpack a `fixest_multi`; no helper
  fits a model (`rules/readable-code.md` §4). Tested on R with fixest installed: `as.list()` on a
  `fixest_multi` returns its `fixest` members, and a `glm` inherits `lm`.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_claims_helpers.py`. Expected: 1 passed. Run
  the naming grep from `~/.claude/references/r-naming.md` on `templates/claims-helpers.R.txt` and
  `tests/r/test_claims_helpers.R`: no hits.
- [ ] **Step 5: Commit.**

```bash
git add templates/claims-helpers.R.txt tests/r/test_claims_helpers.R tests/test_claims_helpers.py
git commit -m "templates/claims-helpers.R.txt: rc_* claim helpers, star convention, cache keys, fingerprint of every fitted model

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Tighten `prose_number_check.py` — surface (all papers)

**Files:**
- Modify: `scripts/prose_number_check.py` (`load_manuscript`, `scan`, `R_CAP`, `main`, docstring)
- Test: `tests/test_prose_number_surface.py`

**Interfaces:**
- Produces, for every paper (retrofitted or not, spec §0.12):
  - YAML `title:`, `subtitle:` and `abstract:` values are scanned as prose.
  - Decimal literals inside `$…$`/`$$…$$` are scanned.
  - R `notes=`/`note=`/`general=` string literals are scanned as captions.
  - A `response-letter: <path>` line in CLAUDE.md (one or more) is scanned with the same rules,
    labelled `letter:`.
  - The star legend of the fixed convention is not a literal: `p ≤ 0.10`, `p <= 0.05`,
    `p $\le$ 0.01` (and `0.1`) are skipped. A legend written with `<` is still a literal and fails,
    which points the author at the convention (Task 14).

- [ ] **Step 1: Write the failing tests.** Follow the pattern of
  `tests/test_prose_number_holes.py`: a temp project with `.claude/` and `CLAUDE.md`, a manuscript,
  and a run of the script. One test per surface; each asserts exit 1 and the literal in the output.
  - Abstract: `abstract: |\n  Prices fell 3.4 percent.` → `'3.4'`.
  - Title: `title: "A 12 percent drop"` → `'12'`.
  - Math: `$\beta = 0.634$` → `'0.634'`, while `$\beta_1$` and `$x_{it}$` pass.
  - Notes: in an R chunk, `modelsummary(m, notes = "Clustered by 51 states.")` → `'51'`.
  - Star legend: `notes = "* p ≤ 0.10, ** p ≤ 0.05, *** p ≤ 0.01"` passes; the same with `<` → `'0.10'`.
  - Letter: CLAUDE.md `response-letter: letter.md` with `We now find 0.21.` → `letter: … '0.21'`;
    a declared letter that does not exist → exit 2.
  - Control: the fixture manuscript still passes.
- [ ] **Step 2:** Run `python3 -m pytest -q tests/test_prose_number_surface.py`. Expected: the
  surface tests FAIL, the control passes.
- [ ] **Step 3: Implement.**
  - **YAML.** In `load_manuscript`, while `in_yaml`, match
    `^(title|subtitle|abstract):[ \t]*(.*)$`. If the value is `|` or `>` (optionally `|-`/`>-`),
    append each following line that starts with whitespace as `(i, line)` to `prose`, until a line
    that doesn't. Otherwise append `(i, value.strip("\"'"))` to `prose`. No other YAML key is
    scanned; `design:` is data, not prose. Tested (Quarto, HTML render): inline `` `r ` `` in a
    YAML `title:` and `abstract:` is evaluated, so the abstract can carry live values.
  - **Star legend.** Add
    `STAR_LEGEND = re.compile(r"\bp\s*(?:≤|<=|\$\\leq?\$)\s*0?\.(?:10?|05|01)\b")` and, in
    `scan()`, apply `STAR_LEGEND.sub(" ", …)` to the text before `MATH.sub` and before the math
    pass below.
  - **Math.** In `scan()`, before `MATH.sub`, add:
    ```python
    for mm in MATH.finditer(STAR_LEGEND.sub(" ", INLINE.sub(" ", text))):
        for d in re.finditer(r"(?<![\w_^{])(\d+\.\d+)", mm.group(0)):
            hits.setdefault(d.group(1), []).append((lineno, label + "math: " + mm.group(0)[:110]))
    ```
  - **Notes.** Change `R_CAP` to
    `r"""\b(?:caption|title|notes?|general)\s*=\s*(["'])(.*?)(?<!\\)\1"""`, and update both
    "Known limits" passages (module docstring and the comment above `FENCE_CAP`): notes are read.
  - **Letter.** In `main`, after scanning the manuscript, loop over
    `declared(root, "response-letter")`. For each path relative to root that exists,
    `load_manuscript(path)` and scan with label `"letter: "`. Exit 2 when a declared letter is
    missing.
- [ ] **Step 4:** Run
  `python3 -m pytest -q tests/test_prose_number_surface.py tests/test_prose_number_check.py tests/test_prose_number_holes.py`.
  Expected: all pass. If an existing test asserted that `notes =` is NOT read, update that
  assertion: the spec now requires it.
- [ ] **Step 5: Commit:** `prose_number_check: scan title/abstract, math decimals, table notes, response letter; star legend is not a literal`
  (with the trailer).

---

### Task 7: Tighten `prose_number_check.py` — words (retrofitted papers), thresholds and context allowlist

**Files:**
- Modify: `scripts/prose_number_check.py`
- Create: `references/pipeline-jargon.txt`
- Test: `tests/test_prose_number_words.py`

**Interfaces:**
- Produces:
  - `retrofitted = design_block.design_block(text) is not None` (imported from the script's real
    directory: `sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))`). The result line
    names the mode.
  - **Retrofitted only (spec §0.12):**
    - the lexicon adds `_VERDICT_STRICT` (direction, comparison, magnitude and universality
      words) to `_VERDICT`, extended by `prose-verdict-words:`;
    - the verdict ceiling defaults to 0 (`prose-verdict-ceiling:` still overrides);
    - a sentence carrying an inline `stopifnot(` guard is bound and its typed words pass (spec
      §0.11); helper output and raw inline `if` pass because inline spans are never scanned;
    - a `PIPELINE JARGON` failure (not allowlistable), from `references/pipeline-jargon.txt` plus
      `prose-jargon:` in CLAUDE.md.
  - **Not retrofitted:** today's verdict behaviour, unchanged (old lexicon, advisory unless a
    ceiling is declared, no jargon, no guard exemption).
  - **All papers:**
    - a `WARN literal threshold` line for an inline `if` comparing against a numeric literal
      other than 0.10/0.1/0.05/0.01 (never fails);
    - an optional allowlist `context` column, for literals and (retrofitted) words alike: when it
      is non-empty, the row explains only occurrences whose context contains it. A word row's
      `literal` is the lower-case word.

- [ ] **Step 1: Write the failing tests** (same harness as Task 6; "retrofitted" means the temp
  manuscript carries the Task 1 `BASE` front matter):
  - Retrofitted: `Prices rose by \`r rc_num(b)\`.` → exit 1, `rose` listed. The same sentence with
    `\`r rc_dir(b, "rose", "fell")\`` passes.
  - Retrofitted, guarded: `Prices rose by \`r rc_num(b)\`\`r local({stopifnot("main: rose" = b > 0); ""})\`.`
    passes; the same without the guard fails.
  - Retrofitted: `larger`, `doubled` and `every specification` beside a live value → exit 1.
  - Not retrofitted: the same `rose` sentence → exit 0 and `advisory` in the output (unchanged).
  - Retrofitted: `prose-verdict-ceiling: 5` with 1 hit → exit 0 (the override still works).
  - `\`r if (p <= 0.07) "x" else "y"\`` → `WARN literal threshold`, exit 0;
    `\`r if (p <= 0.05) "x" else "y"\`` → no warning (both modes).
  - Retrofitted: `the governing p` in prose → exit 1, `PIPELINE JARGON`; `prose-jargon: foo-band`
    makes `foo-band` fail. Not retrofitted: no jargon check.
  - Literal context: allowlist row `2024,settlement year,in 2024` → `in 2024` passes;
    `0.2024 points` still fails.
  - Word context (retrofitted): row `positive,sign of a definition,positive integer` → "a positive
    integer `r k`" passes; "a positive effect of `r rc_num(b)`" fails.
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - `_VERDICT_STRICT = (r"increase[sd]?|decrease[sd]?|declin(?:e|es|ed|ing)|larger|smaller|higher|lower|"
    r"doubled|halved|tripled|exceed(?:s|ed)?|robust(?:ly)?|substantial(?:ly)?|modest(?:ly)?|"
    r"sizable|consistent(?:ly)?|every specification|all specifications")`; multi-word entries last.
  - Guard marking: replace `INLINE.sub(LIVE, text)` in `verdict_hits` with a function that maps a
    match containing `stopifnot(` to `GUARD = "\x01"` and any other match to `LIVE`. In retrofitted
    mode a sentence containing `GUARD` yields no hits.
  - Default ceiling (retrofitted): after the declaration parse,
    `if ceiling is None and retrofitted: ceiling = 0`. Mode text:
    `f"ceiling {ceiling}" + (" (default, retrofitted)" if retrofitted and not ceilings else "")`.
    Update the VERDICT WORDS docstring paragraph: enforced at 0 once a `design:` block exists; bind
    a word with `rc_sig`/`rc_stars`/`rc_dir`/`rc_cmp`, a raw inline `if`, or a `stopifnot()` guard
    in the sentence.
  - Threshold warning. For each match whose `float(group(1))` is not in `{0.1, 0.05, 0.01}`,
    print `WARN literal threshold {n} at line N — the convention is 0.10/0.05/0.01; use rc_sig()`:
    ```python
    THRESH = re.compile(r"`(?:r|\{r\})\s[^`]*\bif\s*\([^)`]*[<>]=?\s*(-?(?:\d+\.?\d*|\.\d+))\s*\)")
    ```
  - Jargon (retrofitted): load the patterns from
    `Path(os.path.realpath(__file__)).parent.parent / "references" / "pipeline-jargon.txt"` (skip
    `#` and blank lines), plus `tokens(" ".join(declared(root, "prose-jargon")))`. Match
    case-insensitively on `INLINE.sub(" ", line)` for prose and caption lines. Any hit fails.
  - Context allowlist: read `r.get("context")`; build `allow_ctx[key] = [contexts…]` (None for a
    row without one). An occurrence is explained when `key in allow` and any context is None or
    occurs in the occurrence's context string. Compute `unexplained` per occurrence. Apply the same
    test to retrofitted verdict hits (key = the lower-case word, context = the sentence).
  - `references/pipeline-jargon.txt`:
    ```
    # Pipeline-internal vocabulary that must never reach a manuscript (spec §5). One regex per line.
    governing p
    wording band
    rival reading
    verdict class(es)?
    finding ledger
    design lock
    \b[a-z]+-critic\b
    pipeline\.py
    \bINV-\d+\b
    \b(?:R|F|L)-\d{1,3}\b
    ```
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_prose_number_words.py tests/test_prose_number_surface.py tests/test_prose_number_check.py tests/test_prose_number_holes.py tests/test_eval_checkers.py`.
  Expected: all pass. No existing test changes, because none of their manuscripts has a `design:`
  block. Then run `python3 scripts/prose_number_check.py tests/fixture-project/manuscript_fixture.qmd`:
  exit 0.
- [ ] **Step 5: Commit:** `prose_number_check: retrofitted papers get ceiling 0, wider lexicon, guards, jargon; threshold warning and context allowlist for all`
  (with the trailer).

---

### Task 8: Results fingerprint on scores, staleness, and stale stages at session start

**Files:**
- Modify: `scripts/pipeline.py` (`record-score`, `evaluate` `score`/`score-if-scored`/`critic-ran`,
  `score --gate`, `next_report`; new `stale` subcommand)
- Create: `hooks/stale-stages.py` (SessionStart)
- Modify: `scripts/wire_guard_hooks.py` (`WANTED` += `("SessionStart", None, "stale-stages.py")`),
  `seeds/settings.json` (SessionStart group, no matcher), `hooks/README.md` (row)
- Test: `tests/test_fingerprint_staleness.py`

**Interfaces:**
- Consumes: Task 1 `design_hash`, the Task 5 fingerprint JSON.
- Produces:
  - `FINGERPRINT_REL = quality_reports/render_fingerprint.json` (committed: replication provenance,
    like `receipts.jsonl`).
  - `current_fingerprint(root, ms) -> Dict[str, Optional[str]]`, keys `{"estimates", "design"}`.
  - `STALE_ON_CHANGE = {"strategy", "manuscript", "referees"}`.
  - `stale_reason(root, ms, comp, entry) -> Optional[str]`;
    `stale_components(root) -> Dict[str, str]`.
  - `pipeline.py stale`: one `STALE <component>: <reason>` line each, exit 1; `stale: none`,
    exit 0; no state file → exit 0.
  - Each score entry and receipt gains `fingerprint: {estimates, design}` and `head`.
  - The hook prints the stale stages at every session start (`systemMessage` for the author,
    `additionalContext` for the session) and is silent when none.

- [ ] **Step 1: Write the failing tests.** Use `FixtureCase` from `tests/test_pipeline.py`.
  1. Without a fingerprint file or lock, record a manuscript score; `score --gate commit` and
     `stale` are unaffected (not retrofitted).
  2. Write `render_fingerprint.json` (`estimates_hash: "A"`), record a manuscript score, then
     rewrite it with `"B"`. Now `score --gate commit` exits 1 with `STALE`, `next` shows
     `manuscript` as `OPEN … older fingerprint`, `pre editor` fails, and `stale` exits 1 naming
     `manuscript`.
  3. A code score is NOT made stale by an estimates change.
  4. A section-scoped writer-critic score under the new fingerprint does not clear the stale
     manuscript score; a whole-manuscript one does.
  5. With a design lock present but no fingerprint file, `score --gate commit` fails with
     `no render_fingerprint.json`.
  6. `record-score` writes `fingerprint` and `head` into the state entry and the receipt.
  7. The hook, run with `CLAUDE_PROJECT_DIR` at a stale fixture (with `.claude/scripts/pipeline.py`
     linked), prints JSON whose `additionalContext` names `manuscript`; at a fresh one it prints
     nothing.
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3: Implement.**

```python
FINGERPRINT_REL = Path("quality_reports") / "render_fingerprint.json"
STALE_ON_CHANGE = {"strategy", "manuscript", "referees"}

def read_fingerprint(root: Path) -> Optional[Dict[str, Any]]:
    p = root / FINGERPRINT_REL
    return json.loads(p.read_text()) if p.exists() else None

def current_fingerprint(root: Path, ms: Path) -> Dict[str, Optional[str]]:
    fp = read_fingerprint(root) or {}
    return {"estimates": fp.get("estimates_hash"), "design": dsb.design_hash(ms.read_text())}

def git_head(root: Path) -> Optional[str]:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None

def stale_reason(root: Path, ms: Path, comp: str, entry: Dict[str, Any]) -> Optional[str]:
    if comp not in STALE_ON_CHANGE or not entry: return None
    cur = current_fingerprint(root, ms); locked = dsb.read_lock(root) is not None
    if cur["estimates"] is None:
        return "no render_fingerprint.json — render the manuscript (its fingerprint chunk writes it)" if locked else None
    fp = entry.get("fingerprint") or {}
    if fp.get("estimates") != cur["estimates"] or fp.get("design") != cur["design"]:
        clears = {"manuscript": "a whole-manuscript writer-critic round", "strategy": "a strategist-critic round",
                  "referees": "a new referee round"}[comp]
        return f"STALE: {comp} score earned under an older fingerprint — re-score with {clears}"
    return None

def stale_components(root: Path) -> Dict[str, str]:
    if not state_path(root).exists(): return {}
    ms = declared_manuscript(root); comps = (load_state(root).get("components") or {})
    return {c: r for c, e in comps.items() if (r := stale_reason(root, ms, c, e))}
```

  Then:
  - In `record-score`, move `ms = declared_manuscript(root)` above the entry construction and set
    `entry["fingerprint"] = current_fingerprint(root, ms); entry["head"] = git_head(root)`; copy
    both into `receipt`. A `--scope section:…` entry is stored under `sections` as today and never
    replaces the component entry, so it cannot clear staleness.
  - In `evaluate` `score` and `score-if-scored`, after reading `val`: when the component's
    `stale_reason` is not None, return `(False, desc + " — " + reason)`.
  - In `critic-ran`, just before the final `return True`: when `stale_reason` is not None, return
    `(False, ran + " — " + reason)`.
  - In `score --gate`, for each component with a reason, print `gate {gate}: {reason}` and set
    `ok = False`.
  - In `next_report`, a CLOSED-but-stale component becomes `info[c] = ("OPEN", reason)`.
  - `stale` subcommand: print each `STALE` line, or `stale: none`; return 1 when any.

  `hooks/stale-stages.py`:

```python
#!/usr/bin/env python3
"""stale-stages.py — SessionStart: name the review stages a re-estimation or design change made stale.

Spec §0.6. Silent when nothing is stale, when the project has no state file, or when pipeline.py
is not linked. Never blocks a session. Fails open.

Hook Event: SessionStart
"""
import json, os, subprocess, sys
from pathlib import Path

def main() -> int:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")).resolve()
    script = root / ".claude" / "scripts" / "pipeline.py"
    if not script.exists() or not (root / "quality_reports" / "pipeline_state.json").exists():
        return 0
    p = subprocess.run([sys.executable, str(script), "--root", str(root), "stale"], capture_output=True, text=True, timeout=20)
    if p.returncode != 1:
        return 0
    body = p.stdout.strip()
    print(json.dumps({"systemMessage": "Stale review stages:\n" + body,
                      "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext":
                          "## Stale review stages\n\n```\n" + body + "\n```\n\nWhile the manuscript stage is stale, manuscript "
                          "commits are refused until it is re-scored under the current fingerprint (rule 15 of .claude/rules/core.md)."}}))
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception: sys.exit(0)
```

  - Wire it: `WANTED`, `seeds/settings.json` (a SessionStart group with no matcher), README row
    `stale-stages.py | SessionStart | Prints the strategy, manuscript or referee scores a
    re-estimation or design change made stale; silent otherwise`.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_fingerprint_staleness.py tests/test_pipeline.py tests/test_wire_guard_hooks.py && ./scripts/check_fork.sh >/dev/null; echo $?`.
  Expected: all pass; `0`.
- [ ] **Step 5: Commit:** `pipeline.py: scores carry the results fingerprint; stale strategy/manuscript/referee scores reopen their stage; stale-stages hook`
  (with the trailer).

---

### Task 9: Finding ledger, rulings log and questions for the author

**Files:**
- Create: `scripts/findings_ledger.py` (ledger, rulings log and questions file I/O); add it to
  `scripts/SHIPPED`
- Create: `templates/findings-ledger.md`, `templates/rulings-log.md`
- Modify: `scripts/pipeline.py` (`ledger`, `ruling` and `question` subcommands; `ledger-closed`
  auto-appended on `post`)
- Modify: `scripts/registry_lib.py` (`PRED_TYPES` += `"ledger-closed"`), `scripts/render_registry.py`
  (`pred()` case), then re-render `rules/permissions.md`
- Test: `tests/test_findings_ledger.py`

**Interfaces:**
- Produces:
  - `LEDGER_REL = quality_reports/findings_ledger.md`, `RULINGS_REL = quality_reports/rulings_log.md`,
    `QUESTIONS_REL = quality_reports/questions_for_author.md`.
  - `rows(path) -> List[Dict[str, str]]`, keys `id, created, creator, report, location, finding,
    status, guard`.
  - `add(path, creator, report, location, finding, status="open") -> str` returning `F-NNN`;
    `set_status(path, fid, status, guard=None)`; `blocking(path, creator) -> List[Dict]` (rows whose
    status is `open`, `proposal: pending` or `proposal: accepted`).
  - `add_ruling(path, by, decision, alternative, reason) -> None`; `add_question(path, text,
    blocks) -> None`.
  - CLI:
    - `pipeline.py ledger add --creator C --report P --location L --finding T [--proposal]`;
    - `pipeline.py ledger close ID (--sha SHA | --pending) [--guard TEXT]`: `--pending` is allowed
      only while `stale_components()` has `manuscript` (status `closed pending`);
    - `pipeline.py ledger decline ID --reason R --by author|session`;
    - `pipeline.py ledger accept|reject ID --by author|session [--reason R]` (`--reason` required
      for `--by session`);
    - `pipeline.py ledger settle`: when HEAD's commit touched the manuscript and nothing is stale,
      every `closed pending` row becomes `closed <HEAD sha7>` (run by `hooks/git/post-commit`,
      Task 12);
    - `pipeline.py ledger show [--open] [--creator C]`;
    - `pipeline.py ruling add --decision D --alternative A --reason R [--by session|author]`;
    - `pipeline.py question add --text T --blocks STAGE`.
  - Every `decline`, `accept` and `reject` also appends a rulings-log row (spec §0.8, §6): decision
    "F-007 declined" / "F-007 accepted" / "F-007 rejected", the alternative ("fix it" / "reject it"
    / "accept it"), the reason, and `by`.

- [ ] **Step 1: Write the failing tests.**
  - `add` creates the file from the template and returns `F-001`, then `F-002`.
  - A `|` in the finding text is escaped as `\|` and round-trips.
  - `close` with a non-existent sha exits 1. Initialise a git repo in the temp dir, commit, and
    close with the real sha: exit 0, status `closed <sha7>`; `--guard "stopifnot in tbl-main"` is
    stored in the `guard` column.
  - `close --pending` exits 1 when nothing is stale; with a stale manuscript score (Task 8 setup)
    it exits 0 and the row reads `closed pending`; `post writer` does not count it as open.
  - `settle`: after a commit that changes the manuscript while still stale, the row stays
    `closed pending`; after re-scoring and a manuscript commit, it becomes `closed <that sha7>`.
    A commit that does not touch the manuscript settles nothing.
  - `decline` without `--reason` or `--by` exits 2; a decline writes one rulings-log row with the
    date, `session`, "F-001 declined", "fix it" and the reason.
  - `post writer` fails while an `open` writer row exists, and passes after close.
  - A `proposal: pending` row blocks; after `reject --by session --reason r` it no longer blocks
    and a ruling is logged; after `accept` it blocks until closed.
  - A row for `coder` doesn't block `post writer`.
  - `ruling add` appends a row with today's date; missing `--alternative` exits 2.
  - `question add` appends a dated entry naming the blocked stage.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement.** Markdown tables under fixed headers.

`templates/findings-ledger.md`:

```markdown
# Finding ledger

Written only by `pipeline.py ledger` (spec §6). One row per critic or referee finding. Status:
`open` · `closed <sha>` · `closed pending` (fixed while review was stale; settled to the commit
that ends the stale window) · `declined: <reason>` · `proposal: pending|accepted|rejected`.
A finding labelled `[missed-earlier]` was raised in a later round on text an earlier round passed.
`guard` names the `stopifnot()` guard that now checks a closed finding, when one does.

| id | created | creator | report | location | finding | status | guard |
|---|---|---|---|---|---|---|---|
```

`templates/rulings-log.md`:

```markdown
# Rulings log

Written only by `pipeline.py ruling add` and by ledger decline/accept/reject (spec §0.8). Each row
is a decision a session made without the author, kept so it can be reversed cheaply. A ruling
never contradicts a decision the author recorded and never changes `design:`; those are
questions (`quality_reports/questions_for_author.md`).

| date | by | decision | alternative | reason |
|---|---|---|---|---|
```

  - `findings_ledger.py` parses rows after the separator line by splitting on unescaped `|`
    (`re.split(r"(?<!\\)\|", line)[1:-1]`), and writes back with `\|` escaping. The rulings log
    uses the same reader and writer.
  - `close --sha` verifies `git cat-file -e <sha>^{commit}` in root.
  - Statuses are validated against
    `^(open|closed (?:[0-9a-f]{7,40}|pending)|declined: .+|proposal: (pending|accepted|rejected))$`.
  - `settle` reads `git diff-tree --no-commit-id --name-only -r HEAD`; it acts only when the
    declared manuscript is in that list and `stale_components(root)` has no `manuscript` entry.
  - `questions_for_author.md` is created with a one-line header and each entry is
    `## <date> — blocks <stage>\n\n<text>\n`.
  - In `pipeline.py`, add the predicate:

```python
    if t == "ledger-closed":
        import findings_ledger as fl
        b = fl.blocking(root / fl.LEDGER_REL, ctx.agent or "")
        return not b, ("ledger-closed: no open findings" if not b else
                       f"ledger-closed: {len(b)} open for {ctx.agent}: " + ", ".join(r["id"] for r in b[:5]))
```

  - In `eval_preds`, for `kind == "post"`, append `{"type": "ledger-closed"}` for every agent with
    a critic, as is done for `critic-ran`.
  - `render_registry.py` `pred()`: `elif t == "ledger-closed": s = "no open finding-ledger row or
    undecided proposal for the creator"`; re-render `rules/permissions.md`.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_findings_ledger.py tests/test_pipeline.py && python3 scripts/pipeline.py registry check && ./scripts/check_fork.sh >/dev/null; echo $?`.
  Expected: all pass; `0`. The fixture has no ledger file, so `blocking` returns `[]`.
- [ ] **Step 5: Commit:** `finding ledger and rulings log: post refuses open findings; declines and proposal decisions are logged rulings`
  (with the trailer; `echo findings_ledger.py >> scripts/SHIPPED` first).

---

### Task 10: No re-review after a pass; round-2+ critic context

**Files:**
- Modify: `scripts/pipeline.py` (`dispatch-ok` and `critic-context` subcommands)
- Test: `tests/test_dispatch_ok.py`

**Interfaces:**
- Consumes: Task 8 (`stale_reason`, the entry's `head` and `fingerprint`), Task 9 (`rows`), and
  the latest receipt's `manuscript_sha256`.
- Produces:
  - `pipeline.py dispatch-ok <critic> [--author-request]`. Exit 1 with `PASSED-UNCHANGED` when the
    critic's component scored ≥ 80, isn't stale, and the manuscript's sha256 equals the one in the
    latest receipt for that component. Exit 0 otherwise.
  - `pipeline.py critic-context <critic>`. Writes
    `quality_reports/critic_inputs/<critic>_context_<stamp>.md` with the ledger rows for the
    critic's creator(s), plus `git diff <entry.head> -- <manuscript>` (or `no prior scored round`
    when there is no entry), and prints the path.

- [ ] **Step 1: Write the failing tests.**
  - No score → `dispatch-ok writer-critic` exit 0.
  - Manuscript score 85, manuscript unchanged → exit 1 `PASSED-UNCHANGED`; with
    `--author-request` → exit 0.
  - Append a line to the manuscript → exit 0.
  - Score 70 → exit 0.
  - A stale score 85 → exit 0.
  - `critic-context writer-critic` after a scored round in a git-initialised fixture, with one
    edit → the file contains the `+` line of the edit and the ledger header.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement.** For `dispatch-ok`:
  - Find `comp` as the component whose `scored_by == critic`.
  - Read `entry` and the last receipt line in `receipts.jsonl` with that `component` and no
    `scope`.
  - Apply the conditions above. Threshold: `GATES["commit"][0]`.

  For `critic-context`:
  - Creators are `[a for a, e in reg["agents"].items() if e.get("critic") == critic]`.
  - Ledger rows come filtered by creator.
  - The diff is `subprocess.run(["git", "diff", head, "--", ms_rel])`.
  - Write the file into `CRITIC_INPUTS_REL` with the same unique-name loop as `critic_inputs`.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_dispatch_ok.py`. Expected: all pass.
- [ ] **Step 5: Commit:** `pipeline.py dispatch-ok and critic-context: no re-review of passed unchanged work; rounds 2+ get ledger and diff`
  (with the trailer).

---

### Task 11: `check_render.py` — NA values and overfull boxes

**Files:**
- Modify: `scripts/check_render.py` (`findings`, plus a `--latex-log` option)
- Modify: `scripts/pipeline.py` `critic_inputs` (pass `--latex-log <stem>.log` when that file
  exists)
- Test: `tests/test_check_render.py` (add cases)

**Interfaces:**
- Produces:
  - Finding kind `NA_VALUE: <token> …context…` for a standalone `NA`, `NaN`, `Inf` or `-Inf` in
    page text.
  - Finding kind `OVERFULL: <n>pt` for each `Overfull \hbox (Npt too wide)` with N > 1.0 in the
    LaTeX log.

- [ ] **Step 1: Write the failing tests.** Use `.txt` input as the existing tests do:
  - `The estimate is NA percent.` → `NA_VALUE`.
  - `NASA` and `N/A` → no finding.
  - A log file containing `Overfull \hbox (12.5pt too wide) in paragraph` → `OVERFULL: 12.5pt`;
    `(0.4pt too wide)` → none.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement.** In `findings()`:
  `for m in re.finditer(r"(?<![\w./-])(-?Inf|NaN|NA)(?![\w/-])", text): out.append(f"NA_VALUE: {m.group(1)} …{text[max(0,m.start()-40):m.end()+40]!r}")`.
  Then add `--latex-log` (a Path, optional) parsed with
  `re.finditer(r"Overfull \\hbox \((\d+(?:\.\d+)?)pt too wide\)", log)`, emitting kind `OVERFULL`
  for values > 1.0. Unverified: whether Quarto keeps `<stem>.log` after a successful render.
  `critic_inputs` passes the log only when the file exists and writes `latex log: absent`
  otherwise.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_check_render.py tests/test_pipeline.py`.
  Expected: all pass.
- [ ] **Step 5: Commit:** `check_render: NA/NaN/Inf on the page; overfull boxes from the LaTeX log`
  (with the trailer).

---

### Task 12: Pre-commit check, cold render and the git hooks

**Files:**
- Modify: `scripts/pipeline.py` (`render --cold` and `commit-check` subcommands)
- Create: `hooks/git/pre-commit`, `hooks/git/post-commit` (both executable)
- Modify: `apply.sh` (set `core.hooksPath` after linking)
- Modify: `scripts/check_install.sh` (a `git-hooks-path` check; `hooks-wired` fails on a
  settings.json command naming `hooks/git/`)
- Modify: `scripts/check_refs.py` (`crit_hooks_readme` skips `hooks/git/` explicitly and flags a
  table row naming `git/…`)
- Modify: `hooks/README.md` (a "Git hooks" section, outside the Claude hook table)
- Test: `tests/test_commit_check.py`, `tests/test_check_refs.py` (cases),
  `tests/test_check_install.py` (cases)

**Interfaces:**
- Consumes: Tasks 1, 3, 8 and 9, `run_script`, `qmd_chunks.extract`.
- Produces:
  - `pipeline.py render --cold`: removes `<stem>_cache/`, runs `quarto render`, and on exit 0
    writes `quality_reports/cold_render.json` `{"manuscript_sha256": …, "at": …}`.
  - `reestimation(root) -> Tuple[bool, str]`: True when the staged
    `render_fingerprint.json` differs from HEAD's in `estimates_hash`, `data_hash` or
    `design_hash`, or HEAD has none. This is how "the commit that lands the re-estimation"
    (spec §0.6) is recognised: a model-chunk change that moves estimates changes `estimates_hash`,
    a data change changes `data_hash`, an amendment changes `design_hash`. Data under `data/raw/`
    is gitignored, so the fingerprint is the only committed trace of a data change.
  - `pipeline.py commit-check`. Exit 0 when no manuscript is declared, or when neither the
    manuscript nor the fingerprint is staged. Otherwise exit 1 on any of:
    - design status not `SIGNED`/`NOT-RETROFITTED`;
    - unstaged changes to the manuscript or to `render_fingerprint.json`;
    - `prose_number_check.py` ≠ 0; `quarto_structure_check.py` ≠ 0;
    - chunk code differing from HEAD while `cold_render.json`'s sha ≠ the manuscript's sha;
    - a stale `manuscript` component (`stale_components(root).get("manuscript")`) **unless**
      `reestimation()` is True, in which case it prints `WARN re-estimation commit — stale: …;
      every later manuscript commit is refused until the manuscript is re-scored`. Stale
      `strategy`/`referees` only print `WARN stale: …` and never block (author ruling 2026-10-17);
    - `amendment_count(root) > 0` and no chunk labelled `tbl-design-changes` in the manuscript.
  - `hooks/git/post-commit` runs `pipeline.py ledger settle` and always exits 0.

- [ ] **Step 1: Write the failing tests.** Use a git-initialised `FixtureCase` copy.
  - No CLAUDE.md → exit 0 (Review Focus 7).
  - Nothing relevant staged → exit 0 quickly.
  - Stage a prose-only change → exit 0.
  - Stage a chunk-code change without a cold render → exit 1 `cold render`; write
    `cold_render.json` with the current sha → exit 0.
  - Unsigned design block → exit 1 `design`.
  - Typed literal in prose → exit 1 `prose`.
  - **Stale, prose-only commit:** commit fingerprint `A`, record a manuscript score under `A`,
    commit fingerprint `B` (the re-estimation commit, see next case), then stage a prose-only change
    → exit 1 `STALE`.
  - **Stale, re-estimation commit:** with a manuscript score under `A`, stage a chunk-code change,
    a cold-render receipt and a fingerprint with `estimates_hash: "B"` → exit 0 with
    `WARN re-estimation commit`.
  - **Data-only re-estimation:** stage a fingerprint whose `data_hash` alone changed → exit 0 WARN.
  - After `record-score` under `B` → the prose-only commit exits 0.
  - **Stale strategy only:** manuscript score under the current fingerprint, strategy score under
    an older one, stage a prose-only change → exit 0 with `WARN stale: strategy`.
  - A fingerprint modified but not staged → exit 1 `stage quality_reports/render_fingerprint.json`.
  - Amendment rows in the CSV and no `tbl-design-changes` chunk → exit 1 `tbl-design-changes`;
    adding a chunk with that label → exit 0.
  - Mock `quarto` for `render --cold` by prepending a temp `PATH` dir holding a `quarto` script
    that exits 0; assert the cache dir was removed and `cold_render.json` written.
  - Through git: install `hooks/git` as `core.hooksPath` in the temp repo; `git commit` of a stale
    prose-only change exits non-zero; the post-commit hook settles a `closed pending` row after
    the re-scored commit.
  - `tests/test_check_refs.py`: a `hooks/git/pre-commit` with no README row passes `hooks-readme`;
    a README table row naming `git/pre-commit` fails it.
  - `tests/test_check_install.py`: `git-hooks-path` FAILs when `core.hooksPath` is unset, when it
    names another path, and when `.claude/hooks/git/pre-commit` is missing (the fresh-worktree
    case); PASSes when set and present. `hooks-wired` FAILs on a settings command naming
    `hooks/git/`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement.** For chunk-code changes, compare
  `qmd_chunks.extract(head_text.split("\n"))` with the same call on the working text. Get
  `head_text` from `git show HEAD:<ms_rel>`; when that fails (new file), treat the code as
  changed. Staged detection: `git diff --cached --name-only`. Unstaged detection:
  `git diff --quiet -- <path>` returns 1. HEAD's fingerprint: `git show HEAD:quality_reports/render_fingerprint.json`.

  `hooks/git/pre-commit`:

```sh
#!/bin/sh
# research-claude pre-commit: the manuscript gates run on every commit, whatever made it (spec §7).
# Installed by apply.sh as core.hooksPath = .claude/hooks/git. Never bypass with --no-verify.
top=$(git rev-parse --show-toplevel) || exit 0
[ -f "$top/.claude/scripts/pipeline.py" ] || exit 0
exec python3 "$top/.claude/scripts/pipeline.py" --root "$top" commit-check
```

  `hooks/git/post-commit`:

```sh
#!/bin/sh
# research-claude post-commit: close ledger rows fixed during a stale window against this commit (spec §0.6).
top=$(git rev-parse --show-toplevel) || exit 0
[ -f "$top/.claude/scripts/pipeline.py" ] || exit 0
python3 "$top/.claude/scripts/pipeline.py" --root "$top" ledger settle >/dev/null 2>&1
exit 0
```

  Make both executable in git:
  `chmod +x hooks/git/pre-commit hooks/git/post-commit && git add --chmod=+x hooks/git/pre-commit hooks/git/post-commit`.

  In `apply.sh`, after the `skills agents rules hooks` loop (which links `hooks/git` as one
  directory link):

```bash
  if git -C "$PROJECT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    cur="$(git -C "$PROJECT_DIR" config --get core.hooksPath || true)"
    gd="$(git -C "$PROJECT_DIR" rev-parse --git-dir)"; case "$gd" in /*) ;; *) gd="$PROJECT_DIR/$gd";; esac
    own="$(ls "$gd/hooks" 2>/dev/null | grep -v '\.sample$' || true)"
    if [[ -n "$cur" && "$cur" != ".claude/hooks/git" ]]; then echo "  WARN core.hooksPath is $cur — left alone; pre-commit gate NOT installed"
    elif [[ -z "$cur" && -n "$own" ]]; then echo "  WARN .git/hooks has its own hooks ($own) — pre-commit gate NOT installed; merge by hand"
    else git -C "$PROJECT_DIR" config core.hooksPath .claude/hooks/git; echo "  git hooks: core.hooksPath = .claude/hooks/git"; fi
  fi
```

  Tested (git 2.54): a symlinked `.claude/hooks/git` directory runs its `pre-commit`; a
  `core.hooksPath` naming a missing directory runs no hook and the commit exits 0 — which is what
  a fresh worktree without the links gets. So `check_install.sh`, beside `claude-md-size`:
  `ok git-hooks-path` only when `git -C "$P" config --get core.hooksPath` equals
  `.claude/hooks/git` **and** `$P/.claude/hooks/git/pre-commit` is executable; otherwise
  `bad git-hooks-path "pre-commit gate not installed here — run apply.sh --project-dir <this checkout> --link"`.
  `install-check.py` already surfaces that FAIL at session start in a worktree.

  Auditors: in `scripts/check_refs.py` `crit_hooks_readme`, keep the top-level `*.py`/`*.sh` glob,
  add a comment that `hooks/git/` holds git hooks and is never a Claude hook, and flag any table row
  whose name starts with `git/`. In `check_install.sh` section 10, extend the existing `post-merge`
  test to any command containing `hooks/git/`. `hooks/README.md` gains a "Git hooks" section (not a
  table row): `hooks/git/pre-commit` runs `pipeline.py commit-check`; `hooks/git/post-commit` runs
  `pipeline.py ledger settle`; both are installed by `core.hooksPath`, never wired in settings.json.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_commit_check.py tests/test_check_install.py tests/test_check_refs.py tests/test_apply_lock.py tests/test_run_hook.py && ./scripts/check_fork.sh >/dev/null; echo $?`.
  Expected: all pass; `0`. Update any `test_check_install` fixture that now lacks `core.hooksPath`
  by having its setup run `git config core.hooksPath .claude/hooks/git` and link
  `.claude/hooks/git`.
- [ ] **Step 5: Commit:** `git hooks: pre-commit runs commit-check (staleness blocks except the re-estimation commit); post-commit settles the ledger; apply.sh sets core.hooksPath`
  (with the trailer).

---

### Task 13: Shipped-tree and instruction checks; rule, skill and agent text

**Files:**
- Create: `scripts/check_single_manuscript.py`; add it to `scripts/SHIPPED`; call it from
  `scripts/check_fork.sh` through `py check_single_manuscript.py` in the "seeds and shipped
  scripts" section
- Modify: `scripts/check_install.sh` (`claude-md-size` warn → bad; a new `claude-md-design-facts`
  check)
- Modify: `CLAUDE.md` (research-claude): import core rules
- Modify: `rules/core.md` (rules 13–16), `rules/agents.md` §3 and §6, `rules/quarto-empirical.md`
  (a new section), `rules/content-invariants.md` (INV-11 extended to words; INV-18 names the
  fingerprint chunk)
- Modify: `skills/analyze/SKILL.md`, `skills/write/SKILL.md`, `skills/revise/SKILL.md`,
  `skills/review/SKILL.md`, `skills/pipeline/SKILL.md`
- Modify: `agents/writer-critic.md`, `agents/coder-critic.md`, `agents/coder.md`,
  `agents/strategist-critic.md`, `agents/editor.md`, `agents/domain-referee.md`,
  `agents/methods-referee.md`
- Test: `tests/test_check_single_manuscript.py`, `tests/test_check_install.py` (cases),
  `tests/test_rule_reads.py` (must stay green)

**Interfaces:**
- Produces: `check_single_manuscript.py`, which exits 1 when `source(` or
  `readRDS(…output|results…)` appears in the code of any shipped `.R`, `.R.txt`, `.qmd` or `.Rmd`
  file, or inside a fenced `r`/`{r}` block of a shipped `.md` file. A line carrying
  `residue:prohibition` is skipped.

- [ ] **Step 1: Write the failing tests.**
  - `check_single_manuscript`: a temp tree with `skills/x/SKILL.md` containing
    ```` ```r\nsource("a.R")\n``` ```` → exit 1. The same fence with a `# residue:prohibition`
    line → exit 0. Prose mentioning `source()` outside a fence → exit 0.
  - `check_install`: a project CLAUDE.md of 61 lines → FAIL `claude-md-size`. A CLAUDE.md with
    `Treatment date: 2024-10-01` → FAIL `claude-md-design-facts`. A line `- H1: prices fall` →
    FAIL.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement the checks.** Before wiring `check_single_manuscript.py` into
  `check_fork.sh`, run it on the tree: a hit inside an `r` fence that shows a prohibited pattern on
  purpose gets a `residue:prohibition` marker; any other hit is a real defect to fix here, because
  `check_fork.sh` must stay at exit 0. In `check_install.sh`, change `warn claude-md-size` to
  `bad claude-md-size`, and add:

```bash
  local facts; facts="$(grep -nEi '(treat(ment|ed)|event)[^.]{0,40}(19|20)[0-9]{2}-[0-9]{2}(-[0-9]{2})?|^[[:space:]]*[-*]?[[:space:]]*\**H[0-9]+\**[[:space:]]*[:.)]' "$P/CLAUDE.md" 2>/dev/null || true)"
  [[ -z "$facts" ]] && ok claude-md-design-facts "none" || bad claude-md-design-facts "design facts belong in the manuscript's design: block: $(echo "$facts" | head -2 | tr '\n' ' ')"
```

- [ ] **Step 4: Edit the text.** Re-read `rules/core.md` first: it holds rules 1–12. Insert
  exactly the following.
  - Research-claude `CLAUDE.md`, directly under the title paragraph:

    ```
    **Pipeline core rules, loaded here too** — a session redesigning the pipeline carries the
    rules the papers run under: @rules/core.md
    ```

    Verify the import loads (unverified until run; test it, don't assume):
    `claude -p "Without using any tools, quote rule 1 under '## The manuscript' from your loaded instructions."`
    run from the repo root, with no timeout. Expected: the "One manuscript" text. If it is not
    quoted, inline the core rules instead and record that the import did not work.
  - `rules/core.md`, a new `## Design, results and review` section after `## Code`:

    ```
    13. **The design lives in the manuscript's `design:` block, and the author signs it in chat.**
        The block holds hypotheses → model objects, treatment with a located source quote, sample,
        inference rule, and the results of the power and size checks, which run in `explorations/`.
        The author approves with one line of their own message — `approve design sign`, or
        `approve design unlock: <reason>` — which issues a one-time token; only then does the
        session run `pipeline.py design sign|unlock`. Every amendment is recorded in
        `quality_reports/design_amendments.csv` and disclosed by a `tbl-design-changes` chunk.
        Adjusting a model after seeing results is normal; recording it is what is required.
        `[hook: design-token, design-guard; script: design-lock predicate, commit-check]`
    14. **Every result word is bound to the model:** helper output (`rc_sig`, `rc_stars`, `rc_dir`,
        `rc_cmp`, `rc_num`, `rc_pct`, pasted into the setup chunk from
        `.claude/templates/claims-helpers.R.txt`), a raw inline `if`, or a typed word in a sentence
        that carries an inline `stopifnot()` result guard. Stars: `*` p ≤ 0.10, `**` p ≤ 0.05,
        `***` p ≤ 0.01; "statistically significant" names its level. `[script: prose_number_check.py]`
    15. **A re-estimation reopens review mechanically.** Scores carry the results fingerprint; a
        strategy, manuscript or referee score earned under another one is stale, and manuscript
        commits are refused until it is re-scored (the re-estimation commit itself passes).
        Findings live in `quality_reports/findings_ledger.md`. A passed, unchanged target is not
        re-reviewed. `[script: pipeline.py; hook: pre-commit, stale-stages]`
    16. **Unattended runs make rulings and continue.** Log each with `pipeline.py ruling add`
        (date, decision, the alternative, reason) in `quality_reports/rulings_log.md`. Two hard
        stops: a ruling that would contradict a decision the author recorded, and any change to
        the `design:` block. Write those with `pipeline.py question add` to
        `quality_reports/questions_for_author.md` and stop that line of work.
        `[judgment; script: ledger rulings]`
    ```

  - `rules/agents.md` §6: replace the paragraph "**The finding ledger.** …" with:
    "**The finding ledger** is `quality_reports/findings_ledger.md`, written only through
    `pipeline.py ledger`; `post <creator>` refuses while a row for that creator is open or a
    proposal is undecided. The whole-manuscript re-review is enforced by the fingerprint:
    `record-score` stores the results fingerprint, and a strategy, manuscript or referee score
    earned under another one is STALE (`pipeline.py score`, `next`, `pre`, `post`, `stale`, and the
    pre-commit check). A fix made while review is stale is closed with `ledger close ID --pending`
    and settles to the commit that ends the stale window. A decline or a proposal decision is a
    ruling and is logged (core rule 16)."
  - `rules/agents.md` §3: add a bullet after "Each round is a fresh foreground `Agent` dispatch":
    "Round 1 is a cold read. From round 2, the dispatching skill runs `pipeline.py critic-context
    <critic>` and names the file in the prompt: the critic verifies each ledger row's closure,
    flags regressions, reviews changed text and every summary sentence, and labels any other new
    finding `[missed-earlier]`. Before any dispatch the skill runs `pipeline.py dispatch-ok
    <critic>`; `PASSED-UNCHANGED` means no dispatch unless the author asked."
  - `rules/quarto-empirical.md`, a new section `## Design block and claim helpers` before the
    caching section. It covers:
    - the `design:` YAML example from spec §4 (no α, no verdict words; `checks` with `file:`);
    - power and size checks as `explorations/power.qmd` and `explorations/size.qmd`, their
      results copied into `design.checks` before signing, and re-run on an amendment touching the
      inference rule, sample, treatment or an outcome; never a check chunk in the manuscript;
    - the setup-chunk lines `design <- rc_design("<manuscript>.qmd")` and
      `knitr::opts_chunk$set(cache.extra = list(rc_design_hash(design), rc_data_hash()))`, and that
      no chunk sets its own `cache.extra` (it would replace the global key);
    - `options(modelsummary_stars_note = FALSE)` in the setup chunk, with the star legend passed in
      `notes` (Task 14 says why);
    - the final chunk `rc_fingerprint()` (label `fingerprint`, `cache: false`, `include: false`),
      and that `quality_reports/render_fingerprint.json` is committed;
    - the `tbl-design-changes` chunk, required once an amendment exists, cited in the prose with
      `@tbl-design-changes`; the author writes the prose around it:

      ```r
      #| label: tbl-design-changes
      #| cache: false
      #| tbl-cap: "Changes to the research design"
      design_changes <- read.csv(here("quality_reports/design_amendments.csv"), stringsAsFactors = FALSE)
      knitr::kable(design_changes, col.names = c("Date", "Field", "Before", "After", "Reason"))
      ```

    - result guards: `` `r local({stopifnot("<claim>" = <condition>); ""})` `` in the sentence it
      guards (`rules/readable-code.md` §5);
    - "`pipeline.py render --cold` before committing a model-chunk change".
  - `rules/content-invariants.md`:
    - INV-11: append "— and every significance, direction, comparison or universality word beside
      a value is helper output, a raw inline `if`, or sits in a sentence with a `stopifnot()` result
      guard (rule 14 of core.md)." Update its enforcement row: the verdict ceiling defaults to 0
      once the manuscript has a `design:` block.
    - INV-18: append "The one exception is the `fingerprint` chunk: `rc_fingerprint()` writes
      `quality_reports/render_fingerprint.json`, which `pipeline.py` reads to decide which reviews
      a re-estimation reopens."
  - Skills:
    - `/analyze` Step 0 (replace "informational only"), `/write` (the first step of `[section]`
      mode), `/revise` Step 1 and `/review` before dispatch each run `pipeline.py pre <creator>` as
      a **blocking** step: "a FAIL stops the skill and is reported". Add the step where a skill has
      none.
    - Each skill that dispatches a critic adds, before the dispatch: run `pipeline.py dispatch-ok
      <critic>`; from round 2 run `pipeline.py critic-context <critic>`; after saving each report,
      add one ledger row per finding with `pipeline.py ledger add`.
    - `/review --peer` and `/revise`: a referee's request to add an analysis or change the design
      is added with `--proposal`; nothing is built until `ledger accept`. An unattended accept or
      reject is a ruling (logged by the ledger command); a proposal touching `design:` is a hard
      stop until the author approves `design unlock` in chat.
    - `/analyze`: before the first estimate, if the manuscript has a `design:` block that is not
      signed, run the power and size explorations, record their results, and ask the author to
      approve `design sign` in chat.
    - `/pipeline` adds core rule 16's two hard stops as stop conditions, and names
      `pipeline.py ruling add` for every other decision an unattended run makes.
  - Agents:
    - `writer-critic`, `coder-critic`: a `## Rounds 2+` section matching the agents.md §3 bullet.
    - `writer-critic` also adds: "Judge claims against the rendered PDF named in the critic-inputs
      log, not the `.qmd` source. A typed result word is a finding unless it is helper output, a
      raw inline `if`, or its sentence carries a `stopifnot()` guard."
    - `coder`: "When a ledger finding is mechanically checkable, close it with a `stopifnot()`
      guard beside the claim and name the guard (`ledger close … --guard`)."
    - `strategist-critic`: "Score the memo against the manuscript's `design:` block. Every
      treatment, date and institutional fact must carry a located quote from a source you read in
      this dispatch; a fact marked verified without one is a deduction, whatever the memo's
      internal logic."
    - `editor`, `domain-referee`, `methods-referee`: "A request for a new analysis or a design
      change is a PROPOSAL, labelled as such; the author decides."
- [ ] **Step 5:** Run `python3 -m pytest -q tests && ./scripts/check_fork.sh; echo "check_fork exit $?"`.
  Expected: pytest is green and `check_fork exit 0`. Then commit:
  `rules, skills, agents: design lock signed in chat, bound result words, ledger, rulings; check_single_manuscript; CLAUDE.md caps fail`
  (with the trailer).

---

### Task 14: Star convention and post-results sweep of the shipped tree

**Files:**
- Modify: `skills/analyze/references/table-standards.md` (line ~50 convention, line ~60 call)
- Modify: `skills/analyze/templates/chunk-structure.md` (line ~73 call)
- Modify: `rules/quarto-pdf.md` (~69), `rules/quarto-word.md` (~80), `rules/quarto-empirical.md`
  (~168): the `modelsummary` example calls
- Modify: `rules/content-invariants.md` (INV-4: "Default: stars with a note defining the
  thresholds" → "Default: `*` p ≤ 0.10, `**` p ≤ 0.05, `***` p ≤ 0.01, stated in the note")
- Modify: `references/journal-profiles.md` (the default line ~27, and the three profiles at ~412,
  ~430 and ~448 that restate the standard cutoffs; the profiles with other cutoffs stay as they are)
- Modify: `agents/editor.md` (~322: "Heterogeneity must be pre-specified or clearly exploratory;
  no p-hacking via subgroup analysis.")
- Test: `tests/test_star_convention.py`

**Interfaces:**
- Tested (modelsummary 2.6.0, `modelsummary:::make_stars`): stars are assigned with `p <= cutoff`
  (p = 0.05 gets `**`), which matches the convention; but the automatic note prints `p < 0.1`.
  Tested: `options(modelsummary_stars_note = FALSE)` suppresses that note, and a `notes` string
  then carries the legend. So every shipped `modelsummary` example keeps
  `stars = c("*" = 0.10, "**" = 0.05, "***" = 0.01)`, sets the option in the setup chunk, and adds
  the legend `"* p ≤ 0.10, ** p ≤ 0.05, *** p ≤ 0.01"` to `notes`. Unverified: that the `≤` glyph
  renders in every PDF font the rules allow; Task 15's render checks the fixture's PDF text, and
  if the glyph is missing the shipped examples switch to `$\\le$` (the checker accepts both).

- [ ] **Step 1: Write the failing test** `tests/test_star_convention.py`: scan `agents skills rules
  references templates` for `p\s*<\s*0?\.(?:10?|05|01)\b` and `p<0` forms; every hit must be on a
  line that also names a profile with other cutoffs (`APSA`) or carries `residue:prohibition`.
  A second test asserts no shipped file contains `results seen` / `results_seen` /
  `--results-seen`, and that `agents/editor.md` no longer contains `p-hacking`.
- [ ] **Step 2:** Run `python3 -m pytest -q tests/test_star_convention.py`. Expected: FAIL, listing
  the lines above.
- [ ] **Step 3: Edit.**
  - Every standard-convention statement: `<` → `≤` (`*` p ≤ 0.10, `**` p ≤ 0.05, `***` p ≤ 0.01).
  - Every shipped `modelsummary` example: add `notes = c("<existing note>", "* p ≤ 0.10, ** p ≤ 0.05, *** p ≤ 0.01")`
    (or extend the existing string), and add `options(modelsummary_stars_note = FALSE)` to the
    setup-chunk examples in `chunk-structure.md`, `quarto-pdf.md`, `quarto-word.md` and
    `quarto-empirical.md`, with a one-line comment: "tested: modelsummary 2.6.0 stars with p ≤
    cutoff but its automatic note says p <".
  - `agents/editor.md`: replace the heterogeneity line with "Heterogeneity analyses report every
    subgroup examined and how it was chosen, not only the significant ones; a paper with a
    pre-analysis plan says which were pre-specified." No other shipped line treats a change after
    estimation as a defect: the remaining pre-registration text sits in the PAP templates
    (`skills/strategize/templates/pap-*`), `methods-referee` ("if PAP exists"), and the discipline
    and journal references, and stays.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_star_convention.py tests/test_prose_number_surface.py && ./scripts/check_fork.sh >/dev/null; echo $?`.
  Expected: all pass; `0`.
- [ ] **Step 5: Commit:** `star convention p ≤ 0.10/0.05/0.01 across the shipped tree; modelsummary legend; no post-results-defect text`
  (with the trailer).

---

### Task 15: Fixture manuscript adopts the contract; defect tests

**Files:**
- Modify: `tests/fixture-project/manuscript_fixture.qmd` (design block, helpers, cache key,
  fingerprint chunk, helper-generated words)
- Create: `tests/fixture-project/explorations/power.qmd`, `tests/fixture-project/explorations/size.qmd`
- Modify: `tests/test_pipeline.py` (`FixtureCase.setUp` signs the design through a test token)
- Modify: `tests/run_fixture.sh` (sign the design after `state-init`)
- Create: `tests/test_design_lock_fixture.py`

**Interfaces:**
- Consumes: Tasks 1–14. The lock is generated by `pipeline.py design sign` in each test's setup,
  never committed, because it depends on the block.

- [ ] **Step 1: Edit the fixture** (readable code; run the r-naming grep on every file you touch).
  - Paste the helpers into the setup chunk; add `options(modelsummary_stars_note = FALSE)`,
    `design <- rc_design("manuscript_fixture.qmd")` and the global `cache.extra` line. Delete the
    `build-panel` chunk's own `cache.extra` (it would replace the global key).
  - Add the `design:` block: H1's `spec` is `m_main` (outcome `outcome`, direction from the
    synthetic design), the inference rule is cluster-robust by unit, the treatment date is the
    fixture's adoption year with a source quote from `references.bib`'s fixture entry, and `checks`
    record the results of the two explorations with their `file:`.
  - `explorations/power.qmd`: a simulated MDE on `data/raw/panel.csv` with `fixest`, drawing count
    stated in a named constant; `explorations/size.qmd`: 200 placebo permutations of the adoption
    year, reporting the rejection rate at 0.10. Each states its result at the end; copy both into
    `design.checks`.
  - Add a final `fingerprint` chunk (`cache: false`, `include: false`) calling `rc_fingerprint()`.
  - Rewrite the result sentences with `rc_*` (the direction and significance of `beta_hat` via
    `rc_dir` and `rc_sig`), and add the star legend to `tbl-main`'s `notes`.

  Run `quarto render tests/fixture-project/manuscript_fixture.qmd` in a temp copy: exit 0,
  `render_fingerprint.json` written, and the PDF text (via `check_render.py`) shows the star legend
  with no missing glyph.
- [ ] **Step 2:** Update `FixtureCase.setUp` to issue a test token (`author_token.issue`), run
  `design sign --signer fixture`, and write a stub `quality_reports/render_fingerprint.json`
  (`estimates_hash: "fixture"`): once a lock exists, a score recorded with no fingerprint file is
  stale (Task 8), so every existing score test needs one; the staleness tests rewrite it. Do the
  same in `tests/run_fixture.sh` right after `state-init` (`python3 -c` with the worktree's
  `scripts/` on `sys.path`). Re-run `tests/test_pipeline.py`: green.
- [ ] **Step 3: Write the defect tests** in `tests/test_design_lock_fixture.py`. Each copies the
  fixture to a temp dir, plants one defect, and asserts its check fails; the clean copy passes
  every check. Tests marked (render) skip when `quarto` or `Rscript` is missing.
  - A typed verdict word with no guard → `prose_number_check` exit 1; the same word with a
    `stopifnot()` guard in the sentence → exit 0.
  - A direction verb typed against the sign ("rose" beside a negative `beta_hat`) → prose check
    exit 1; with the guard `stopifnot("rose" = beta_hat > 0)` → (render) exit non-zero.
  - An NA value: H1's object set to `NA` in a chunk → (render) exit non-zero, `not one finite
    number` in the output.
  - Pipeline jargon in prose ("the governing p") → exit 1 `PIPELINE JARGON`.
  - A typed number in a table note → exit 1.
  - A typed number in the abstract → exit 1.
  - An edit to the design block without an unlock → design-guard denies it; written directly to
    disk, `commit-check` exits 1 `CHANGED`.
  - `design sign` without an author token → exit 1 `no author token`.
  - (render) A model cache that survives a data change: render, multiply the outcome column of
    `data/raw/panel.csv` by 2, re-render with a warm cache → `estimates_hash` and `data_hash`
    change.
  - (render) A robustness model named in no hypothesis (`m_robust` in its own chunk): changing its
    formula changes `estimates_hash`.
  - (render) A stale writer score blocks a prose-only commit while the re-estimation commit passes:
    record a manuscript score, mutate the data, re-render cold, commit with the new fingerprint →
    exit 0 WARN; then a prose-only commit → exit 1 `STALE`.
  - An amendment without the `tbl-design-changes` chunk: token, unlock, change the sample, update
    `design.checks`, token, sign → `commit-check` exit 1 `tbl-design-changes`; adding the chunk
    → exit 0.
  - An open ledger row at `post writer` → exit 1 `ledger-closed`.
  - A critic dispatch on a passed target → `dispatch-ok writer-critic` exit 1 `PASSED-UNCHANGED`.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_design_lock_fixture.py tests/test_pipeline.py && tests/run_fixture.sh`.
  Expected: all pass. Fix the fixture, never the gate, when the fixture fails a gate.
- [ ] **Step 5: Commit:** `fixture: design block signed by test token, claim helpers, fingerprint, explorations; defect tests`
  (with the trailer).

---

### Task 16: Release — review, re-link, live evals, merge

**Files:** `docs/SESSION_REPORT.md`, `docs/improvement-ledger.md` (L-008 → `landed <sha>`),
`CLAUDE.md` "Start here" pointer.

- [ ] **Step 1:** Run a whole-branch review (superpowers:requesting-code-review) and fix its
  findings.
- [ ] **Step 2:** Run `python3 -m pytest -q tests` (green) and `./scripts/check_fork.sh` (exit 0).
- [ ] **Step 3:** Before merging, run `python3 scripts/pipeline.py --root <p> commit-check` with
  the manuscript staged (`git -C <p> add -N` is enough to make it "staged" for the check; do not
  commit) in each paper project, and list which papers the new pre-commit hook would block and why
  (most are not retrofitted, so this is the surface scans and the prose check). Report the list to
  the author; installing a blocking hook in a paper that fails it is the author's decision.
- [ ] **Step 4:** Merge to `main` locally: `git merge --no-ff feat/design-lock-prose-binding`.
  The linked papers see the change from this point.
- [ ] **Step 5:** For each paper project the author approved in Step 3, run
  `./apply.sh --project-dir <p> --link` and `python3 scripts/wire_guard_hooks.py <p>/.claude/settings.json`.
  Then run `./scripts/check_install.sh --all`.
  - Expected: PASS, except `claude-md-size` / `claude-md-design-facts` / `gitignore-covers` FAILs
    in papers not yet retrofitted, and `git-hooks-path` in papers the author held back. List them;
    Task 17 clears them.
  - `--tip` projects need external imports approved first (README).
- [ ] **Step 6:** Run the live evals with no timeout (never set `EVAL_TIMEOUT`/`LIVE_TIMEOUT`):
  `tests/evals/analyze.sh`, `write.sh`, `revise.sh` and `review.sh`, then
  `tests/run_fixture.sh --live`. No eval prompt contains an approval line. A red run is diagnosed
  after it finishes, never killed.
- [ ] **Step 7:** Update the `docs/SESSION_REPORT.md` entry, mark ledger L-008 landed, and repoint
  the CLAUDE.md "Start here" paragraph at this plan. Commit (with the trailer).

---

### Task 17: Retrofit each paper (author-gated; project repos)

Run once per paper. The rewritten papers go first; the order is the author's call. This happens
in the paper's own repo, with a project commit after each step. **Stop and wait for the author at
every `AUTHOR` step.**

- [ ] **Step 1:** Move the project CLAUDE.md design facts (treatment dates, hypothesis lists) into
  a draft `design:` block written as the paper stands today, and cut CLAUDE.md to ≤ 60 lines with
  the history in the project's docs history file. Add `.claude/state/design_token.json` to the
  project `.gitignore`. Seed the paper's existing design changes, one
  `pipeline.py design seed-amendment` per change (date, field, old, new, reason), before any
  signing.
- [ ] **Step 2:** Write `explorations/power.qmd` and `explorations/size.qmd` for the paper's
  actual design, render them, and report the power and size results to the author verbatim. Record
  them in `design.checks` with their `file:`.
- [ ] **Step 3 — AUTHOR:** The author reviews the block and the check results. A size check outside
  0.07–0.13 at the 10% level, an MDE above the target effect, or a design with no strategy memo or
  strategist review is resolved by the author before signing. The author then approves in chat
  with the line `approve design sign`, and the session runs
  `python3 .claude/scripts/pipeline.py design sign --signer <author's name>`.
- [ ] **Step 4:** Paste the helpers, the cache key, the `fingerprint` chunk and (when the CSV has
  rows) the `tbl-design-changes` chunk; alias existing project helpers to `rc_*` inside the setup
  chunk. Run `prose_number_check.py` and save the failures as
  `quality_reports/plans/<date>_binding-fix-list.md`. Fix them, render with
  `pipeline.py render --cold`, and commit.
- [ ] **Step 5:** Seed the ledger: one `pipeline.py ledger add` per still-open finding in the
  current critic reports, with the author confirming which findings are still open.
- [ ] **Step 6:** Run `pipeline.py critic-inputs` and dispatch one whole-manuscript writer-critic
  (round 1, cold) under the new fingerprint, recording with `record-score`. Then run
  `pipeline.py stale`: a strategy or referee score recorded before the retrofit carries no
  fingerprint and is stale. That does not block commits; re-score those stages in the normal
  pipeline order (strategist-critic against the signed `design:` block).
  Then run `check_install.sh` for the project: PASS.
