# gstack Feature Adoption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: complete (2026-09-25).** Merged to `main` as `ccea599` (commits `51cf860`, `3fa5b0b`,
`e8a5cd8`, `982d640`, `78ecfe9`); fleet re-linked the same day — see the 2026-09-25 "Pipeline-fix
residue cleanup" entry in `docs/SESSION_REPORT.md`. The checkboxes below were not ticked during
execution; they are not open work.

**Goal:** Port three features identified from `garrytan/gstack` (the software-engineering
toolkit `clo-author` — this pipeline's ancestor — is itself derived from) that have a real
gap here: a root-cause-before-retry debugging discipline, receipts binding a recorded score
to the exact content it was scored against, and a static token/context-cost auditor for the
shipped skill tree. Cross-model second opinion (`/codex`) is explicitly out of scope per the
user (no free Codex access confirmed).

**Architecture:** All three are additive — a new rule file plus cross-references, one new
`pipeline.py` code path reusing its existing `state record-score` choke point (every score
in the pipeline already flows through one function call, so this needs no changes to any of
the ~15 skill call sites), and one new standalone script exposed as a `/tools` subcommand.
Nothing here changes an existing agent's authority, the registry, or the three-strikes
mechanism — receipts and the debugging rule are deliberately orthogonal to it (see Task 1).

**Tech Stack:** Python 3.9 stdlib only (this repo's existing convention — `pipeline.py`,
`audit_graph.py` etc. take no third-party dependencies), `unittest` via `pytest`, Markdown
rule/agent files.

**Spec:** This plan **is** the spec — it was derived directly from reading
`rules/agents.md`, `rules/logging.md`, `hooks/README.md`, `agents/verifier.md`,
`agents/coder.md`, `agents/data-engineer.md`, `skills/analyze/SKILL.md`,
`skills/tools/SKILL.md`, `scripts/pipeline.py` (in full) and `scripts/audit_graph.py` in
this session, plus a web lookup of `garrytan/gstack`'s feature list. No separate design doc
exists; the file/line references throughout are the design.

## Global Constraints

- No third-party Python dependencies — stdlib only, matching every script in `scripts/`.
- `./scripts/check_fork.sh` must exit 0 before any commit touching `agents/`, `skills/`,
  `rules/`, or `hooks/` (repo `CLAUDE.md`) — no journal name, dataset name, project noun, or
  non-standard manuscript filename in any new or edited file under those directories.
- New files under `agents/`, `skills/`, `rules/`, `hooks/` require re-running
  `./scripts/check_install.sh --all` after a re-link, per repo `CLAUDE.md`.
- `python3 scripts/audit_graph.py` must report no new dangling path references — it is the
  existing gate that catches a cross-reference to a rule file that doesn't exist or a typo'd
  path, so it substitutes for a bespoke test verifying the doc cross-references in Task 1.
- Every new/edited Python file matches this repo's terse comment style: a comment explains
  *why* a decision was made or *why* a bug would otherwise occur, never *what* the next line
  does.
- Timestamps written by any new code must use `pipeline.py`'s `now()` format exactly (UTC,
  explicit `+00:00` offset, millisecond precision) — `scripts/pipeline.py:24-37` explains why
  (lexicographic order must equal chronological order across machines).

---

## Task 1: Systematic-debugging rule (root cause before retry)

**Files:**
- Create: `rules/systematic-debugging.md`
- Modify: `rules/agents.md` (append new `## 5.` section)
- Modify: `agents/coder.md` (insert new section before `## AI Use Log`)
- Modify: `agents/data-engineer.md` (insert new section before `## What You Do NOT Do`)
- Modify: `skills/analyze/SKILL.md` (add one bullet under `## Principles`)

**Interfaces:** None (documentation only — no code, no new script, no state file field).

- [ ] **Step 1: Create the rule file**

Create `rules/systematic-debugging.md`:

