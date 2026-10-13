# Design lock and prose binding — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A paper proceeds only on an author-signed, power- and size-checked design, all of it in
the manuscript's own front matter. Every result-describing word is generated from the model
objects. A re-estimation mechanically reopens the reviews it invalidates. Reviews converge
through a finding ledger.

**Architecture:**
- The design lives in a `design:` front-matter block of the single `.qmd`. The lock is a hash of
  that block's normalised text, kept in `quality_reports/design_lock.json`.
- The author signs and unlocks the design from their own terminal. A PreToolUse hook stops
  agents from editing a signed block, or from running the sign/unlock commands.
- Claim helpers (base R, `rc_` prefix) are pasted into the setup chunk from a template. They key
  every chunk cache on the design and data hashes, and write a results fingerprint.
- `pipeline.py` compares that fingerprint against every score. It also owns the finding ledger
  and a pre-commit check.

**Tech Stack:** Python 3.9 stdlib (the `scripts/pipeline.py` convention), bash, base R plus
`rmarkdown`, Quarto/knitr, pytest/unittest.

**Spec:** `docs/superpowers/specs/2026-10-12-design-lock-and-prose-binding-design.md`. §0 of the
spec records the changes this plan made to it after reading the code.

## Global Constraints

- **One manuscript (core rule 1).** No results file, no analysis script and no `source()` in any
  shipped manuscript code. Helpers are pasted into the setup chunk, never sourced.
- **Python scripts:** stdlib only, Python 3.9 (`pipeline.py` header). No PyYAML.
- **R helpers:** base R plus `rmarkdown::yaml_front_matter`. Every exported name carries the
  `rc_` prefix, and no base/builtin name is assigned at top level (`~/.claude/references/r-naming.md`).
- **Live evals:** never pass, add or raise a timeout (`EVAL_TIMEOUT=0` / `LIVE_TIMEOUT=0`).
- **Shipped files:** no project, journal or dataset name anywhere under
  `agents/ skills/ rules/ hooks/ templates/`.
- **Commits:** never `--no-verify`. Local commits only; no push.
- **Work in a git worktree,** never on the linked working copy
  (`~/Academic/research-claude`). Every save there is live in all six papers. Merge to `main`
  only in Task 14.
- **Hooks fail open on internal error** (the existing hook convention). The `pipeline.py`
  predicates fail closed.
- **`check_fork.sh` baseline:** on `main` at `b4538e9` it already FAILs `project-identity`,
  `project-nouns`, `skill-refs`, `artifact-paths` and `path-resolves`. This plan must add no new
  FAIL label, and must not fix those (separate task).

## Review Focus

1. **A manuscript with no `design:` block** (a paper not yet retrofitted, or the research-claude
   fixture before Task 13). Every new check prints `not retrofitted` and passes. Once a
   `design_lock.json` exists, every check fails closed. Tests: Tasks 1, 2, 7 and 11.
2. **Front-matter noise:** CRLF line endings, tabs, comments, blank lines, key order unchanged.
   The design hash ignores comments, trailing whitespace and CRLF, and changes on any value
   change. Test: Task 1.
3. **An edit to YAML outside the `design:` block while locked** (title, date, format). It must be
   allowed. Test: Task 3.
4. **A hypothesis `spec:` naming a model object that does not exist, or a `fixest` model.**
   `rc_fingerprint()` stops and names the missing object; it works on `fixest` through
   `coef`/`vcov`/`nobs`. Test: Task 4.
5. **A commit in a repo with no declared manuscript, or one that doesn't stage the manuscript.**
   The pre-commit check exits 0 fast. Test: Task 11.

---

### Task 0: Worktree and baseline

**Files:** none (environment).

- [ ] **Step 1:** Create the worktree with superpowers:using-git-worktrees, from branch
  `feat/design-lock-prose-binding`, under `.claude/worktrees/design-lock`. Every later path in
  this plan is relative to the worktree root.
- [ ] **Step 2:** Record the baseline.

```bash
python3 -m pytest -q tests 2>&1 | tail -3 > /tmp/dl_baseline_pytest.txt
./scripts/check_fork.sh > /tmp/dl_baseline_fork.txt 2>&1; grep -E '^FAIL' /tmp/dl_baseline_fork.txt
```

Expected: the five FAIL labels listed in Global Constraints. Note the pytest pass count.

---

### Task 1: `design_block.py` — extract, normalise and hash the design block

**Files:**
- Create: `scripts/design_block.py`
- Modify: `scripts/SHIPPED` (add `design_block.py`)
- Test: `tests/test_design_block.py`

**Interfaces:**
- Produces:
  - `front_matter_lines(text: str) -> Optional[List[Tuple[int, str]]]`: (1-based line number,
    line) for each line between the opening `---` and the closing `---`/`...`.
  - `design_block(text: str) -> Optional[str]`: raw block text starting at `design:`.
  - `design_span(text: str) -> Optional[Tuple[int, int]]`: first and last file line of the
    block, inclusive.
  - `design_hash(text: str) -> Optional[str]`: sha256 hex of the normalised block, or None when
    there is no block.
  - `has_check(text: str, name: str) -> bool`: True when `design.checks.<name>` is present.
  - `LOCK_REL`, `AMEND_REL` (Paths).
  - `read_lock(root: Path) -> Optional[dict]`, `write_lock(root: Path, lock: dict) -> None`.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/test_design_block.py
import pathlib, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import design_block as db

BASE = """---
title: "T"
design:
  alpha: 0.10   # field standard
  verdicts: {sig: "significant", nonsig: "not significant"}
  hypotheses:
    H1: {estimand: "ATT", outcome: y, spec: m_h1, direction: negative}
  checks:
    power: {mde: 0.02, target_effect: 0.03, chunk: chk-power}
    size: {rejection_at_alpha: 0.10, reps: 500, chunk: chk-size}
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
        self.assertEqual(db.design_span(BASE), (3, 10))
    def test_no_front_matter_or_block(self):
        self.assertIsNone(db.design_block("Body only\n"))
        self.assertIsNone(db.design_hash("---\ntitle: x\n---\n"))
    def test_hash_ignores_comments_ws_crlf(self):
        h = db.design_hash(BASE)
        noisy = BASE.replace("# field standard", "").replace("\n", "\r\n").replace("alpha: 0.10", "alpha: 0.10   ")
        noisy = noisy.replace("  hypotheses:", "\n  # note\n  hypotheses:")
        self.assertEqual(db.design_hash(noisy), h)
    def test_hash_changes_on_value(self):
        self.assertNotEqual(db.design_hash(BASE.replace("0.10   #", "0.05   #")), db.design_hash(BASE))
    def test_edit_outside_block_keeps_hash(self):
        self.assertEqual(db.design_hash(BASE.replace('title: "T"', 'title: "U"')), db.design_hash(BASE))
    def test_has_check(self):
        self.assertTrue(db.has_check(BASE, "power")); self.assertTrue(db.has_check(BASE, "size"))
        self.assertFalse(db.has_check(BASE.replace("    size:", "    sizz:"), "size"))
    def test_lock_roundtrip(self):
        r = pathlib.Path(tempfile.mkdtemp())
        self.assertIsNone(db.read_lock(r))
        db.write_lock(r, {"status": "signed", "hash": "abc"})
        self.assertEqual(db.read_lock(r)["hash"], "abc")

if __name__ == "__main__": unittest.main()
```

- [ ] **Step 2:** Run `python3 -m pytest -q tests/test_design_block.py`. Expected: FAIL with
  `ModuleNotFoundError: design_block`.
- [ ] **Step 3: Implement.**

```python
#!/usr/bin/env python3
"""design_block.py — the manuscript's `design:` front-matter block (spec §4).

The design lock hashes the block's NORMALISED TEXT, not a parse: stdlib has no YAML parser, and
text is what an edit changes. Normalising drops comments, blank lines, trailing whitespace and
CR, so cosmetic edits keep the hash and any value edit changes it.
"""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import List, Optional, Tuple

LOCK_REL = Path("quality_reports") / "design_lock.json"
AMEND_REL = Path("quality_reports") / "design_amendments.md"
_TOP = re.compile(r"^design:\s*(#.*)?$")

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

def _normalise(block: str) -> str:
    keep = []
    for ln in block.split("\n"):
        ln = re.sub(r"\s+#.*$", "", ln.replace("\t", "  ")).rstrip()
        if ln.strip():
            keep.append(ln)
    return "\n".join(keep)

def design_hash(text: str) -> Optional[str]:
    b = design_block(text)
    return None if b is None else hashlib.sha256(_normalise(b).encode()).hexdigest()

def has_check(text: str, name: str) -> bool:
    b = design_block(text) or ""
    in_checks = False
    for ln in _normalise(b).split("\n"):
        if re.match(r"^\s{2,}checks:\s*$", ln): in_checks = True; continue
        if in_checks and re.match(rf"^\s{{4,}}{re.escape(name)}:", ln): return True
        if in_checks and re.match(r"^\s{2}\S", ln): in_checks = False
    return False

def read_lock(root: Path) -> Optional[dict]:
    p = root / LOCK_REL
    return json.loads(p.read_text()) if p.exists() else None

def write_lock(root: Path, lock: dict) -> None:
    p = root / LOCK_REL; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(lock, indent=2) + "\n")
```

- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_design_block.py`. Expected: 8 passed. If
  `test_span` fails, check the arithmetic: the block runs from file line 3 (`design:`) to line 10
  (the `size:` line). Fix the code, not the test.
- [ ] **Step 5: Commit.**

```bash
echo design_block.py >> scripts/SHIPPED
git add scripts/design_block.py scripts/SHIPPED tests/test_design_block.py
git commit -m "design_block.py: extract, normalise and hash the manuscript design block

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `pipeline.py design status|sign|unlock` and the `design-lock` predicate

**Files:**
- Modify: `scripts/pipeline.py` (new `design` subcommand; new predicate in `evaluate`)
- Modify: `scripts/registry_lib.py:17` (add `"design-lock"` to the predicate-type set)
- Modify: `rules/registry.yaml` (add `- type: design-lock` to the `requires` of `coder` and
  `writer`)
- Modify: `rules/lifecycle.md` (predicate table: add a `design-lock` row and the missing
  `no-source` row)
- Test: `tests/test_design_lock.py`

**Interfaces:**
- Consumes: Task 1 (`design_hash`, `design_block`, `has_check`, `read_lock`, `write_lock`,
  `AMEND_REL`).
- Produces:
  - `design_state(root: Path, ms: Path) -> Tuple[str, str]`. The status is one of
    `NOT-RETROFITTED`, `UNSIGNED`, `SIGNED`, `CHANGED`, `UNLOCKED`; the string is detail.
  - CLI: `pipeline.py design status` exits 0 only for `SIGNED` or `NOT-RETROFITTED`.
  - CLI: `pipeline.py design sign --signer NAME`.
  - CLI: `pipeline.py design unlock --reason TEXT --results-seen yes|no`.
  - Predicate `{type: design-lock}`: passes on `SIGNED` or `NOT-RETROFITTED`.
  - Lock JSON: `{status, hash, block, signed_at, signer, amendments: int}`.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/test_design_lock.py
import json, pathlib, shutil, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
PIPE = ROOT / "scripts" / "pipeline.py"
sys.path.insert(0, str(ROOT / "tests")); from test_design_block import BASE

def run(*a, root):
    p = subprocess.run([sys.executable, str(PIPE), "--root", str(root), *a], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

class DesignCase(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
        (self.t / "CLAUDE.md").write_text("manuscript: m.qmd\n")
        (self.t / "rules").mkdir(); shutil.copy(ROOT / "rules" / "registry.yaml", self.t / "rules" / "registry.yaml")
        self.ms = self.t / "m.qmd"; self.ms.write_text(BASE + "\n```{r}\n#| label: chk-power\n1\n```\n\n```{r}\n#| label: chk-size\n1\n```\n")
    def tearDown(self): shutil.rmtree(self.t)

    def test_not_retrofitted_passes(self):
        self.ms.write_text("---\ntitle: x\n---\nbody\n")
        rc, out = run("design", "status", root=self.t); self.assertEqual(rc, 0); self.assertIn("NOT-RETROFITTED", out)
    def test_unsigned_fails(self):
        rc, out = run("design", "status", root=self.t); self.assertEqual(rc, 1); self.assertIn("UNSIGNED", out)
    def test_sign_then_signed(self):
        rc, out = run("design", "sign", "--signer", "author", root=self.t); self.assertEqual(rc, 0, out)
        rc, out = run("design", "status", root=self.t); self.assertEqual(rc, 0); self.assertIn("SIGNED", out)
    def test_sign_requires_checks_and_chunks(self):
        self.ms.write_text(BASE.replace("    size:", "    sizz:"))
        rc, out = run("design", "sign", "--signer", "a", root=self.t); self.assertEqual(rc, 1); self.assertIn("size", out)
    def test_changed_after_sign_fails(self):
        run("design", "sign", "--signer", "a", root=self.t)
        self.ms.write_text(self.ms.read_text().replace("alpha: 0.10", "alpha: 0.05"))
        rc, out = run("design", "status", root=self.t); self.assertEqual(rc, 1); self.assertIn("CHANGED", out)
    def test_unlock_amend_resign_logs(self):
        run("design", "sign", "--signer", "a", root=self.t)
        rc, out = run("design", "unlock", "--reason", "fix alpha", "--results-seen", "yes", root=self.t); self.assertEqual(rc, 0, out)
        self.assertIn("UNLOCKED", run("design", "status", root=self.t)[1])
        self.ms.write_text(self.ms.read_text().replace("alpha: 0.10", "alpha: 0.05"))
        rc, out = run("design", "sign", "--signer", "a", root=self.t); self.assertEqual(rc, 0, out)
        log = (self.t / "quality_reports" / "design_amendments.md").read_text()
        self.assertIn("fix alpha", log); self.assertIn("results seen: yes", log)
        self.assertIn("-  alpha: 0.10", log); self.assertIn("+  alpha: 0.05", log)
    def test_unlock_requires_signed(self):
        rc, out = run("design", "unlock", "--reason", "x", "--results-seen", "no", root=self.t); self.assertEqual(rc, 1)
    def test_pre_coder_blocks_unsigned(self):
        rc, out = run("pre", "coder", root=self.t); self.assertIn("design-lock", out); self.assertEqual(rc, 1)

if __name__ == "__main__": unittest.main()
```

- [ ] **Step 2:** Run `python3 -m pytest -q tests/test_design_lock.py`. Expected: FAIL
  (`invalid choice: 'design'`).
- [ ] **Step 3: Implement.** Add to `scripts/pipeline.py`, after `critic_inputs`:

```python
import design_block as dsb, difflib

def design_state(root: Path, ms: Path) -> Tuple[str, str]:
    text = ms.read_text(); h = dsb.design_hash(text); lock = dsb.read_lock(root)
    if lock is None:
        return ("NOT-RETROFITTED", "no design: block and no lock") if h is None else ("UNSIGNED", "design: block present, never signed — the author runs `pipeline.py design sign`")
    if h is None:
        return "CHANGED", "design_lock.json exists but the manuscript has no design: block"
    if lock.get("status") == "unlocked":
        return "UNLOCKED", f"amendment open since {lock.get('unlocked_at')}: {lock.get('reason')}"
    if h != lock.get("hash"):
        return "CHANGED", "design: block differs from the signed lock — the author runs `pipeline.py design unlock`, then `design sign`"
    return "SIGNED", f"signed {lock.get('signed_at')} by {lock.get('signer')}"

def design_cmd(root: Path, a) -> int:
    ms = declared_manuscript(root); text = ms.read_text(); st, why = design_state(root, ms)
    if a.op == "status":
        print(f"design: {st} — {why}"); return 0 if st in ("SIGNED", "NOT-RETROFITTED") else 1
    if a.op == "sign":
        if not a.signer: sys.exit("usage: design sign --signer NAME")
        if dsb.design_block(text) is None: print("design sign: no design: block in the manuscript front matter"); return 1
        miss = [c for c in ("power", "size") if not dsb.has_check(text, c)]
        miss += [f"chunk chk-{c}" for c in ("power", "size") if f"chk-{c}" not in chunk_labels(ms)]
        if miss: print("design sign: refused — missing " + ", ".join(miss)); return 1
        if st == "SIGNED": print("design sign: already signed and unchanged"); return 0
        if st == "CHANGED": print("design sign: refused — the block changed without `design unlock`; run unlock first"); return 1
        lock = dsb.read_lock(root) or {"amendments": 0}
        new_block = dsb.design_block(text)
        if st == "UNLOCKED":
            diff = "\n".join(difflib.unified_diff(lock["block"].split("\n"), new_block.split("\n"), "signed", "amended", lineterm="", n=0))
            p = root / dsb.AMEND_REL
            with p.open("a") as f:
                f.write(f"\n## Amendment {lock['amendments'] + 1} — {now()[:10]}\n\n- reason: {lock['reason']}\n"
                        f"- results seen: {lock['results_seen']}\n- re-signed by: {a.signer}\n\n```diff\n{diff}\n```\n")
            lock["amendments"] += 1
        lock.update({"status": "signed", "hash": dsb.design_hash(text), "block": new_block, "signed_at": now(), "signer": a.signer})
        for k in ("reason", "results_seen", "unlocked_at"): lock.pop(k, None)
        dsb.write_lock(root, lock); print(f"design: SIGNED ({lock['hash'][:12]})"); return 0
    if a.op == "unlock":
        if not a.reason or a.results_seen not in ("yes", "no"): sys.exit("usage: design unlock --reason TEXT --results-seen yes|no")
        if st != "SIGNED": print(f"design unlock: refused — status is {st}"); return 1
        lock = dsb.read_lock(root); lock.update({"status": "unlocked", "reason": a.reason, "results_seen": a.results_seen, "unlocked_at": now()})
        p = root / dsb.AMEND_REL
        if not p.exists(): p.write_text("# Design amendments\n\nAppend-only. Written by `pipeline.py design sign` after `design unlock`.\n")
        dsb.write_lock(root, lock); print("design: UNLOCKED — edit the design: block, then the author runs `design sign`"); return 0
    return 2
```

  Wire it into `main()`:

```python
    ds = sub.add_parser("design"); ds.add_argument("op", choices=["status", "sign", "unlock"])
    ds.add_argument("--signer"); ds.add_argument("--reason"); ds.add_argument("--results-seen", dest="results_seen")
    ...
    if a.cmd == "design": return design_cmd(root, a)
```

  Add the predicate to `evaluate()` before `any_of`:

```python
    if t == "design-lock":
        st, why = design_state(root, ctx.ms)
        return st in ("SIGNED", "NOT-RETROFITTED"), f"design-lock: {st} — {why}"
```

  - In `scripts/registry_lib.py:17`, add `"design-lock"` to the set.
  - In `rules/registry.yaml`, append `      - type: design-lock` to the `requires:` list of
    `coder` and of `writer`, matching the indentation of the neighbouring entries.
  - In `rules/lifecycle.md`'s predicate table, add the rows `design-lock` (the design block is
    signed and unchanged, or the project is not retrofitted) and `no-source`.
- [ ] **Step 4:** Run
  `python3 -m pytest -q tests/test_design_lock.py tests/test_pipeline.py && python3 scripts/pipeline.py registry check`.
  Expected: all pass, `registry-complete` PASS. `test_pipeline` stays green because the fixture
  is NOT-RETROFITTED.
- [ ] **Step 5: Commit:** `git add -A scripts rules tests && git commit -m "pipeline.py design sign|unlock|status; design-lock predicate on pre coder/writer"`
  (with the Co-Authored-By trailer).

---

### Task 3: `design-guard` hook, and protect-files covering Bash

**Files:**
- Create: `hooks/design-guard.py`
- Modify: `hooks/protect-files.sh` (add `design_lock.json`, `design_amendments.md`,
  `findings_ledger.md`, `render_fingerprint.json`, `cold_render.json`; add a Bash branch)
- Modify: `scripts/wire_guard_hooks.py` (`WANTED` += `("PreToolUse", "Write|Edit|Bash", "design-guard.py")`)
- Modify: `seeds/settings.json` (the same entry in the existing `Write|Edit|Bash` group; the
  `Edit|Write` matcher on protect-files becomes `Edit|Write|Bash`)
- Modify: `hooks/README.md` (one row per hook change)
- Test: `tests/test_design_guard.py`

**Interfaces:**
- Consumes: Task 1 (`design_hash`, `read_lock`), plus the payload shape of the existing hooks
  (`tests/test_guard_hooks.py`).
- Produces: a hook that denies (a) an Edit/Write leaving the manuscript's design hash different
  from a `signed` lock, (b) any Bash command invoking `pipeline.py … design sign|unlock`, and
  (c) a Bash in-place write to the manuscript while the design is signed.

- [ ] **Step 1: Write the failing tests.** Reuse `ProjectCase` from `tests/test_guard_hooks.py`
  by import.

```python
# tests/test_design_guard.py
import json, pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests")); sys.path.insert(0, str(ROOT / "scripts"))
from test_guard_hooks import ProjectCase
from test_design_block import BASE
import design_block as db
HOOK = ROOT / "hooks" / "design-guard.py"

class TestDesignGuard(ProjectCase):
    def setUp(self):
        super().setUp(); self.ms.write_text(BASE)
    def sign(self):
        db.write_lock(self.proj, {"status": "signed", "hash": db.design_hash(BASE)})
    def edit(self, old, new):
        return self.run_hook(HOOK, {"hook_event_name": "PreToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": str(self.ms), "old_string": old, "new_string": new}})
    def bash(self, cmd):
        return self.run_hook(HOOK, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}})

    def test_unlocked_project_allows(self):
        self.assertFalse(self.denied(self.edit("alpha: 0.10", "alpha: 0.05")))
    def test_signed_blocks_design_edit(self):
        self.sign(); self.assertTrue(self.denied(self.edit("alpha: 0.10", "alpha: 0.05")))
    def test_signed_allows_title_and_body(self):
        self.sign()
        self.assertFalse(self.denied(self.edit('title: "T"', 'title: "U"')))
        self.assertFalse(self.denied(self.edit("Body text.", "New body.")))
    def test_signed_blocks_write_changing_block(self):
        self.sign()
        out = self.run_hook(HOOK, {"hook_event_name": "PreToolUse", "tool_name": "Write",
            "tool_input": {"file_path": str(self.ms), "content": BASE.replace("0.10", "0.20")}})
        self.assertTrue(self.denied(out))
    def test_unlocked_status_allows(self):
        db.write_lock(self.proj, {"status": "unlocked", "hash": db.design_hash(BASE)})
        self.assertFalse(self.denied(self.edit("alpha: 0.10", "alpha: 0.05")))
    def test_agent_cannot_sign_or_unlock(self):
        for c in ("python3 .claude/scripts/pipeline.py design sign --signer me",
                  "cd x && python3 .claude/scripts/pipeline.py --root . design unlock --reason r --results-seen no"):
            self.assertTrue(self.denied(self.bash(c)), c)
        self.assertFalse(self.denied(self.bash("python3 .claude/scripts/pipeline.py design status")))
    def test_bash_inplace_write_blocked_when_signed(self):
        self.sign()
        self.assertTrue(self.denied(self.bash("sed -i '' 's/0.10/0.05/' manuscript_p.qmd")))
        self.assertFalse(self.denied(self.bash("grep alpha manuscript_p.qmd")))

if __name__ == "__main__": unittest.main()
```

  Add to `tests/test_guard_hooks.py` a protect-files Bash test:
  `echo x > quality_reports/pipeline_state.json` is denied (exit 2), and `cat pipeline_state.json`
  is allowed.
- [ ] **Step 2:** Run `python3 -m pytest -q tests/test_design_guard.py`. Expected: FAIL (no hook
  file).
- [ ] **Step 3: Implement** `hooks/design-guard.py`.

```python
#!/usr/bin/env python3
"""design-guard.py — PreToolUse (Write|Edit|Bash): the signed design block is the author's.