```markdown
# Systematic Debugging: Root Cause Before Retry

Governs any **mechanical failure** an agent hits mid-task — a `quarto render` error, a
failing chunk, a script that throws, a replication that does not match, a test that fails.
This is not `.claude/rules/agents.md` §3 (three-strikes): that governs *quality* rounds
between a creator and its paired critic, on work that already ran. This governs what
happens *before* a critic ever sees it, inside one creator's own turn, when the thing
does not run at all.

**Adopted from `garrytan/gstack`'s `/investigate` discipline** (max three failed fixes
before stopping), scoped down to a two-attempt cap here because a creator that reaches a
third mechanical failure already has two documented, falsified hypotheses to hand to its
critic or to the user — a third blind attempt adds a guess, not information.

## The loop

1. **Capture the exact error, verbatim.** Not a paraphrase, not "it didn't work" — the
   actual `quarto render` log line, the actual R/Python traceback, the actual diff between
   expected and actual output. A hypothesis built on a paraphrase is a hypothesis about the
   paraphrase, not the bug.
2. **State one falsifiable hypothesis for the root cause before changing anything.**
   "The chunk fails because `df` still has the old column name after the rename in the
   setup chunk" — not "let me try adding `na.rm = TRUE` and see."
3. **Make the smallest change that tests only that hypothesis.** One variable. Do not
   also reformat, also add error handling, also change something unrelated noticed along
   the way — a fix that touches three things and works leaves no way to know which of the
   three mattered.
4. **Re-run and compare against the captured error, not against "no error."** The same
   exact error persisting is refutation. A *different* error is not progress — it is a new
   symptom, and step 1 restarts from it, not from the goal.
5. **If refuted, discard the change.** Do not stack a second speculative fix on top of a
   first one that did not fix anything — an agent that has "tried three things at once" by
   the time something works cannot say which one it was, and the next person to touch this
   code inherits a change nobody can explain.
6. **After two falsified hypotheses on the same symptom, stop.** Do not attempt a third
   fix. Report: the exact error, both hypotheses tried and how each was falsified, and
   what to try next — as a question, not a silent third attempt. `coder` and
   `data-engineer` put this in their returned report instead of the score neither has the
   authority to give itself; a skill running standalone surfaces it to the user directly.

## Anti-patterns

- Changing code before reading the actual error text.
- Re-running the identical command unchanged, hoping for a different result.
- Suppressing the error (`try/except: pass`, `eval: false` on the failing chunk, a flag
  that skips the check) instead of understanding it — this closes the report, not the bug.
- A fix that "shouldn't matter" left in after the real fix is found — every change made
  during the loop that did not survive step 5 must be reverted, not left as harmless
  residue.

## Where this applies

`agents/coder.md`, `agents/data-engineer.md` (script and chunk failures);
`skills/analyze/SKILL.md` (the dispatching skill, when a dispatched agent's report names a
two-hypothesis stop). It does not apply to `agents/verifier.md` — the verifier only
reports FAIL, it never fixes anything (`.claude/rules/agents.md` §2, `verifier.md`: "The
tree is not yours to change") — and it does not apply to a critic's quality deductions,
which is `rules/agents.md` §3, a different axis entirely.
```

- [ ] **Step 2: Cross-reference from `rules/agents.md`**

Append to the end of `rules/agents.md` (after the existing `## 4. Dispatch ownership`
section and its trailing paragraph about Option gates):

```markdown

## 5. Mechanical failures are not quality rounds

A render error, a script traceback, or a chunk that will not run is not a strike (§3) —
it happens before a critic ever sees the work. `.claude/rules/systematic-debugging.md`
governs it: capture the exact error, one hypothesis at a time, stop and report after two
falsified hypotheses rather than guessing a third time.
```

- [ ] **Step 3: Cross-reference from `agents/coder.md`**

In `agents/coder.md`, insert immediately before the `## AI Use Log` heading:

```markdown
## When a Script or Render Fails

Follow `.claude/rules/systematic-debugging.md` — capture the exact error, one falsifiable
hypothesis at a time, stop and report after two falsified hypotheses rather than a third
blind fix.

```

(Use the Edit tool with `old_string` anchored on the existing `## AI Use Log\n\nAfter
completing your work, append one entry to \`ai_use_log.md\`` text so the insertion lands
directly above it.)

- [ ] **Step 4: Cross-reference from `agents/data-engineer.md`**

In `agents/data-engineer.md`, insert immediately before the `## What You Do NOT Do`
heading:

```markdown
## When a Script Fails

Follow `.claude/rules/systematic-debugging.md` — capture the exact error, one falsifiable
hypothesis at a time, stop and report after two falsified hypotheses rather than a third
blind fix.

```

(Anchor the Edit on the existing `## What You Do NOT Do\n\n- Do not run regressions or
estimate models` text.)

- [ ] **Step 5: Cross-reference from `skills/analyze/SKILL.md`**

In `skills/analyze/SKILL.md`, under `## Principles`, add a new bullet immediately after
the existing `- **Reproduce, don't guess.** If the user specifies a regression, run
exactly that.` line:

```markdown
- **Root cause before retry.** A chunk error or render failure follows
  `.claude/rules/systematic-debugging.md` — one hypothesis, smallest test, stop after two
  falsified attempts and report rather than guess a third time.
```

- [ ] **Step 6: Verify no dangling references and no fork violations**

```bash
python3 scripts/audit_graph.py
./scripts/check_fork.sh
```

Expected: both exit 0. `audit_graph.py` confirms every new `.claude/rules/
systematic-debugging.md` reference resolves; `check_fork.sh` confirms nothing
project-specific was introduced.

- [ ] **Step 7: Commit**

```bash
git add rules/systematic-debugging.md rules/agents.md agents/coder.md agents/data-engineer.md skills/analyze/SKILL.md
git commit -m "$(cat <<'EOF'
rules: add systematic-debugging (root cause before retry), adopted from gstack /investigate

Fills a real gap: no rule here formalized "stop guessing after N failed fixes" for
mechanical failures (render errors, script tracebacks) as distinct from the existing
three-strikes mechanism, which governs quality-score rounds between a creator and its
critic on work that already ran, not failures before a critic ever sees it.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Receipts (bind a recorded score to the exact content it scored)

**Files:**
- Modify: `scripts/pipeline.py:14` (import), `:20-22` (constants), after `:78`
  (`save_state`) (two new helpers), `:591-597` (`record-score` handler)
- Modify: `rules/logging.md` (new `## Receipts` section)
- Test: `tests/test_pipeline.py` (new `TestReceipts` class)

**Interfaces:**
- Consumes: `declared_manuscript(root) -> Path` (`scripts/pipeline.py:48`), `now() -> str`
  (`scripts/pipeline.py:24`), the existing `record-score` argparse args (`a.args`,
  `a.critic`, `a.report`, `a.scope`) already parsed at `scripts/pipeline.py:563-566`.