Spec §4. Once quality_reports/design_lock.json says `signed`, no agent edit may change the
manuscript's `design:` front-matter block; the author opens an amendment with
`pipeline.py design unlock` in their own terminal. Agents may never run `design sign|unlock` —
that is the whole lock: a session cannot approve its own change, and an unattended run has no
author at the terminal. Bash writes to the manuscript are refused while signed (use Edit, which
this hook can evaluate). Fails open on internal error.
"""
# Hook Event: PreToolUse
import json, os, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude" / "scripts"))
import design_block as db

SIGN_RE = re.compile(r"pipeline\.py\b[^\n;&|]*\bdesign\s+(sign|unlock)\b")
INPLACE_RE = r"(sed\s+-i|perl\s+-[a-z]*i|>>?|\btee\b|\bcp\b|\bmv\b)[^\n;&|]*{name}"

def deny(msg):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
        "permissionDecision": "deny", "permissionDecisionReason": "design-guard: " + msg}}))

def manuscript(root: Path):
    c = root / "CLAUDE.md"
    if not c.exists(): return None
    hits = re.findall(r"^manuscript:\s*(\S+\.qmd)\s*$", c.read_text(errors="ignore"), re.M)
    return (root / hits[0]).resolve() if len(hits) == 1 else None

def main() -> int:
    payload = json.load(sys.stdin); root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")).resolve()
    tool = payload.get("tool_name", ""); ti = payload.get("tool_input") or {}
    if tool == "Bash" and SIGN_RE.search(ti.get("command", "")):
        deny("`design sign` and `design unlock` are the author's commands — ask the author to run it in their own terminal."); return 0
    ms = manuscript(root)
    if ms is None or not ms.exists(): return 0
    lock = db.read_lock(root)
    if not lock or lock.get("status") != "signed": return 0
    if tool == "Bash":
        if re.search(INPLACE_RE.format(name=re.escape(ms.name)), ti.get("command", "")):
            deny(f"the design is signed; edit {ms.name} with the Edit tool so the design block can be checked.")
        return 0
    if tool not in ("Edit", "Write") or Path(ti.get("file_path", "")).resolve() != ms: return 0
    cur = ms.read_text()
    if tool == "Write": new = ti.get("content", "")
    else:
        old, rep = ti.get("old_string", ""), ti.get("new_string", "")
        new = cur.replace(old, rep) if ti.get("replace_all") else cur.replace(old, rep, 1)
    if db.design_hash(new) != lock.get("hash"):
        deny("this edit changes the signed design: block. The author runs `pipeline.py design unlock --reason ... --results-seen yes|no` first; the change is then logged and disclosed.")
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception: sys.exit(0)
```

  In `hooks/protect-files.sh`:
  - Add the five patterns to `PROTECTED_PATTERNS`.
  - Replace the "no file path → allow" exit with a Bash branch: for `TOOL=Bash`, read
    `.tool_input.command`, and for each pattern exit 2 when the command matches
    `(>|>>|tee|sed -i|cp|mv|rm)[^;&|]*<pattern-as-ERE>`. Convert each glob to an ERE: `*` → `.*`,
    `.` → `\.`.

  ```bash
  if [ "$TOOL" = "Bash" ]; then
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
    for PATTERN in "${PROTECTED_PATTERNS[@]}"; do
      ERE=$(printf '%s' "$PATTERN" | sed -e 's/\./\\./g' -e 's/\*/.*/g' -e 's/\[0-9\]/[0-9]/g')
      if echo "$CMD" | grep -Eq "(>|>>|\btee\b|sed -i|\bcp\b|\bmv\b|\brm\b)[^;&|]*${ERE}"; then
        echo "Protected file named in a shell write: $PATTERN" >&2; exit 2
      fi
    done
    exit 0
  fi
  ```

  - In `seeds/settings.json`, change the protect-files matcher to `Edit|Write|Bash` and add
    design-guard to the `Write|Edit|Bash` group.
  - Add design-guard to `WANTED` in `scripts/wire_guard_hooks.py`.
  - Add the README rows.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_design_guard.py tests/test_guard_hooks.py`.
  Expected: all pass.
- [ ] **Step 5: Commit:** `design-guard hook: signed design block is author-only; protect-files covers Bash`.

---

### Task 4: Claim helpers template (base R)

**Files:**
- Create: `templates/claims-helpers.R.txt`
- Create: `tests/r/test_claims_helpers.R`
- Create: `tests/test_claims_helpers.py` (pytest wrapper; skips when `Rscript` is missing)

**Interfaces:**
- Produces, as R functions in the manuscript's global env after the setup chunk:
  - `rc_design(qmd) -> list`;
  - `rc_num(x, digits = 2)`, `rc_pct(x, digits = 1)`;
  - `rc_sig(p, alpha = design$alpha)`;
  - `rc_dir(b, up, down)`;
  - `rc_cmp(a, b, more, less, same = NULL, tol = 0)`;
  - `rc_design_hash(d)`, `rc_data_hash(dirs = c("data/raw", "data/derived"))`;
  - `rc_fingerprint(d = design, extra = character(), path = "quality_reports/render_fingerprint.json")`.

  It expects an object named `design` in the global env (set by the setup chunk). The
  fingerprint JSON is `{"estimates_hash": str, "data_hash": str, "models": [str]}`, with no
  timestamp so that it changes only when the estimates do.

- [ ] **Step 1: Write the failing R test.**

```r
# tests/r/test_claims_helpers.R — run: Rscript tests/r/test_claims_helpers.R <repo-root>
args <- commandArgs(trailingOnly = TRUE); repo <- args[[1]]
eval(parse(file.path(repo, "templates", "claims-helpers.R.txt")))  # test harness only; manuscripts paste, never parse a file
qmd <- tempfile(fileext = ".qmd")
writeLines(c("---", "title: t", "design:", "  alpha: 0.10",
             '  verdicts: {sig: "significant", nonsig: "not significant"}',
             "  hypotheses:", "    H1: {spec: m_h1}", "---", "x"), qmd)
design <- rc_design(qmd)
expect_err <- function(expr, pat) { e <- tryCatch({expr; NULL}, error = function(e) conditionMessage(e)); if (is.null(e) || !grepl(pat, e)) stop("expected error /", pat, "/ got: ", e) }
stopifnot(rc_sig(0.05) == "significant", rc_sig(0.2) == "not significant", rc_sig(0.05, alpha = 0.01) == "not significant")
stopifnot(rc_dir(-1, "rose", "fell") == "fell", rc_dir(2, "rose", "fell") == "rose")
stopifnot(rc_cmp(3, 2, "larger", "smaller") == "larger", rc_cmp(2, 2.0001, "larger", "smaller", same = "the same", tol = 0.01) == "the same")
stopifnot(rc_num(1234.567) == "1,234.57", rc_pct(0.0312) == "3.1%")
expect_err(rc_num(NA_real_), "not one finite number"); expect_err(rc_sig(NaN), "not one finite number")
expect_err(rc_dir(0, "u", "d"), "exactly 0"); expect_err(rc_num(c(1, 2)), "not one finite number")
expect_err(rc_fingerprint(), "m_h1")                               # Review Focus 4: missing spec object
m_h1 <- lm(mpg ~ wt, data = mtcars)
fp <- tempfile(fileext = ".json"); rc_fingerprint(path = fp); a <- readLines(fp)
m_h1 <- lm(mpg ~ wt + hp, data = mtcars); rc_fingerprint(path = fp); b <- readLines(fp)
stopifnot(!identical(a, b), any(grepl('"models": \\["m_h1"\\]', a)))
if (requireNamespace("fixest", quietly = TRUE)) { m_h1 <- fixest::feols(mpg ~ wt | cyl, data = mtcars); rc_fingerprint(path = fp) }
d1 <- rc_design_hash(design); design$alpha <- 0.05; stopifnot(d1 != rc_design_hash(design))
expect_err(rc_design(tempfile()), "")
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
# Every result word in prose comes from these, so the word changes when the model does.
rc_design <- function(qmd) {
  d <- rmarkdown::yaml_front_matter(qmd)$design
  if (is.null(d)) stop("rc_design: no `design:` block in the front matter of ", qmd, call. = FALSE)
  if (!is.numeric(d$alpha) || length(d$alpha) != 1 || d$alpha <= 0 || d$alpha >= 1)
    stop("rc_design: design$alpha must be one number in (0, 1)", call. = FALSE)
  if (is.null(d$verdicts$sig) || is.null(d$verdicts$nonsig))
    stop("rc_design: design$verdicts needs `sig` and `nonsig`", call. = FALSE)
  d
}
.rc_ok <- function(x, what) {
  if (is.null(x) || length(x) != 1 || !is.numeric(x) || !is.finite(x))
    stop(sprintf("%s: value is %s, not one finite number - fix the model, do not type the word", what,
                 if (is.null(x)) "NULL" else paste(format(x), collapse = ", ")), call. = FALSE)
  invisible(x)
}
rc_num <- function(x, digits = 2) { .rc_ok(x, "rc_num"); formatC(x, format = "f", digits = digits, big.mark = ",") }
rc_pct <- function(x, digits = 1) { .rc_ok(x, "rc_pct"); paste0(formatC(100 * x, format = "f", digits = digits), "%") }
rc_sig <- function(p, alpha = design$alpha) {
  .rc_ok(p, "rc_sig"); if (p < alpha) design$verdicts$sig else design$verdicts$nonsig
}
rc_dir <- function(b, up, down) {
  .rc_ok(b, "rc_dir"); if (b == 0) stop("rc_dir: estimate is exactly 0; no direction word applies", call. = FALSE)
  if (b > 0) up else down
}
rc_cmp <- function(a, b, more, less, same = NULL, tol = 0) {
  .rc_ok(a, "rc_cmp"); .rc_ok(b, "rc_cmp")
  if (abs(a - b) <= tol) { if (is.null(same)) stop("rc_cmp: values equal within tol and no `same` word given", call. = FALSE); return(same) }
  if (a > b) more else less
}
.rc_md5 <- function(txt) { f <- tempfile(); on.exit(unlink(f)); writeLines(txt, f); unname(tools::md5sum(f)) }
rc_design_hash <- function(d) .rc_md5(paste(deparse(d, control = c("keepNA", "keepInteger", "niceNames", "showAttributes")), collapse = "\n"))
rc_data_hash <- function(dirs = c("data/raw", "data/derived")) {
  files <- sort(unlist(lapply(dirs[dir.exists(dirs)], list.files, recursive = TRUE, full.names = TRUE)))
  .rc_md5(paste(files, unname(tools::md5sum(files)), collapse = "\n"))
}
rc_fingerprint <- function(d = design, extra = character(), path = "quality_reports/render_fingerprint.json") {
  specs <- unique(c(vapply(d$hypotheses, function(h) as.character(h$spec), ""), extra))
  missing <- specs[!vapply(specs, exists, logical(1), envir = globalenv())]
  if (length(missing)) stop("rc_fingerprint: design spec object(s) not found: ", paste(missing, collapse = ", "), call. = FALSE)
  rows <- vapply(sort(specs), function(n) {
    m <- get(n, envir = globalenv()); co <- stats::coef(m); se <- sqrt(diag(as.matrix(stats::vcov(m))))
    paste(n, stats::nobs(m), paste(names(co), signif(co, 10), signif(se, 10), collapse = ";"))
  }, "")
  dir.create(dirname(path), showWarnings = FALSE, recursive = TRUE)
  writeLines(sprintf('{\n  "estimates_hash": "%s",\n  "data_hash": "%s",\n  "models": [%s]\n}',
                     .rc_md5(rows), rc_data_hash(), paste0('"', sort(specs), '"', collapse = ", ")), path)
  invisible(path)
}
# ---- end claims helpers ----
```

- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_claims_helpers.py`. Expected: 1 passed.
  If `deparse` control names error on this R version, fall back to `deparse(d)` and re-run.
- [ ] **Step 5: Commit:** `templates/claims-helpers.R.txt: rc_* claim helpers, cache keys, results fingerprint`.

---

### Task 5: Tighten `prose_number_check.py` — surface (abstract, math, notes, letter)

**Files:**
- Modify: `scripts/prose_number_check.py` (`load_manuscript`, `scan`, `R_CAP`, `main`, docstring)
- Test: `tests/test_prose_number_surface.py`

**Interfaces:**
- Produces:
  - YAML `title:`, `subtitle:` and `abstract:` values are scanned as prose.
  - Decimal literals inside `$…$`/`$$…$$` are scanned.
  - R `notes=`/`note=`/`general=` string literals are scanned as captions.
  - A `response-letter: <path>` line in CLAUDE.md (one or more) is scanned with the same rules,
    labelled `letter:`.

- [ ] **Step 1: Write the failing tests.** Follow the pattern of
  `tests/test_prose_number_holes.py`: write a temp project with `.claude/` and `CLAUDE.md`, a
  manuscript, and run the script. One test per surface; each asserts exit 1 and the literal in
  the output.
  - Abstract: `abstract: |\n  Prices fell 3.4 percent.` → `'3.4'`.
  - Title: `title: "A 12 percent drop"` → `'12'`.
  - Math: `$\beta = 0.634$` → `'0.634'`, while `$\beta_1$` and `$x_{it}$` pass.
  - Notes: in an R chunk, `modelsummary(m, notes = "Clustered by 51 states.")` → `'51'`.
  - Letter: CLAUDE.md `response-letter: letter.md` with `We now find 0.21.` → `letter: … '0.21'`.
  - Control: the clean fixture manuscript still passes.
- [ ] **Step 2:** Run `python3 -m pytest -q tests/test_prose_number_surface.py`. Expected: the
  surface tests FAIL, the control passes.
- [ ] **Step 3: Implement.**
  - **YAML.** In `load_manuscript`, while `in_yaml`, match
    `^(title|subtitle|abstract):[ \t]*(.*)$`. If the value is `|` or `>` (optionally `|-`/`>-`),
    set `yaml_block = True` and append each following line that starts with whitespace as
    `(i, line)` to `prose`, until a line that doesn't. Otherwise append `(i, value.strip("\"'"))`
    to `prose`. No other YAML key is scanned; `design:` is data, not prose.
  - **Math.** In `scan()`, before `MATH.sub`, add:
    ```python
    for mm in MATH.finditer(INLINE.sub(" ", text)):
        for d in re.finditer(r"(?<![\w_^{])(\d+\.\d+)", mm.group(0)):
            hits.setdefault(d.group(1), []).append((lineno, label + "math: " + mm.group(0)[:110]))
    ```
  - **Notes.** Change `R_CAP` to
    `r"""\b(?:caption|title|notes?|general)\s*=\s*(["'])(.*?)(?<!\\)\1"""`, and update the
    docstring's "Known limits" (notes are now read).
  - **Letter.** In `main`, after scanning the manuscript, loop over
    `declared(root, "response-letter")`. For each `path` relative to root that exists,
    `load_manuscript(path)` and scan with label `"letter: "`. Fail with exit 2 when a declared
    letter is missing.
- [ ] **Step 4:** Run
  `python3 -m pytest -q tests/test_prose_number_surface.py tests/test_prose_number_check.py tests/test_prose_number_holes.py`.
  Expected: all pass. If an existing test asserted that `notes =` is NOT read, update that
  assertion: the spec now requires it.
- [ ] **Step 5: Commit:** `prose_number_check: scan title/abstract, math decimals, table notes, response letter`.

---

### Task 6: Tighten `prose_number_check.py` — words (lexicon, ceiling 0, thresholds, jargon, context allowlist)

**Files:**
- Modify: `scripts/prose_number_check.py`
- Create: `references/pipeline-jargon.txt`
- Test: `tests/test_prose_number_words.py`

**Interfaces:**
- Produces:
  - `_VERDICT` extended.
  - The verdict ceiling defaults to 0 (an override is still allowed through
    `prose-verdict-ceiling:`).
  - A `WARN literal threshold` line for an inline `if` comparing against a numeric literal.
  - A `PIPELINE JARGON` failure (not allowlistable), extended by `prose-jargon:` in CLAUDE.md.
  - An optional allowlist `context` column: when it is non-empty, the literal is explained only
    at occurrences whose context contains it.

- [ ] **Step 1: Write the failing tests** (same harness as Task 5):
  - `Prices rose by \`r rc_num(b)\`.` → exit 1, `rose` listed. The same sentence with
    `\`r rc_dir(b, "rose", "fell")\`` passes.
  - `larger`, `doubled` and `every specification` beside a live value → exit 1.
  - `prose-verdict-ceiling: 5` with 1 hit → exit 0 (the override still works).
  - `\`r if (p < .1) "significant" else "not"\`` → output contains `WARN literal threshold`,
    exit 0. `\`r if (p < design$alpha) …\`` → no warning.
  - `the governing p` in prose → exit 1, `PIPELINE JARGON`. The CLAUDE.md line
    `prose-jargon: foo-band` makes `foo-band` fail.
  - An allowlist row `literal,reason,context` = `2024,settlement year,in 2024`: `in 2024` passes;
    `0.2024 points` still fails.
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - Extend `_VERDICT` with:
    `|increase[sd]?|decrease[sd]?|declin(?:e|es|ed|ing)|larger|smaller|higher|lower|doubled|halved|tripled|exceed(?:s|ed)?|every specification|all specifications|robust(?:ly)?|"`.
    Keep the multi-word entries last.
  - Default ceiling: after the declaration parse, `if ceiling is None: ceiling = 0`. Rewrite the
    `mode` text as `f"ceiling {ceiling}" + (" (default)" if not ceilings else "")`. Update the
    VERDICT WORDS docstring paragraph: default enforced at 0, generate the word with
    `rc_sig`/`rc_dir`/`rc_cmp`.
  - Threshold warning:
    `THRESH = re.compile(r"`(?:r|\{r\})\s[^`]*\bif\s*\([^)`]*[<>]=?\s*-?(?:\d+\.?\d*|\.\d+)\s*\)")`.
    Collect matches over the prose lines and print `WARN literal threshold at line N: …`. Don't
    fail.
  - Jargon: load the patterns from `Path(__file__).resolve().parent.parent / "references" / "pipeline-jargon.txt"`
    (skip `#` and blank lines), plus `tokens(" ".join(declared(root, "prose-jargon")))`. Match
    case-insensitively on `INLINE.sub(" ", line)` for prose and caption lines. Any hit fails, and
    it can't be allowlisted.
  - Context allowlist: build `allow_ctx[key] = context or None`. Compute `unexplained` per
    occurrence: an occurrence is explained when `key in allow` and
    (`allow_ctx[key] is None` or `allow_ctx[key] in ctx`).
  - `references/pipeline-jargon.txt`:
    ```
    # Pipeline-internal vocabulary that must never reach a manuscript (spec §5). One regex per line.
    governing p
    wording band
    rival reading
    verdict class(es)?
    \bINV-\d+\b
    \b[A-Z]{1,3}\d{1,3}-\d+\b
    ruling [A-Z]?\d+
    pre-registration theatre
    finding ledger
    ```
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_prose_number_words.py tests/test_prose_number_check.py tests/test_prose_number_holes.py tests/test_eval_checkers.py`.
  Expected: all pass. Any test that relied on the advisory default gets an explicit
  `prose-verdict-ceiling: 999` in its temp CLAUDE.md, and is not deleted. Then run
  `python3 scripts/prose_number_check.py tests/fixture-project/manuscript_fixture.qmd`: exit 0.
  If it fails, fix the fixture prose in Task 13, not here; record it.
- [ ] **Step 5: Commit:** `prose_number_check: verdict ceiling 0 by default, wider lexicon, jargon, threshold warning, context allowlist`.

---

### Task 7: Results fingerprint on scores, and staleness

**Files:**
- Modify: `scripts/pipeline.py` (`record-score`, `evaluate` `score`/`score-if-scored`/`critic-ran`, `score --gate`, `next_report`)
- Test: `tests/test_fingerprint_staleness.py`

**Interfaces:**
- Consumes: Task 1 `design_hash`, the Task 4 fingerprint JSON.
- Produces:
  - `FINGERPRINT_REL = quality_reports/render_fingerprint.json`.
  - `current_fingerprint(root, ms) -> Dict[str, Optional[str]]` with keys
    `{"estimates", "design"}`.
  - `STALE_ON_CHANGE = {"strategy", "manuscript", "referees"}`.
  - `stale_reason(root, ms, comp, entry) -> Optional[str]`.
  - Each score entry and receipt gains `fingerprint: {estimates, design}` and
    `head: <git sha or None>`.

- [ ] **Step 1: Write the failing tests.** Use `FixtureCase` from `tests/test_pipeline.py`.
  1. Without a fingerprint file or lock, record a manuscript score; `score --gate commit` is
     unaffected (not retrofitted).
  2. Write `render_fingerprint.json` (`estimates_hash: "A"`), record a manuscript score, then
     rewrite it with `"B"`. Now `score --gate commit` exits 1 with `STALE`, `next` shows
     `manuscript` as `OPEN … older fingerprint`, and `pre editor` fails.
  3. A code score is NOT made stale by an estimates change.
  4. With a design lock present but no fingerprint file, `score --gate commit` fails with
     `no render_fingerprint.json`.
  5. `record-score` writes `fingerprint` and `head` into the state entry and the receipt.
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3: Implement.**

```python
FINGERPRINT_REL = Path("quality_reports") / "render_fingerprint.json"
STALE_ON_CHANGE = {"strategy", "manuscript", "referees"}

def current_fingerprint(root: Path, ms: Path) -> Dict[str, Optional[str]]:
    p = root / FINGERPRINT_REL
    est = json.loads(p.read_text()).get("estimates_hash") if p.exists() else None
    return {"estimates": est, "design": dsb.design_hash(ms.read_text())}

def git_head(root: Path) -> Optional[str]:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None

def stale_reason(root: Path, ms: Path, comp: str, entry: Dict[str, Any]) -> Optional[str]:
    if comp not in STALE_ON_CHANGE or not entry: return None
    cur = current_fingerprint(root, ms); locked = dsb.read_lock(root) is not None
    if cur["estimates"] is None:
        return "no render_fingerprint.json — render the manuscript (rc_fingerprint)" if locked else None
    fp = entry.get("fingerprint") or {}
    if fp.get("estimates") != cur["estimates"] or fp.get("design") != cur["design"]:
        return f"STALE: {comp} score earned under an older fingerprint — re-run a whole-manuscript review"
    return None
```

  Then:
  - In `record-score`, set
    `entry["fingerprint"] = current_fingerprint(root, ms); entry["head"] = git_head(root)` and
    copy both into `receipt`. Move `ms = declared_manuscript(root)` above the entry construction.
  - In `evaluate` `score` and `score-if-scored`, after reading `val`: when the component's
    `stale_reason` is not None, return `(False, desc + " — " + reason)`.
  - In `critic-ran`, just before the final `return True`: when `stale_reason` is not None,
    return `(False, ran + " — " + reason)`.
  - In `score --gate`, for each component with a reason, print `gate {gate}: {reason}` and set
    `ok = False`.
  - In `next_report`, add a CLOSED-but-stale case: `info[c] = ("OPEN", reason)`.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_fingerprint_staleness.py tests/test_pipeline.py`.
  Expected: all pass.
- [ ] **Step 5: Commit:** `pipeline.py: scores carry the results fingerprint; stale strategy/manuscript/referee scores reopen their stage`.

---

### Task 8: Finding ledger

**Files:**
- Create: `scripts/findings_ledger.py`
- Create: `templates/findings-ledger.md`
- Modify: `scripts/pipeline.py` (`ledger` subcommand; `ledger-closed` auto-appended on `post`)
- Modify: `scripts/registry_lib.py:17` (add `"ledger-closed"`)
- Modify: `scripts/SHIPPED`
- Test: `tests/test_findings_ledger.py`

**Interfaces:**
- Produces:
  - `LEDGER_REL = quality_reports/findings_ledger.md`.
  - `rows(path) -> List[Dict[str, str]]`, with keys `id`, `created`, `creator`, `report`,
    `location`, `finding`, `status`.
  - `add(path, creator, report, location, finding, status="open") -> str`, returning `F-NNN`.
  - `set_status(path, fid, status) -> None`.
  - `blocking(path, creator) -> List[Dict]`: rows whose status is `open`, `proposal: pending` or
    `proposal: accepted`.
  - CLI:
    - `pipeline.py ledger add --creator C --report P --location L --finding T [--proposal]`;
    - `pipeline.py ledger close ID --sha SHA`;
    - `pipeline.py ledger decline ID --reason R`;
    - `pipeline.py ledger accept|reject ID`;
    - `pipeline.py ledger show [--open] [--creator C]`.

- [ ] **Step 1: Write the failing tests.**
  - `add` creates the file from the template and returns `F-001`, then `F-002`.
  - A `|` in the finding text is escaped as `\|` and round-trips.
  - `close` with a non-existent sha exits 1. Initialise a git repo in the temp dir, commit, and
    close with the real sha: exit 0, status `closed <sha7>`.
  - `decline` without `--reason` exits 2.
  - `post writer` fails while an `open` writer row exists, and passes after close.
  - A `proposal: pending` row blocks; after `reject` it no longer blocks; after `accept` it
    blocks until closed.
  - A row for `coder` doesn't block `post writer`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement.** A markdown table under a fixed header (`templates/findings-ledger.md`):

```markdown
# Finding ledger

Written only by `pipeline.py ledger` (spec §6). One row per critic or referee finding. Status:
`open` · `closed <sha>` · `declined: <author's reason>` · `proposal: pending|accepted|rejected`.
A finding labelled `[missed-earlier]` was raised in a later round on text an earlier round passed.

| id | created | creator | report | location | finding | status |
|---|---|---|---|---|---|---|
```

  - `findings_ledger.py` parses rows after the separator line by splitting on unescaped `|`
    (`re.split(r"(?<!\\)\|", line)[1:-1]`), and writes back with `\|` escaping.
  - `close` verifies `git cat-file -e <sha>^{commit}` in root.
  - Statuses are validated against
    `^(open|closed [0-9a-f]{7,40}|declined: .+|proposal: (pending|accepted|rejected))$`.
  - In `pipeline.py`, add the predicate:

```python
    if t == "ledger-closed":
        import findings_ledger as fl
        b = fl.blocking(root / fl.LEDGER_REL, ctx.agent or "")
        return not b, ("ledger-closed: no open findings" if not b else
                       f"ledger-closed: {len(b)} open for {ctx.agent}: " + ", ".join(r["id"] for r in b[:5]))
```

  - In `eval_preds`, for `kind == "post"`, append `{"type": "ledger-closed"}` for every agent
    with a critic, as is done for `critic-ran`.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_findings_ledger.py tests/test_pipeline.py`.
  Expected: all pass. The fixture has no ledger file, so `blocking` returns `[]`.
- [ ] **Step 5: Commit:** `finding ledger: pipeline.py ledger; post refuses with open findings or undecided proposals`.

---

### Task 9: No re-review after a pass; round-2+ critic context

**Files:**
- Modify: `scripts/pipeline.py` (`dispatch-ok` and `critic-context` subcommands)
- Test: `tests/test_dispatch_ok.py`

**Interfaces:**
- Consumes: Task 7 (`stale_reason`, the entry's `head` and `fingerprint`), Task 8 (`rows`), and
  the latest receipt's `manuscript_sha256`.
- Produces:
  - `pipeline.py dispatch-ok <critic> [--author-request]`. Exit 1 with `PASSED-UNCHANGED` when
    the critic's component scored ≥ 80, isn't stale, and the manuscript's sha256 equals the one
    in the latest receipt for that component. Exit 0 otherwise.
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
- [ ] **Step 5: Commit:** `pipeline.py dispatch-ok and critic-context: no re-review of passed unchanged work; rounds 2+ get ledger and diff`.

---

### Task 10: `check_render.py` — NA values and overfull boxes

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
  `re.finditer(r"Overfull \\hbox \((\d+(?:\.\d+)?)pt too wide\)", log)`, emitting kind
  `OVERFULL` for values > 1.0. Unverified: whether Quarto keeps `<stem>.log` after a successful
  render. `critic_inputs` passes the log only when the file exists and writes
  `latex log: absent` otherwise.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_check_render.py tests/test_pipeline.py`.
  Expected: all pass.
- [ ] **Step 5: Commit:** `check_render: NA/NaN/Inf on the page; overfull boxes from the LaTeX log`.

---

### Task 11: Pre-commit check and cold render

**Files:**
- Modify: `scripts/pipeline.py` (`render --cold` and `commit-check` subcommands)
- Create: `templates/git-hooks/pre-commit` (executable)
- Modify: `apply.sh` (set `core.hooksPath` after linking)
- Modify: `scripts/check_install.sh` (a `git-hooks-path` check)
- Test: `tests/test_commit_check.py`

**Interfaces:**
- Consumes: Tasks 2 and 7, `run_script`, `qmd_chunks.extract`.
- Produces:
  - `pipeline.py render --cold`: removes `<stem>_cache/`, runs `quarto render`, and on exit 0
    writes `quality_reports/cold_render.json` `{"manuscript_sha256": …, "at": …}`.
  - `pipeline.py commit-check`. Exit 0 when the manuscript isn't staged, or when no manuscript
    is declared. Exit 1 on: design status not SIGNED/NOT-RETROFITTED; prose check ≠ 0;
    structure check ≠ 0; unstaged manuscript changes; chunk code differing from HEAD while
    `cold_render.json`'s sha doesn't equal the manuscript's sha; or a lock with
    `amendments > 0` and no `{#sec-design-changes}` heading in the manuscript (the disclosure,
    spec §0.7; add a test for it in Step 1). Staleness only prints a `WARN`.

- [ ] **Step 1: Write the failing tests.** Use a git-initialised `FixtureCase` copy.
  - No CLAUDE.md → exit 0 (Review Focus 5).
  - Manuscript not staged → exit 0 quickly.
  - Stage a prose-only change → exit 0.
  - Stage a chunk-code change without a cold render → exit 1 `cold render`.
  - Write `cold_render.json` with the current sha → exit 0.
  - Unsigned design block → exit 1 `design`.
  - Typed literal in prose → exit 1 `prose`.
  - Stale score → exit 0 with `WARN`.
  - Mock `quarto` for `render --cold` by prepending a temp `PATH` dir holding a `quarto` script
    that exits 0; assert the cache dir was removed and `cold_render.json` written.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement.** For chunk-code changes, compare
  `qmd_chunks.extract(head_text.split("\n"))` with the same call on the working text. Get
  `head_text` from `git show HEAD:<ms_rel>`; when that fails (new file), treat the code as
  changed. Staged detection: `git diff --cached --name-only` contains `ms_rel`. Unstaged
  detection: `git diff --quiet -- ms_rel` returns 1.

  `templates/git-hooks/pre-commit`:

```sh
#!/bin/sh
# research-claude pre-commit: the manuscript gates run on every commit, whatever made it (spec §7).
top=$(git rev-parse --show-toplevel) || exit 0
[ -f "$top/.claude/scripts/pipeline.py" ] || exit 0
exec python3 "$top/.claude/scripts/pipeline.py" --root "$top" commit-check
```

  In `apply.sh`, after the templates are linked:

```bash
  if git -C "$PROJECT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    cur="$(git -C "$PROJECT_DIR" config --get core.hooksPath || true)"
    gd="$(git -C "$PROJECT_DIR" rev-parse --git-dir)"; case "$gd" in /*) ;; *) gd="$PROJECT_DIR/$gd";; esac
    own="$(ls "$gd/hooks" 2>/dev/null | grep -v '\.sample$' || true)"
    if [[ -n "$cur" && "$cur" != ".claude/templates/git-hooks" ]]; then echo "  WARN core.hooksPath is $cur — left alone; pre-commit gate NOT installed"
    elif [[ -z "$cur" && -n "$own" ]]; then echo "  WARN .git/hooks has its own hooks ($own) — pre-commit gate NOT installed; merge by hand"
    else git -C "$PROJECT_DIR" config core.hooksPath .claude/templates/git-hooks; echo "  pre-commit gate: core.hooksPath set"; fi
  fi
```

  In `check_install.sh`, beside `claude-md-size`, `ok git-hooks-path` when
  `git -C "$P" config --get core.hooksPath` equals `.claude/templates/git-hooks`; otherwise
  `bad git-hooks-path "pre-commit gate not installed — re-run apply.sh --link"`. Make the hook
  executable: `chmod +x templates/git-hooks/pre-commit && git add --chmod=+x templates/git-hooks/pre-commit`.
- [ ] **Step 4:** Run `python3 -m pytest -q tests/test_commit_check.py tests/test_check_install.py tests/test_apply_lock.py`.
  Expected: all pass. Update any `test_check_install` fixture that now lacks `core.hooksPath`
  by having its setup run `git config core.hooksPath .claude/templates/git-hooks`.
- [ ] **Step 5: Commit:** `pre-commit gate: pipeline.py commit-check, render --cold; apply.sh installs core.hooksPath`.

---

### Task 12: Shipped-tree and instruction checks; rule and skill text

**Files:**
- Create: `scripts/check_single_manuscript.py`; add it to `scripts/SHIPPED`; call it from
  `scripts/check_fork.sh` through `py check_single_manuscript.py` in the "seeds and shipped
  scripts" section
- Modify: `scripts/check_install.sh` (`claude-md-size` warn → bad; a new `claude-md-design-facts`
  check)
- Modify: `CLAUDE.md` (research-claude): import core rules
- Modify: `rules/core.md`, `rules/agents.md` §3 and §6, `rules/quarto-empirical.md` (a new
  section), `rules/content-invariants.md` (INV-11 extended to words)
- Modify: `skills/analyze/SKILL.md`, `skills/write/SKILL.md`, `skills/revise/SKILL.md`,
  `skills/review/SKILL.md`, `skills/pipeline/SKILL.md`
- Modify: `agents/writer-critic.md`, `agents/coder-critic.md`, `agents/strategist-critic.md`,
  `agents/editor.md`, `agents/domain-referee.md`, `agents/methods-referee.md`
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
- [ ] **Step 3: Implement the checks.**
  - In `check_install.sh`, change `warn claude-md-size` to `bad claude-md-size`, and add:

```bash
  local facts; facts="$(grep -nEi '(treat(ment|ed)|event)[^.]{0,40}(19|20)[0-9]{2}-[0-9]{2}(-[0-9]{2})?|^[[:space:]]*[-*]?[[:space:]]*\**H[0-9]+\**[[:space:]]*[:.)]' "$P/CLAUDE.md" 2>/dev/null || true)"
  [[ -z "$facts" ]] && ok claude-md-design-facts "none" || bad claude-md-design-facts "design facts belong in the manuscript's design: block: $(echo "$facts" | head -2 | tr '\n' ' ')"
```

- [ ] **Step 4: Edit the text.** Insert exactly the following.
  - Research-claude `CLAUDE.md`, directly under the title paragraph:

    ```
    **Pipeline core rules, loaded here too** — a session redesigning the pipeline carries the
    rules the papers run under: @rules/core.md
    ```

    Verify the import loads (`per docs:` Claude Code memory imports; test it, don't assume):
    `claude -p "Without using any tools, quote rule 1 under '## The manuscript' from your loaded instructions."`
    run from the repo root, with no timeout. Expected: the "One manuscript" text. If it is not
    quoted, inline the 11 rules instead and record that the import did not work.
  - `rules/core.md`, a new `## The design` section after `## The manuscript`:

    ```
    12. **The design is signed before estimation.** The manuscript's `design:` front-matter block
        (hypotheses → model objects, treatment with a located source quote, sample, inference rule,
        α, verdict words, power and size checks) is signed by the author with `pipeline.py design
        sign` in their own terminal. A signed block changes only after the author runs `design
        unlock`; the amendment is logged and disclosed. Agents never run sign or unlock.
        `[hook: design-guard; script: design-lock predicate, commit-check]`
    13. **Every result word comes from the model:** `rc_sig`, `rc_dir`, `rc_cmp`, `rc_num`, `rc_pct`
        from the setup chunk (`.claude/templates/claims-helpers.R.txt`), or an inline `if` against
        `design$alpha`. No typed verdict, direction or comparison word beside a value.
        `[script: prose_number_check.py]`
    14. **A changed fingerprint reopens review;** findings live in `quality_reports/findings_ledger.md`
        and close by commit or the author's stated reason. A passed, unchanged target is not
        re-reviewed. `[script: pipeline.py]`
    15. **Unattended runs make no rulings.** A decision point is written to
        `quality_reports/questions_for_author.md` and that line of work stops. `[judgment]`
    ```

  - `rules/agents.md` §6: replace the paragraph "**The finding ledger.** …" with:
    "**The finding ledger** is `quality_reports/findings_ledger.md`, written only through
    `pipeline.py ledger`; `post <creator>` refuses while a row for that creator is open or a
    proposal is undecided. The whole-manuscript re-review is enforced by the fingerprint:
    `record-score` stores the results fingerprint and a strategy, manuscript or referee score
    earned under another one is STALE (`pipeline.py score`, `next`, `pre`, `post`)."
  - `rules/agents.md` §3: add a bullet after "Each round is a fresh foreground `Agent` dispatch":
    "Round 1 is a cold read. From round 2, the dispatching skill runs `pipeline.py critic-context
    <critic>` and names the file in the prompt: the critic verifies each ledger row's closure,
    flags regressions, reviews changed text and every summary sentence, and labels any other new
    finding `[missed-earlier]`. Before any dispatch the skill runs `pipeline.py dispatch-ok
    <critic>`; `PASSED-UNCHANGED` means no dispatch unless the author asked."
  - `rules/quarto-empirical.md`, a new section `## Design block and claim helpers` before the
    caching section. It covers:
    - the `design:` YAML example from spec §4;
    - the setup-chunk lines
      `design <- rc_design("<manuscript>.qmd")` and
      `knitr::opts_chunk$set(cache.extra = list(rc_design_hash(design), rc_data_hash()))`;
    - the final chunk `rc_fingerprint()` (label `fingerprint`, `cache: false`, `include: false`);
    - the `chk-power`/`chk-size` chunk contract: each must `stop()` when its check fails;
    - "`pipeline.py render --cold` before committing a model-chunk change".
  - `rules/content-invariants.md` INV-11: append "— and every significance, direction,
    comparison or universality word beside a value is helper output (rule 13 of core.md)."
  - Skills:
    - `/analyze` Step 0, `/write` (the first step of `[section]` mode), `/revise` Step 1 and
      `/review` before dispatch: replace "informational only" with "**blocking**: a FAIL stops
      the skill and is reported".
    - Each skill that dispatches a critic adds, before the dispatch: run `pipeline.py dispatch-ok
      <critic>`; from round 2 run `pipeline.py critic-context <critic>`; after saving each report,
      add one ledger row per finding with `pipeline.py ledger add`.
    - `/review --peer` and `/revise`: a referee's request to add an analysis or change the design
      is added with `--proposal`; nothing is built until `ledger accept`, and a design-touching
      proposal needs `design unlock` by the author.
    - `/pipeline` adds core rule 15 as a stop condition.
  - Agents:
    - `writer-critic`, `coder-critic`: a `## Rounds 2+` section matching the agents.md §3 bullet.
    - `writer-critic` also adds: "Judge claims against the rendered PDF named in the
      critic-inputs log, not the `.qmd` source."
    - `strategist-critic`: "Score the memo against the manuscript's `design:` block. Every
      treatment, date and institutional fact must carry a located quote from a source you read
      in this dispatch; a fact marked verified without one is a deduction, whatever the memo's
      internal logic."
    - `editor`, `domain-referee`, `methods-referee`: "A request for a new analysis or a design
      change is a PROPOSAL, labelled as such; the author decides."
- [ ] **Step 5:** Run `python3 -m pytest -q tests && ./scripts/check_fork.sh; grep -E '^FAIL' …`.
  Expected: pytest is green, and the FAIL labels are exactly the Task 0 baseline. Then commit:
  `rules, skills, agents: design lock, claim helpers, ledger and round-2 context; check_single_manuscript; CLAUDE.md caps fail`.

---

### Task 13: Fixture manuscript adopts the contract; render-level defect tests

**Files:**
- Modify: `tests/fixture-project/manuscript_fixture.qmd` (design block, helpers, `chk-power`,
  `chk-size`, fingerprint chunk, helper-generated words)
- Modify: `tests/fixture-project/quality_reports/` (add `design_lock.json` generated by
  `pipeline.py design sign` in a test setup — not committed, because the lock depends on the
  block)
- Create: `tests/test_design_lock_render.py`

**Interfaces:**
- Consumes: Tasks 1–11.

- [ ] **Step 1: Edit the fixture.**
  - Paste the helpers into the setup chunk.
  - Add the `design:` block. It names the fixture's main model object as H1's `spec`, sets
    `alpha: 0.05`, and has checks with chunk labels.
  - Add a `chk-power` chunk: a simulated MDE on the fixture panel that `stop()`s if MDE >
    target.
  - Add a `chk-size` chunk: 200 placebo permutations, `stop()` unless the rejection rate is in
    [α−0.03, α+0.03].
  - Add the cache key line.
  - Add a final `fingerprint` chunk.
  - Rewrite any result sentence to use `rc_*`.

  Run `quarto render tests/fixture-project/manuscript_fixture.qmd` in a temp copy: exit 0, and
  `render_fingerprint.json` written.
- [ ] **Step 2: Write the render tests** (they copy the fixture to a temp dir; skip when
  `quarto` is missing):
  - **NA:** set H1's model object to `NA` in a mutated copy → the render exits non-zero, with
    `not one finite number` in the output.
  - **Cache invalidation:** render, then multiply the outcome column of `data/raw/panel.csv` by
    2. `estimates_hash` and `data_hash` change on a warm-cache re-render.
  - **Design change invalidates the cache:** sign, unlock, and change `alpha`. The re-render's
    cache directory has new entries for the estimation chunk, because the `cache.extra` key
    changed.
  - **Re-estimation reopens review:** record a manuscript score, mutate the data, and re-render.
    `score --gate commit` reports STALE.
  - **End to end:** `commit-check` on the clean fixture, staged → exit 0.
- [ ] **Step 3:** Run `python3 -m pytest -q tests/test_design_lock_render.py tests/test_pipeline.py && tests/run_fixture.sh`.
  Expected: all pass. Fix the fixture, never the gate, when the fixture fails a gate.
- [ ] **Step 4: Commit:** `fixture: adopts design block, claim helpers and fingerprint; render-level defect tests`.

---

### Task 14: Release — review, re-link, live evals, merge

**Files:** `docs/SESSION_REPORT.md`, `docs/improvement-ledger.md` (L-008 → `landed <sha>`),
`CLAUDE.md` "Start here" pointer.

- [ ] **Step 1:** Run a whole-branch review (superpowers:requesting-code-review) and fix its
  findings.
- [ ] **Step 2:** Run `python3 -m pytest -q tests` (green) and `./scripts/check_fork.sh` (FAIL
  labels equal to the Task 0 baseline).
- [ ] **Step 3:** Merge to `main` locally: `git merge --no-ff feat/design-lock-prose-binding`.
  The linked papers see the change from this point.
- [ ] **Step 4:** For each paper project, run `./apply.sh --project-dir <p> --link` and
  `python3 scripts/wire_guard_hooks.py <p>/.claude/settings.json`. Then run
  `./scripts/check_install.sh --all`.
  - Expected: PASS, except `claude-md-size`/`claude-md-design-facts`/`git-hooks-path` FAILs in
    papers not yet retrofitted. List them; Task 15 clears them.
  - `--tip` projects need external imports approved first (README).
- [ ] **Step 5:** Run the live evals with no timeout (never set `EVAL_TIMEOUT`/`LIVE_TIMEOUT`):
  `tests/evals/analyze*.sh`, `write*.sh`, `revise*.sh` and `review*.sh` (whichever exist), then
  `tests/run_fixture.sh --live`. A red run is diagnosed after it finishes, never killed.
- [ ] **Step 6:** Update the `docs/SESSION_REPORT.md` entry, mark ledger L-008 landed, and
  repoint the CLAUDE.md "Start here" paragraph at this plan. Commit.

---

### Task 15: Retrofit each paper (author-gated; project repos)

Run once per paper. The rewritten papers go first; the order is the author's call. This happens
in the paper's own repo, with a project commit after each step. **Stop and wait for the author
at every `AUTHOR` step.**

- [ ] **Step 1:** Move the project CLAUDE.md design facts (treatment dates, hypothesis lists)
  into a draft `design:` block, and cut CLAUDE.md to ≤ 60 lines with the history in
  `docs/status_history.md`. Paste the helpers, the cache key and the fingerprint chunk. Write the
  `chk-power`/`chk-size` chunks for the paper's actual design.
- [ ] **Step 2:** Run `pipeline.py render --cold`, then report the power and size results to the
  author verbatim.
- [ ] **Step 3 — AUTHOR:** The author reviews the block. Any item that fails is resolved by the
  author before signing:
  - a size check outside tolerance;
  - a post-results design change not disclosed in the paper;
  - a design with no strategy memo or strategist review.

  The author then runs `python3 .claude/scripts/pipeline.py design sign --signer <name>` in
  their own terminal.
- [ ] **Step 4:** Alias the existing project helpers to `rc_*` inside the setup chunk. Run
  `prose_number_check.py` and save the failures as `quality_reports/plans/<date>_binding-fix-list.md`.
  Fix them, then render and commit.
- [ ] **Step 5:** Seed the ledger: one `pipeline.py ledger add` per still-open finding in the
  current critic reports, with the author confirming which findings are still open.
- [ ] **Step 6:** Run `pipeline.py critic-inputs` and dispatch one whole-manuscript writer-critic
  (round 1, cold), recording with `record-score`. Then run `check_install.sh` for the project:
  PASS.