- Produces: `sha256_file(p: Path) -> str`, `append_receipt(root: Path, entry:
  Dict[str, Any]) -> None`, and `RECEIPTS_REL = Path("quality_reports") /
  "receipts.jsonl"` — for any later task that wants to read or extend the receipts log.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_pipeline.py` (after the existing `TestState` class, i.e. after its last
method around line 113):

```python
class TestReceipts(FixtureCase):
    """record-score must bind its verdict to the exact bytes it scored — a receipt line
    naming the manuscript's and report's sha256 at the moment of recording, so a later
    claim "verifier passed" can't silently apply to a since-edited file."""
    def test_record_score_writes_a_receipt(self):
        run("state", "init", root=self.t)
        rc, out = run("state", "record-score", "code", "85", "--critic", "coder-critic",
                       "--report", "r.md", root=self.t)
        self.assertEqual(rc, 0, out)
        receipts_path = self.t / "quality_reports" / "receipts.jsonl"
        self.assertTrue(receipts_path.exists())
        lines = receipts_path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        receipt = json.loads(lines[0])
        self.assertEqual(receipt["agent"], "coder-critic")
        self.assertEqual(receipt["component"], "code")
        self.assertEqual(receipt["score"], 85.0)
        self.assertEqual(receipt["report"], "r.md")
        self.assertEqual(receipt["manuscript"], "manuscript_fixture.qmd")
        import hashlib
        expected_ms_hash = hashlib.sha256((self.t / "manuscript_fixture.qmd").read_bytes()).hexdigest()
        expected_report_hash = hashlib.sha256((self.t / "r.md").read_bytes()).hexdigest()
        self.assertEqual(receipt["manuscript_sha256"], expected_ms_hash)
        self.assertEqual(receipt["report_sha256"], expected_report_hash)
        self.assertIn("at", receipt)

    def test_a_refused_record_score_writes_no_receipt(self):
        """The report-must-exist refusal (Phase 2.3) must not leave a receipt behind —
        a receipt for a score that was never recorded would be a lie."""
        run("state", "init", root=self.t)
        rc, _ = run("state", "record-score", "code", "85", "--critic", "coder-critic",
                     "--report", "nonexistent-report.md", root=self.t)
        self.assertEqual(rc, 1)
        self.assertFalse((self.t / "quality_reports" / "receipts.jsonl").exists())

    def test_second_record_score_appends_a_second_line(self):
        run("state", "init", root=self.t)
        run("state", "record-score", "code", "70", "--critic", "coder-critic", "--report", "r.md", root=self.t)
        run("state", "record-score", "code", "85", "--critic", "coder-critic", "--report", "r.md", root=self.t)
        lines = (self.t / "quality_reports" / "receipts.jsonl").read_text().strip().splitlines()
        self.assertEqual(len(lines), 2)

    def test_manuscript_content_changing_between_scores_produces_different_hashes(self):
        """The whole point of a receipt: if the manuscript changes after a PASS, the next
        receipt's hash differs, so the two PASSes are visibly not about the same content."""
        run("state", "init", root=self.t)
        run("state", "record-score", "code", "85", "--critic", "coder-critic", "--report", "r.md", root=self.t)
        ms = self.t / "manuscript_fixture.qmd"
        ms.write_text(ms.read_text() + "\n% edited\n")
        run("state", "record-score", "code", "90", "--critic", "coder-critic", "--report", "r.md", root=self.t)
        lines = (self.t / "quality_reports" / "receipts.jsonl").read_text().strip().splitlines()
        r1, r2 = json.loads(lines[0]), json.loads(lines[1])
        self.assertNotEqual(r1["manuscript_sha256"], r2["manuscript_sha256"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_pipeline.py::TestReceipts -v`
Expected: all four FAIL (`quality_reports/receipts.jsonl` never gets created — no
`AttributeError`/`ImportError`, just missing-file / KeyError assertions, since
`record-score` itself still succeeds).

- [ ] **Step 3: Add the import and constant**

In `scripts/pipeline.py`, modify line 14 from:

```python
import argparse, datetime as dt, fnmatch, glob, json, re, subprocess, sys
```

to:

```python
import argparse, datetime as dt, fnmatch, glob, hashlib, json, re, subprocess, sys
```

Modify line 20-21 from:

```python
STATE_REL = Path("quality_reports") / "pipeline_state.json"
LOG_REL = Path("quality_reports") / "agent_dispatch.jsonl"
```

to:

```python
STATE_REL = Path("quality_reports") / "pipeline_state.json"
LOG_REL = Path("quality_reports") / "agent_dispatch.jsonl"
RECEIPTS_REL = Path("quality_reports") / "receipts.jsonl"
```

- [ ] **Step 4: Add the two helpers**

In `scripts/pipeline.py`, insert immediately after `save_state` (after the line
`state_path(root).write_text(json.dumps(st, indent=2) + "\n")` at line 78, before
`def validate_state`):

```python

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def append_receipt(root: Path, entry: Dict[str, Any]) -> None:
    """One JSON line per recorded score, binding the verdict to the exact bytes it scored.

    COMMITTED, like pipeline_state.json (`.claude/rules/logging.md`: "replication
    provenance") — unlike agent_dispatch.jsonl, this is not session mechanics, it is the
    audit trail a later reader needs to know a recorded PASS was about the manuscript as it
    stood at record time, not as it stands now. Append-only: never rewritten, never pruned.
    """
    p = root / RECEIPTS_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(entry) + "\n")
```

- [ ] **Step 5: Call it from `record-score`**

In `scripts/pipeline.py`, in the `state` command handler, the `record-score` branch
currently reads (around line 591-597):

```python
            entry = {"score": score, "critic": a.critic, "report": a.report, "at": now()}
            if a.deductions is not None: entry["deductions"] = a.deductions
            if a.scope and a.scope.startswith("section:"):
                stt["sections"][a.scope.split(":", 1)[1]] = entry
            else:
                entry["rounds"] = stt["components"].get(comp, {}).get("rounds", 0) + 1; stt["components"][comp] = entry
            stt["overall"], _ = compute_overall(stt, reg); save_state(root, stt); print(f"recorded {comp}={score}"); return 0
```

Replace it with:

```python
            entry = {"score": score, "critic": a.critic, "report": a.report, "at": now()}
            if a.deductions is not None: entry["deductions"] = a.deductions
            if a.scope and a.scope.startswith("section:"):
                stt["sections"][a.scope.split(":", 1)[1]] = entry
            else:
                entry["rounds"] = stt["components"].get(comp, {}).get("rounds", 0) + 1; stt["components"][comp] = entry
            # Bind this verdict to the exact bytes it scored — both the manuscript and the
            # report file, at this instant, before the state write below (Task 2, receipts).
            ms = declared_manuscript(root)
            receipt = {"at": entry["at"], "agent": a.critic, "component": comp, "score": score,
                       "report": a.report, "manuscript": str(ms.relative_to(root)),
                       "manuscript_sha256": sha256_file(ms), "report_sha256": sha256_file(root / a.report)}
            if a.scope: receipt["scope"] = a.scope
            append_receipt(root, receipt)
            stt["overall"], _ = compute_overall(stt, reg); save_state(root, stt); print(f"recorded {comp}={score}"); return 0
```

The report-must-exist check at line 579-581 (`if not (root / a.report).is_file(): ...
return 1`) already runs before this point and returns early, so a refused `record-score`
never reaches the new code — satisfying `test_a_refused_record_score_writes_no_receipt`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_pipeline.py::TestReceipts -v`
Expected: all four PASS.

- [ ] **Step 7: Run the full pipeline test suite to check for regressions**

Run: `python3 -m pytest tests/test_pipeline.py -v`
Expected: PASS — no prior test asserts on the *absence* of `quality_reports/receipts.jsonl`
or on `record-score`'s side effects being limited to `pipeline_state.json`, so this is
additive.

- [ ] **Step 8: Document it in `rules/logging.md`**

In `rules/logging.md`, insert a new section after the existing `## Dispatch Log` section
(after its last line, `.claude/hooks/dispatch-log.py\` (SubagentStop) or by \`pipeline.py
log <agent>\` from a standalone skill. \`pipeline.py post\` reads it to prove the critic
ran. **Gitignored** — session mechanics.`) and before `## Learning Loop`:

```markdown

## Receipts

`quality_reports/receipts.jsonl` — one JSON line per `pipeline.py state record-score`
call, written by `record-score` itself (`scripts/pipeline.py`'s `append_receipt`), binding
the recorded verdict to a sha256 of the manuscript and the report file at the instant of
recording: `{at, agent, component, score, report, manuscript, manuscript_sha256,
report_sha256}` (`scope` added when `--scope section:NAME` was used). **Committed** —
provenance, like `pipeline_state.json`, not session mechanics like the dispatch log. Never
rewritten or pruned; a refused `record-score` (bad component, missing report, wrong
critic) writes nothing. Adopted from `garrytan/gstack`'s `gstack-review-log`, which binds
a review to the working-tree content it reviewed the same way.
```

- [ ] **Step 9: Verify fork/install gates**

```bash
./scripts/check_fork.sh
```

Expected: exit 0. (No file under `agents/`, `skills/`, `hooks/` changed in this task, so
`check_install.sh --all` is not required — only `rules/logging.md` and `scripts/
pipeline.py` changed, and `scripts/` is not a linked directory per
`rules/shared-pipeline.md`'s list... verify this: `scripts/` is **not** in the
`SHIP` list read in Task 1's grounding (`agents/skills/rules/references/hooks/templates`),
but `pipeline.py` is shared identically via the same-checkout-per-item link every project
uses for `.claude/scripts/pipeline.py` — run `check_install.sh --all` anyway if unsure;
it is cheap and idempotent.)

```bash
./scripts/check_install.sh --all
```

- [ ] **Step 10: Commit**

```bash
git add scripts/pipeline.py rules/logging.md tests/test_pipeline.py
git commit -m "$(cat <<'EOF'
pipeline: bind record-score to a content receipt, adopted from gstack gstack-review-log

record-score now appends one line to quality_reports/receipts.jsonl (committed
provenance, like pipeline_state.json) binding the recorded score to a sha256 of the
manuscript and report at the instant of recording. Every one of the ~15 skill call
sites already funnels through this one function, so no skill file changes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Token/context-cost auditor (`/tools context`)

**Post-review rename (2026-09-25):** the subcommand shipped as `/tools context` collided
with the subcommand name deleted 2026-09-24 (`tests/test_tools_contracts.py` pins that
`context` must not appear in the argument-hint). Renamed to `/tools context-bill`
everywhere below and in `skills/tools/SKILL.md`; `scripts/context_bill.py`'s filename and
CLI flags are unchanged. Steps below are left as originally written for the historical
record of what was planned and executed.

**Files:**
- Create: `scripts/context_bill.py`
- Test: `tests/test_context_bill.py`
- Modify: `skills/tools/SKILL.md` (frontmatter + new `### /tools context` subcommand)

**Interfaces:**
- Produces: a standalone CLI, `python3 scripts/context_bill.py [ROOT] [--top N] [--json
  OUT]`, printing a summary to stdout and, if `--json` is given, writing the full report.
  No other task in this plan depends on it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_context_bill.py`:

```python
import json, subprocess, sys, tempfile, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "context_bill.py"

def run(*args, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          cwd=cwd or ROOT)

class TestContextBillCli(unittest.TestCase):
    """Mirrors scripts/audit_graph.py's own CLI test shape (tests/test_audit_graph.py) —
    same footgun class: a script that dies on a missing positional arg before it ever
    audits anything."""

    def test_no_arguments_audits_this_checkout(self):
        r = run(cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("skills loaded into every session", r.stdout)

    def test_root_and_json_writes_the_full_report(self):
        with tempfile.TemporaryDirectory() as t:
            out = pathlib.Path(t) / "bill.json"
            r = run(str(ROOT), "--json", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            report = json.loads(out.read_text())
            self.assertIn("skills", report)
            self.assertIn("directories", report)
            self.assertIn("est_tokens", report["skills"][0])

    def test_json_only_written_when_asked(self):
        with tempfile.TemporaryDirectory() as t:
            r = run(str(ROOT), cwd=t)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(list(pathlib.Path(t).iterdir()), [])

    def test_top_flag_limits_the_largest_files_list(self):
        r = run(str(ROOT), "--top", "3")
        self.assertEqual(r.returncode, 0, r.stderr)
        # Count numbered lines under the "Largest files" heading.
        after = r.stdout.split("Largest files")[1]
        numbered = [ln for ln in after.splitlines() if ln.strip()[:2].rstrip(".").isdigit()]
        self.assertLessEqual(len(numbered), 3)

    def test_skills_are_sorted_by_est_tokens_descending(self):
        with tempfile.TemporaryDirectory() as t:
            out = pathlib.Path(t) / "bill.json"
            run(str(ROOT), "--json", str(out))
            report = json.loads(out.read_text())
            tokens = [s["est_tokens"] for s in report["skills"]]
            self.assertEqual(tokens, sorted(tokens, reverse=True))

    def test_help_is_usage_not_a_scan(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("usage", r.stdout.lower())
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_context_bill.py -v`
Expected: FAIL — `scripts/context_bill.py` does not exist yet (every test errors with
`FileNotFoundError` from `subprocess.run`, surfaced by pytest as a test failure).

- [ ] **Step 3: Write the script**

Create `scripts/context_bill.py`:

```python
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
import argparse, json, re, sys
from pathlib import Path
from typing import Any, Dict, List

SHIP = ["agents", "skills", "rules", "hooks", "references", "templates"]
SKIP_DIRS = {"__pycache__", ".git"}

def est_tokens(size_bytes: int) -> int:
    return size_bytes // 4

def iter_files(d: Path):
    for p in sorted(d.rglob("*")):
        if p.is_dir():
            continue
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
        description="Static token-cost audit of the shipped agents/skills/rules/hooks tree. "
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_context_bill.py -v`
Expected: all six PASS.

- [ ] **Step 5: Manual sanity check against the real tree**

```bash
python3 scripts/context_bill.py
```

Expected: prints directory totals for `agents/skills/rules/hooks/references/templates`,
an "Always-resident skill-description budget" list of every skill under `skills/` sorted
by its frontmatter description size, and a "Largest files" list. Skim it for anything
surprising (e.g. a skill whose description is disproportionately large relative to what it
does) — that is the actual payoff of this tool, not the script itself.

- [ ] **Step 6: Document `/tools context` in `skills/tools/SKILL.md`**

Modify the frontmatter (lines 1-6) from:

```yaml
---
name: tools
description: Utility commands — commit (with blocking quality/number/structure gates), render, validate-bib, lint, journal, learn. Replaces individual utility skills.
argument-hint: "[subcommand: commit | render | validate-bib | lint | journal | learn] [args] [--yes]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent
---
```

to:

```yaml
---
name: tools
description: Utility commands — commit (with blocking quality/number/structure gates), render, validate-bib, lint, journal, learn, context. Replaces individual utility skills.
argument-hint: "[subcommand: commit | render | validate-bib | lint | journal | learn | context] [args] [--yes]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent
---
```

Then insert a new subcommand section after `### /tools learn` (before the trailing `---`
and `## Principles` section):

```markdown

### `/tools context` — Token/Context-Cost Audit
Static audit of what the shipped `agents/`, `skills/`, `rules/`, `hooks/`, `references/`
and `templates/` tree costs in context: which skill's frontmatter description is loaded
into every session's skill listing before it is ever invoked, and which shipped file is
heaviest if something reads it in full. Adopted from `garrytan/gstack`'s
`gstack-context-bill`.

```bash
python3 .claude/scripts/context_bill.py
```

Add `--json <path>` for the full machine-readable report, `--top N` to change how many
entries the ranked lists show (default 15). Advisory only — nothing here gates a commit or
a pipeline stage; use it when a session feels heavier than it should, or before adding a
new skill, to see what it will cost every session from then on.
```

- [ ] **Step 7: Verify fork/install gates**

```bash
./scripts/check_fork.sh
```

Expected: exit 0. `skills/tools/` gained no new file (only its existing `SKILL.md` was
edited), so `check_install.sh --all` is not required by the repo's own rule for
*membership* changes — run it anyway as a cheap sanity check:

```bash
./scripts/check_install.sh --all
```

- [ ] **Step 8: Commit**

```bash
git add scripts/context_bill.py tests/test_context_bill.py skills/tools/SKILL.md
git commit -m "$(cat <<'EOF'
tools: add /tools context, a static token-cost auditor, adopted from gstack gstack-context-bill

Reports which skill's frontmatter description is loaded into every session before the
skill is ever invoked, and which shipped file is heaviest if read in full. Advisory —
nothing here gates a commit or a pipeline stage.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage:** all three user-requested features (root-cause debugging rule, receipts,
token auditor) have a task each. Cross-model second opinion is explicitly excluded per the
user's instruction. Every gstack feature identified as *not* worth porting in the prior
research turn (design-shotgun, browser QA, GBrain/Supabase, ship/land-and-deploy, CSO,
/office-hours, diagram/make-pdf) is correctly left out.

**Placeholder scan:** no TBD/TODO, no "add appropriate handling," every step shows the
actual diff or full file content, no step says "similar to Task N" without repeating the
code.

**Type/name consistency:** `RECEIPTS_REL`, `sha256_file`, `append_receipt` are defined once
in Task 2 Step 4 and used identically in Step 5 and the test in Step 1. `context_bill.py`'s
`scan()` return shape (`directories`, `skills`, `files`, each entry's `est_tokens`/`bytes`
keys) matches exactly between the script (Step 3) and the test assertions (Step 1).

**Corrected during planning:** an earlier draft of Task 1 planned to cross-reference the
debugging rule from `agents/verifier.md`. Re-reading `verifier.md` in full (its own text:
"The tree is not yours to change," and `rules/agents.md` §2: a critic/infrastructure
reviewer never edits) showed the verifier only ever reports FAIL and never attempts a fix,
so it cannot apply a retry discipline — the cross-reference was moved to the agents that
*do* respond to a verifier FAIL (`coder`, `data-engineer`, and the dispatching `/analyze`
skill) instead.
