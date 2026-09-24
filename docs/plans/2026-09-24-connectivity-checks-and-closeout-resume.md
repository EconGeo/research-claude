# Connectivity Checks and Closeout Resume — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the "verify the graph, not just the node" check class that
`docs/2026-09-23_pipeline-closeout-handoff.md` §4.2 identified as missing, then unblock and
hand off the one remaining piece of open work that class exists to have caught —
the stalled `docs/plans/2026-09-16-skill-defect-closeout.md`.

**Architecture:** Every existing gate in this repo (`scripts/check_fork.sh`,
`scripts/check_refs.py`, `scripts/check_install.sh`) verifies a single artifact's own
correctness. None asks "does anything reach this, and is what reaches it telling the truth
about it." This plan adds five narrow, single-purpose checks of that second kind, each wired
into the existing gate infrastructure at the narrowest point that already fits it, and each
proven with a fixture that fails before the fix and passes after — per this repo's own
standing rule (`docs/plans/2026-09-23_pipeline-repair.md`, "Why this plan exists"): *"Every
item ends in an executable check that FAILS before the work and PASSES after."*

**Tech Stack:** Python 3.9 stdlib only (matches `scripts/check_refs.py`'s own constraint),
Bash for `scripts/check_fork.sh` wiring, `unittest` for tests (matches `tests/test_check_refs.py`,
`tests/test_audit_graph.py`).

**Spec:** `docs/2026-09-23_pipeline-closeout-handoff.md` (§1 diagnosis, §4.2 the five missing
check types, §5 rules for whoever writes this plan) and
`docs/plans/2026-09-16-skill-defect-closeout.md` (the plan Task 6 resumes and patches).

## Global Constraints

- Every new `check_refs.py` criterion follows the existing shape exactly: a `crit_<name>(root)`
  function returning `report(name, hits)`'s int, registered in `CRITERIA`, and added to
  `check_fork.sh`'s `for c in ...` criterion loop — copy `crit_promote_vendor_warn` as the
  template, it is the newest and smallest existing example.
- A check that blocks a commit (FAIL, folds into `check_fork.sh`'s `fail=1`) must have **zero**
  false positives against the real tree, verified by running it before committing — this plan
  found and fixed one real false-positive bug (`scripts/audit_graph.py`'s vendored-agent path
  resolution) precisely by doing this before wiring anything in. A check whose false-positive
  rate is not yet known ships as a **WARN** (prints, never sets `fail=1`) — this is not a
  weaker version of the same check, it is the honest label for a check whose coverage has not
  been fully triaged yet (closeout handoff §5, rule 3).
- Every new or modified Python script under `scripts/` takes `--root` (never a bare positional),
  matching `check_refs.py`, `check_paths.py`, `pipeline.py` — the one exception is
  `scripts/audit_graph.py`, which already ships a positional `root` argument with real callers
  relying on nothing (it currently has zero real callers) but real *tests* relying on the
  positional form (`tests/test_audit_graph.py`); Task 3 below fixes its logic in place without
  changing that CLI, to avoid unrelated churn.
- Tests go in `tests/test_check_refs.py` (new criteria), `tests/test_audit_graph.py` (Task 3),
  and one new file `tests/test_check_plan_liveness.py` (Task 5) — matching the one-test-file-per-
  script convention already in `tests/`.
- After every task: `./scripts/check_fork.sh` must exit 0 and the full suite
  (`python3 -m pytest tests/ -q`) must pass, before commit.

---

## Task 1: `writes:` vs. tool-capability consistency check

**Files:**
- Modify: `scripts/check_refs.py` (add `crit_writes_tools`, register in `CRITERIA`)
- Modify: `scripts/check_fork.sh:93-96` (add `writes-tools` to the criterion loop)
- Test: `tests/test_check_refs.py` (new `TestWritesTools` class)

**Interfaces:**
- Consumes: `registry_lib.load_registry(root)["agents"]` (dict of agent name → entry with a
  `writes` list), `registry_lib.AGENT_DIRS` (`["agents", "ai-audit/agents"]`).
- Produces: `crit_writes_tools(root) -> int` (0/1), registered as `CRITERIA["writes-tools"]`.

This is the gate `docs/plans/2026-09-23_pipeline-repair.md`'s Phase 2.1 promised ("a
`writes`-vs-`tools` consistency check... failing when an agent is declared to write a path its
tools cannot produce") but never built — that item's "Done" note only reworded nine agent
files by hand. Verified 2026-09-24 by reading every agent's `tools:` line and every
`writes:`-declaring registry entry directly: every critic-role agent that lacks `Write`/`Edit`
already carries the exact disclaimer phrase Phase 2.1 introduced ("Do NOT write any files
yourself" / "Do NOT edit any file(s)"), so this check passes today — it exists to stop the
*next* agent from silently reintroducing the bug Phase 2.1 fixed by hand.

- [ ] **Step 1: Write the failing tests**

```python
class TestWritesTools(unittest.TestCase):
    """Phase 2.1 of docs/plans/2026-09-23_pipeline-repair.md fixed nine agents by hand (no
    Write/Edit tool + no 'do not write' disclaimer meant a declared writes: path was silently
    never produced). This is the check that should have existed to catch it, and to stop it
    recurring: an agent with writes: in registry.yaml must EITHER carry a write-capable tool
    OR carry the disclaimer establishing the dispatching skill writes on its behalf."""

    def _run(self, agent_md_body: str) -> int:
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "rules").mkdir()
            (root / "rules" / "registry.yaml").write_text((ROOT / "rules" / "registry.yaml").read_text())
            (root / "agents").mkdir()
            # coder-critic already declares writes: in the real registry.yaml copied above;
            # only its own .md file's content varies per test.
            (root / "agents" / "coder-critic.md").write_text(agent_md_body)
            with contextlib.redirect_stdout(io.StringIO()):
                return cr.crit_writes_tools(root)

    def test_no_write_tool_no_disclaimer_flagged(self):
        self.assertEqual(self._run("---\ntools: Read, Grep, Glob\n---\nReview things.\n"), 1)

    def test_no_write_tool_with_disclaimer_passes(self):
        self.assertEqual(self._run(
            "---\ntools: Read, Grep, Glob\n---\n"
            "Return as your final response. Do NOT write any files yourself.\n"), 0)

    def test_write_tool_present_passes_without_disclaimer(self):
        self.assertEqual(self._run("---\ntools: Read, Write, Grep\n---\nWrite the report directly.\n"), 0)

    def test_real_tree_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cr.crit_writes_tools(ROOT), 0)
```

Add this class to `tests/test_check_refs.py` (the file already does `import check_refs as cr`
and defines `ROOT` at module level — follow `TestArtifactPaths`'s exact fixture pattern above
it, which also copies the real `rules/registry.yaml` into a tempdir).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_check_refs.py::TestWritesTools -v`
Expected: FAIL with `AttributeError: module 'check_refs' has no attribute 'crit_writes_tools'`

- [ ] **Step 3: Implement `crit_writes_tools`**

Add to `scripts/check_refs.py`, directly above `CRITERIA = {`:

```python
WRITE_CAPABLE_TOOLS = {"Write", "Edit", "NotebookEdit"}
NO_WRITE_MARKER = re.compile(r"do\s+not\s+(write|edit)\b", re.I)

def _agent_tools(root, name):
    """Resolve an agent's own .md file across both roster directories (rl.AGENT_DIRS) and
    return (path, full text, tools set) — or (None, "", set()) if no file exists anywhere."""
    for d in rl.AGENT_DIRS:
        f = root / d / f"{name}.md"
        if f.exists():
            text = f.read_text(errors="ignore")
            m = re.search(r"^(?:allowed-)?tools:\s*(.*)$", text, re.M)
            tools = {tok.strip() for tok in m.group(1).split(",")} if m else set()
            return f, text, tools
    return None, "", set()

def crit_writes_tools(root):
    """Phase 2.1 of the 2026-09-23 repair plan fixed nine agents by hand: declared to write a
    path in registry.yaml, with no Write/Edit tool and no instruction that the dispatching
    skill writes on their behalf, so the write silently never happened. This is the check that
    should have existed to catch it. An agent whose own .md file cannot be resolved is skipped —
    that is registry-complete's job (pipeline.py registry check), not this criterion's."""
    reg = rl.load_registry(root)
    hits = []
    for name, e in reg["agents"].items():
        writes = e.get("writes") or []
        if not writes:
            continue
        f, text, tools = _agent_tools(root, name)
        if f is None:
            continue
        if tools & WRITE_CAPABLE_TOOLS:
            continue
        if NO_WRITE_MARKER.search(text):
            continue
        hits.append(f"{f.relative_to(root)}: registry.yaml declares writes: {writes} but this "
                    f"agent has no write-capable tool and no 'do not write/edit' disclaimer")
    return report("writes-tools", hits)
```

Add `"writes-tools": crit_writes_tools,` to the `CRITERIA` dict.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_check_refs.py::TestWritesTools -v`
Expected: PASS (4/4)

- [ ] **Step 5: Wire into `check_fork.sh` and verify the gate**

In `scripts/check_fork.sh`, change:
```bash
for c in latex-residue manuscript-model deleted-things inv-refs skill-refs tool-name hooks-readme artifact-paths promote-vendor-warn promote-register-check; do
```
to:
```bash
for c in latex-residue manuscript-model deleted-things inv-refs skill-refs tool-name hooks-readme artifact-paths promote-vendor-warn promote-register-check writes-tools; do
```

Run: `./scripts/check_fork.sh 2>&1 | grep writes-tools`
Expected: `PASS [writes-tools]`

- [ ] **Step 6: Full suite and commit**

Run: `python3 -m pytest tests/ -q && ./scripts/check_fork.sh`
Expected: both PASS.

```bash
git add scripts/check_refs.py scripts/check_fork.sh tests/test_check_refs.py
git commit -m "feat(check_refs): add writes-vs-tools consistency check (closeout handoff §4.2)"
```

---

## Task 2: Hook direct-wiring check

**Files:**
- Modify: `scripts/check_refs.py` (add `crit_hooks_wired`, register in `CRITERIA`)
- Modify: `scripts/check_fork.sh:93-96` (add `hooks-wired` to the criterion loop — note this
  name collides with `check_install.sh`'s existing per-*project* `hooks-wired` criterion; they
  check different things at different layers and neither reads the other, but name the
  criterion `hooks-wired-source` in `CRITERIA`/`check_fork.sh` to keep the two unambiguous in
  combined output)
- Test: `tests/test_check_refs.py` (new `TestHooksWiredSource` class)

**Interfaces:**
- Consumes: `hooks/README.md`'s existing `| \`name\` | Event | ... |` table (already parsed by
  `crit_hooks_readme`'s regex — reuse the same regex, do not duplicate the parsing logic
  differently), `seeds/settings.json` as raw text.
- Produces: `crit_hooks_wired_source(root) -> int`, registered as `CRITERIA["hooks-wired-source"]`.

`hooks/README.md` already documents, per hook, whether it is invoked directly (an `Event` cell
with no "via") or indirectly (e.g. `lint-scripts.sh`'s `PostToolUse (via post-edit-lint.sh) /
CLI`). Verified 2026-09-24: `seeds/settings.json` currently wires all 12 directly-invoked hooks
and correctly omits `lint-scripts.sh`, the one indirectly-invoked hook — so this check passes
today. It exists to catch the *next* hook shipped with a direct-wiring README row and no
`seeds/settings.json` entry — exactly the shape `hooks/README.md`'s own "A hook that is
installed but unwired is not a dormant feature" section describes as a defect already found
twice (`session-guard.py`, before this section was written).

- [ ] **Step 1: Write the failing tests**

```python
class TestHooksWiredSource(unittest.TestCase):
    """hooks/README.md documents which hooks are wired directly vs. invoked indirectly (an
    Event cell containing 'via'). A directly-documented hook that seeds/settings.json never
    mentions is exactly the R-7/session-guard.py shape hooks/README.md's own 'not a dormant
    feature' section describes — this makes it a gate instead of a paragraph."""

    def _run(self, event_cell: str, settings_text: str) -> int:
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "hooks").mkdir()
            (root / "hooks" / "probe.sh").write_text("#!/bin/bash\n# does a thing\n")
            (root / "hooks" / "README.md").write_text(
                "| Hook | Event | What it does |\n|---|---|---|\n"
                f"| `probe.sh` | {event_cell} | does a thing |\n")
            (root / "seeds").mkdir()
            (root / "seeds" / "settings.json").write_text(settings_text)
            with contextlib.redirect_stdout(io.StringIO()):
                return cr.crit_hooks_wired_source(root)

    def test_directly_wired_hook_missing_from_settings_flagged(self):
        self.assertEqual(self._run("PreToolUse", "{}"), 1)

    def test_directly_wired_hook_present_in_settings_passes(self):
        self.assertEqual(self._run("PreToolUse", '{"cmd": "hooks/probe.sh"}'), 0)

    def test_indirectly_invoked_hook_not_required_in_settings(self):
        self.assertEqual(self._run("PostToolUse (via other.sh)", "{}"), 0)

    def test_real_tree_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cr.crit_hooks_wired_source(ROOT), 0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_check_refs.py::TestHooksWiredSource -v`
Expected: FAIL with `AttributeError: module 'check_refs' has no attribute 'crit_hooks_wired_source'`

- [ ] **Step 3: Implement `crit_hooks_wired_source`**

Add to `scripts/check_refs.py`, directly below `crit_hooks_readme`:

```python
def crit_hooks_wired_source(root):
    """hooks/README.md's table cell for Event states, per hook, whether it fires by direct
    settings.json wiring or 'via' another hook / the CLI. A directly-documented hook that
    seeds/settings.json never names is an unwired promise (hooks/README.md's own 'not a
    dormant feature' section, written after session-guard.py shipped exactly this way)."""
    readme = root / "hooks" / "README.md"
    settings = root / "seeds" / "settings.json"
    if not readme.exists():
        return report("hooks-wired-source", ["hooks/README.md missing"])
    if not settings.exists():
        return report("hooks-wired-source", ["seeds/settings.json missing"])
    settings_text = settings.read_text()
    rows = [(n, e) for n, e in
            re.findall(r"^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|", readme.read_text(), re.M)
            if n.endswith((".py", ".sh"))]
    hits = []
    for name, event in rows:
        if re.search(r"\bvia\b", event, re.I):
            continue
        if name not in settings_text:
            hits.append(f"hooks/{name}: README documents direct wiring ('{event.strip()}') "
                        f"but seeds/settings.json never names it")
    return report("hooks-wired-source", hits)
```

Add `"hooks-wired-source": crit_hooks_wired_source,` to `CRITERIA`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_check_refs.py::TestHooksWiredSource -v`
Expected: PASS (4/4)

- [ ] **Step 5: Wire into `check_fork.sh`**

Extend the same `for c in ...` line from Task 1 Step 5 to also include `hooks-wired-source`.

Run: `./scripts/check_fork.sh 2>&1 | grep hooks-wired-source`
Expected: `PASS [hooks-wired-source]`

- [ ] **Step 6: Full suite and commit**

Run: `python3 -m pytest tests/ -q && ./scripts/check_fork.sh`

```bash
git add scripts/check_refs.py scripts/check_fork.sh tests/test_check_refs.py
git commit -m "feat(check_refs): add hooks-wired-source check (closeout handoff §4.2)"
```

---

## Task 3: Fix and wire `scripts/audit_graph.py` (reachability)

**Files:**
- Modify: `scripts/audit_graph.py`
- Modify: `scripts/check_fork.sh` (new section, bespoke invocation — not the `py()` helper,
  since this script takes a positional root, not `--root`)
- Test: `tests/test_audit_graph.py` (new `TestAuditGraphLogic` class)

**Interfaces:**
- Consumes: nothing new.
- Produces: `audit_graph.py <root> [out]` now exits 1 when `dangling_paths` is non-empty (it
  previously always exited 0); `report["dangling_paths"]` is fixed to no longer false-positive
  on a valid `ai-audit/agents/*.md` or `ai-audit/skills/*` / `zotpilot-skills/*` reference.

`scripts/audit_graph.py` already computes exactly the "reachability" check the closeout
handoff asked for, but two things kept it from being trustworthy: it has a real
false-positive (a valid vendored-tree reference reads as dangling), and nothing runs it.
Verified 2026-09-24 by running it against the live tree: **before** this task,
`dangling path refs: 1` — `rules/agents.md` → `agents/civilize-auditor.md`, which actually
lives at `ai-audit/agents/civilize-auditor.md` (`registry_lib.AGENT_DIRS` already knows this
alias; `audit_graph.py` did not). The other two categories it reports —
`skills_never_invoked_by_anything` (1: `ztp-ollama`) and `orphan_files_no_inbound_reference`
(34, e.g. every `skills/*/gotchas.md` and `skills/pipeline/references/*.md`, both loaded by a
naming *convention* the regex-based scanner cannot see) — have **not** been triaged for false
positives, so this task wires them as WARN, never blocking, per this plan's Global Constraint
on FAIL-vs-WARN. Only the dangling-path count, now a verified zero, becomes a blocking gate.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_audit_graph.py` (which already defines `ROOT`, `SCRIPT`, and a `run(*args,
cwd=None)` helper at module level — reuse `run` as-is):

```python
class TestAuditGraphLogic(unittest.TestCase):
    """Logic-level regression, not CLI plumbing (TestAuditGraphCli above only exercises argv
    handling). Found 2026-09-24: rules/agents.md names agents/civilize-auditor.md, a real file
    that lives at ai-audit/agents/civilize-auditor.md — audit_graph.py reported it dangling
    because it never tried the vendored-tree alias registry_lib.AGENT_DIRS already knows."""

    def test_vendored_agent_reference_resolves(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "rules").mkdir()
            (root / "rules" / "probe.md").write_text("See agents/probe-agent.md for the contract.\n")
            (root / "ai-audit" / "agents").mkdir(parents=True)
            (root / "ai-audit" / "agents" / "probe-agent.md").write_text("---\ntools: Read\n---\n")
            r = run(str(root))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("dangling path refs        : 0", r.stdout)

    def test_genuinely_dangling_path_still_caught(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "rules").mkdir()
            (root / "rules" / "probe.md").write_text("See agents/does-not-exist.md.\n")
            r = run(str(root))
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("dangling path refs        : 1", r.stdout)

    def test_real_tree_has_zero_dangling_paths(self):
        r = run(str(ROOT))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("dangling path refs        : 0", r.stdout)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_audit_graph.py::TestAuditGraphLogic -v`
Expected: `test_vendored_agent_reference_resolves` and `test_real_tree_has_zero_dangling_paths`
FAIL (dangling count is 1, not 0, both before the fix and on the real tree, and exit code is 0
not 1 since nothing calls `sys.exit` yet); `test_genuinely_dangling_path_still_caught` already
passes by accident (exit 0 either way until Step 3) — confirm all three run, not that all three
fail.

- [ ] **Step 3: Fix the resolution bug and add the exit code**

In `scripts/audit_graph.py`, add near the top (after `EXEMPT_EXACT`):

```python
# A reference under agents/ or skills/ that does not resolve in the main tree may still be a
# real, valid reference into a vendored subtree — registry_lib.AGENT_DIRS already treats
# ai-audit/agents as an alias for agents/ when resolving an agent's own file; this scanner
# needs the same alias or it reports a real, valid reference as dangling.
VENDOR_ALIASES = {"agents": ["ai-audit/agents"], "skills": ["ai-audit/skills", "zotpilot-skills"]}
```

Then change the resolution loop (currently):

```python
    for t in set(PATH_RE.findall(scanned)):
        if t.startswith(EXEMPT_PREFIX) or t in EXEMPT_EXACT: continue
        hit = None
        for base in (CLAUDE, ROOT, f.parent):
            if (base/t).exists(): hit = base/t; break
        if hit is None:
            dangling_paths.append((str(rel), t))
        else:
            inbound[str(hit.resolve())] += 1
```

to:

```python
    for t in set(PATH_RE.findall(scanned)):
        if t.startswith(EXEMPT_PREFIX) or t in EXEMPT_EXACT: continue
        hit = None
        for base in (CLAUDE, ROOT, f.parent):
            if (base/t).exists(): hit = base/t; break
        if hit is None:
            top, _, rest = t.partition("/")
            for alias_dir in VENDOR_ALIASES.get(top, ()):
                cand = ROOT / alias_dir / rest
                if cand.exists():
                    hit = cand
                    break
        if hit is None:
            dangling_paths.append((str(rel), t))
        else:
            inbound[str(hit.resolve())] += 1
```

Then change the final block (currently ending on the five `print(...)` lines) to add WARN
labels and the exit code — replace:

```python
c=report["counts"]
print(f"{ROOT.name}: {c['files']} files, {c['agents']} agents, {c['skills']} skills")
print(f"  dangling path refs        : {len(report['dangling_paths'])}")
print(f"  agents named, not on roster: {report['agents_named_not_on_roster']}")
print(f"  roster agents never dispatched anywhere: {report['agents_on_roster_never_named_outside_own_file']}")
print(f"  skills never invoked      : {report['skills_never_invoked_by_anything']}")
print(f"  orphan files (0 inbound)  : {len(report['orphan_files_no_inbound_reference'])}")
```

with:

```python
c=report["counts"]
print(f"{ROOT.name}: {c['files']} files, {c['agents']} agents, {c['skills']} skills")
print(f"  dangling path refs        : {len(report['dangling_paths'])}")
print(f"  agents named, not on roster: {report['agents_named_not_on_roster']}")
print(f"  roster agents never dispatched anywhere: {report['agents_on_roster_never_named_outside_own_file']}")
print(f"  skills never invoked      : {report['skills_never_invoked_by_anything']}")
print(f"  orphan files (0 inbound)  : {len(report['orphan_files_no_inbound_reference'])}")
# Only dangling_paths is a verified-zero-false-positive gate (fixed 2026-09-24). The other
# three are printed for visibility but not yet triaged for false positives (gotchas.md and
# pipeline/references/*.md are loaded by naming convention, not a textual reference this
# regex-based scanner can see) — WARN, never blocking, per this plan's coverage rule.
if report["skills_never_invoked_by_anything"]:
    print(f"WARN [graph-skills] never invoked by anything: {report['skills_never_invoked_by_anything']}")
if report["orphan_files_no_inbound_reference"]:
    print(f"WARN [graph-orphans] {len(report['orphan_files_no_inbound_reference'])} files have no inbound reference (not yet triaged for false positives)")
sys.exit(1 if report["dangling_paths"] else 0)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_audit_graph.py -v`
Expected: PASS, all of `TestAuditGraphCli` (5) and `TestAuditGraphLogic` (3).

- [ ] **Step 5: Wire into `check_fork.sh`**

In `scripts/check_fork.sh`, directly above the `echo "── fixture ──"` line, add:

```bash
echo "── dependency graph (scripts/audit_graph.py) ──"
python3 "$RC/scripts/audit_graph.py" "$RC"
if [[ $? -ne 0 ]]; then echo "FAIL [graph-dangling]"; fail=1; else echo "PASS [graph-dangling]"; fi
```

Run: `./scripts/check_fork.sh 2>&1 | grep -A6 "dependency graph"`
Expected: `PASS [graph-dangling]`, plus the two `WARN [graph-*]` lines from Step 3 printed
above it (informational, `check_fork` still exits 0 overall).

- [ ] **Step 6: Full suite and commit**

Run: `python3 -m pytest tests/ -q && ./scripts/check_fork.sh`

```bash
git add scripts/audit_graph.py scripts/check_fork.sh tests/test_audit_graph.py
git commit -m "fix(audit_graph): resolve vendored-tree references, wire as blocking-on-dangling-only gate"
```

---

## Task 4: Cited script-path existence check

**Files:**
- Modify: `scripts/check_refs.py` (add `crit_script_refs`, register in `CRITERIA`)
- Modify: `scripts/check_fork.sh:93-96` (add `script-refs` to the criterion loop)
- Test: `tests/test_check_refs.py` (new `TestScriptRefs` class)

**Interfaces:**
- Consumes: `shipped_files`, `lines_of` (already defined in `check_refs.py`).
- Produces: `crit_script_refs(root) -> int`, registered as `CRITERIA["script-refs"]`.

The closeout handoff's example of this gap was `quarto_structure_check.py`/`INV-25` being
cited before either existed — since fixed by building them, not by a check that would catch
the *next* one. Verified 2026-09-24: a regex for `scripts/<path>.py` / `scripts/<path>.sh`
tokens across the shipped tree, excluding `scripts/acquire/` (project-level, never present in
this template — the same exemption `LATEX_RESIDUE`'s `MANUSCRIPT_MODEL` checks already use),
returns **zero hits** against the real tree today — this is a clean, verified-zero-false-
positive check and ships as a blocking gate from the start, not a WARN.

- [ ] **Step 1: Write the failing tests**

```python
class TestScriptRefs(unittest.TestCase):
    """R-fix, closeout handoff §4.2 item 4: a script path named in prose (a rule, a skill, an
    agent) that does not exist on disk. quarto_structure_check.py/INV-25 was cited before it
    existed once; this is the check that stops the next one."""

    def _run(self, text: str, create=()) -> int:
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "rules").mkdir()
            (root / "rules" / "probe.md").write_text(text)
            for rel in create:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("")
            with contextlib.redirect_stdout(io.StringIO()):
                return cr.crit_script_refs(root)

    def test_nonexistent_script_flagged(self):
        self.assertEqual(self._run("Run `scripts/does_not_exist.py` first.\n"), 1)

    def test_existing_script_passes(self):
        self.assertEqual(self._run("Run `scripts/check_fork.sh` first.\n",
                                    create=["scripts/check_fork.sh"]), 0)

    def test_acquire_scripts_exempt(self):
        self.assertEqual(self._run("Run `scripts/acquire/clean_raw.py` (project-specific).\n"), 0)

    def test_real_tree_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cr.crit_script_refs(ROOT), 0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_check_refs.py::TestScriptRefs -v`
Expected: FAIL with `AttributeError: module 'check_refs' has no attribute 'crit_script_refs'`

- [ ] **Step 3: Implement `crit_script_refs`**

Add to `scripts/check_refs.py`, directly below `crit_tool_name`:

```python
SCRIPT_REF = re.compile(r"(?<![A-Za-z0-9_./-])scripts/[A-Za-z0-9_./-]+\.(?:py|sh)\b")
SCRIPT_REF_EXEMPT_PREFIX = ("scripts/acquire/",)

def crit_script_refs(root):
    """A scripts/<path>.py or .sh cited in prose that does not exist on disk — the
    quarto_structure_check.py/INV-25 shape (closeout handoff §4.2 item 4), generalized."""
    hits = []
    for f in shipped_files(root, SHIP):
        for n, ln in lines_of(f):
            for m in SCRIPT_REF.finditer(ln):
                tok = m.group(0)
                if tok.startswith(SCRIPT_REF_EXEMPT_PREFIX):
                    continue
                if not (root / tok).exists():
                    hits.append(f"{f.relative_to(root)}:{n}: {tok} does not exist")
    return report("script-refs", hits)
```

Add `"script-refs": crit_script_refs,` to `CRITERIA`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_check_refs.py::TestScriptRefs -v`
Expected: PASS (4/4)

- [ ] **Step 5: Wire into `check_fork.sh`**

Extend the `for c in ...` line (same one from Tasks 1–2) to also include `script-refs`.

Run: `./scripts/check_fork.sh 2>&1 | grep script-refs`
Expected: `PASS [script-refs]`

- [ ] **Step 6: Full suite and commit**

```bash
python3 -m pytest tests/ -q && ./scripts/check_fork.sh
git add scripts/check_refs.py scripts/check_fork.sh tests/test_check_refs.py
git commit -m "feat(check_refs): add script-refs cited-artifact-existence check (closeout handoff §4.2)"
```

---

## Task 5: Plan-liveness check (advisory)

**Files:**
- Create: `scripts/check_plan_liveness.py`
- Modify: `scripts/check_fork.sh` (new section, advisory only, never sets `fail=1`)
- Test: `tests/test_check_plan_liveness.py`

**Interfaces:**
- Consumes: `docs/plans/*.md`, `git log` (via `subprocess`).
- Produces: `check_plan_liveness.py --root <path> [--days N, default 7]`, prints
  `PASS [plan-liveness]` or `WARN [plan-liveness]` with one line per stale plan, **always exits 0**.

The closeout handoff's example: `docs/plans/2026-09-16-skill-defect-closeout.md` sat with no
commit landing any of its 43 defects for seven days, invisible to every existing gate, because
none of them looks at `docs/plans/` at all. **Scope this check honestly, not more cleverly
than it can be:** verified 2026-09-24 that this repo's plans use two different completion
conventions — the newer style (`docs/plans/2026-09-23_pipeline-repair.md`) flips `- [ ]` to
`- [x]` as tasks land; the older, `superpowers`-style plans (`2026-09-16-skill-defect-
closeout.md`, `2026-09-16-skill-token-optimization.md`) never flip a checkbox even when a task
is fully done — completion is recorded in prose in a Progress Log section instead. A signal
based on checkbox-flip counts would therefore false-positive-WARN on a fully-delivered
older-style plan. The signal this task builds instead — **has any commit touched this file's
path at all in N days** — is coarser (a commit that only edits the plan's own Progress Log
resets the clock same as a commit that lands real work) but has no such false positive, and it
is exactly the literal gap named: *"is there an open plan that hasn't moved in a week."* This
ships as **WARN only, never blocking** — a stalled-plan judgment call is not a fact a script
should be trusted to enforce silently, per this plan's Global Constraint on FAIL vs. WARN.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_check_plan_liveness.py`:

```python
import os, pathlib, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_plan_liveness.py"

def git(args, cwd, when=None):
    env = os.environ.copy()
    if when:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True)

def init_repo(root):
    git(["init", "-q"], root)
    git(["config", "user.email", "t@example.com"], root)
    git(["config", "user.name", "T"], root)

def run_check(root, days=7):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), "--days", str(days)],
                           capture_output=True, text=True)

class TestCheckPlanLiveness(unittest.TestCase):
    """closeout handoff §4.2 item 5: 'nothing asks is there an open plan that hasn't moved in
    a week' — the 2026-09-16 closeout plan's own stall, invisible to every prior gate."""

    def test_old_open_plan_warns(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            init_repo(root)
            (root / "docs" / "plans").mkdir(parents=True)
            (root / "docs" / "plans" / "old-plan.md").write_text("- [ ] Step 1\n")
            git(["add", "."], root)
            git(["commit", "-q", "-m", "old"], root, when="2020-01-01T00:00:00")
            r = run_check(root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("WARN [plan-liveness]", r.stdout)
            self.assertIn("old-plan.md", r.stdout)

    def test_recently_touched_open_plan_quiet(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            init_repo(root)
            (root / "docs" / "plans").mkdir(parents=True)
            (root / "docs" / "plans" / "fresh-plan.md").write_text("- [ ] Step 1\n")
            git(["add", "."], root)
            git(["commit", "-q", "-m", "fresh"], root)
            r = run_check(root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("PASS [plan-liveness]", r.stdout)

    def test_fully_checked_plan_ignored_even_if_old(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            init_repo(root)
            (root / "docs" / "plans").mkdir(parents=True)
            (root / "docs" / "plans" / "done-plan.md").write_text("- [x] Step 1\n")
            git(["add", "."], root)
            git(["commit", "-q", "-m", "done"], root, when="2020-01-01T00:00:00")
            r = run_check(root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("PASS [plan-liveness]", r.stdout)

if __name__ == "__main__": unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_check_plan_liveness.py -v`
Expected: FAIL — `scripts/check_plan_liveness.py` does not exist yet (`FileNotFoundError` /
non-zero from a missing script).

- [ ] **Step 3: Implement `scripts/check_plan_liveness.py`**

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_check_plan_liveness.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Wire into `check_fork.sh`**

Directly below the Task 3 dependency-graph block, add:

```bash
echo "── plan liveness (advisory, scripts/check_plan_liveness.py) ──"
python3 "$RC/scripts/check_plan_liveness.py" --root "$RC"
```

(No `fail=1` anywhere in this block — it is always advisory.)

Run: `./scripts/check_fork.sh 2>&1 | grep -A3 "plan liveness"`
Expected: prints `PASS [plan-liveness]` or a `WARN` block — either way `check_fork.sh`'s own
exit code is unaffected.

- [ ] **Step 6: Full suite and commit**

```bash
python3 -m pytest tests/ -q && ./scripts/check_fork.sh
git add scripts/check_plan_liveness.py scripts/check_fork.sh tests/test_check_plan_liveness.py
git commit -m "feat: add advisory plan-liveness check (closeout handoff §4.2 item 5)"
```

---

## Task 6: Unblock and hand off the 09-16 closeout plan

**Files:**
- Modify: `docs/plans/2026-09-16-skill-defect-closeout.md` (7 verification-chain fixes, 1 count
  correction, 1 new amendment note for D2)

**Interfaces:** none (documentation-only task; no code, no tests — the "test" is that the
fixed shell chains actually run to their end, per Step 2 below).

This task does not re-derive or re-execute the 09-16 plan's 43 defects — they already exist in
full TDD detail in that file, verified current by a fresh read on 2026-09-24 ("The 43 unfixed
defects are all still exactly as ... described," per its own audit). Duplicating them here
would violate this repo's DRY convention and create two copies to keep in sync. This task's
job is narrower: apply the amendments that plan's own audit already specified, plus one it
could not have known about yet, so the next session can resume at Task 1 without rediscovering
either.

- [ ] **Step 1: Fix the 7 broken verification chains**

Each of these chains calls `check_paths.py` and/or `check_refs.py` with no `--root`, which
exits on an argparse usage error and kills everything after it in the `&&` chain — confirmed
2026-09-24 by running `python3 scripts/check_paths.py` bare: `error: the following arguments
are required: --root`. Fix all 7 occurrences by appending
`--root /Users/andrew.mueller/Academic/research-claude` to every bare `check_paths.py` /
`check_refs.py` invocation in the plan. Use `Edit` with `replace_all: true` where the exact
same broken substring repeats, or per-line replacement where the surrounding chain differs:

At `docs/plans/2026-09-16-skill-defect-closeout.md:435`:
```
old: && python3 scripts/check_paths.py; echo "exit=$?"
new: && python3 scripts/check_paths.py --root /Users/andrew.mueller/Academic/research-claude; echo "exit=$?"
```
(This exact substring `&& python3 scripts/check_paths.py; echo "exit=$?"` also appears at
lines 630 and 1170 — use `replace_all: true` for these three in one `Edit` call.)

At line 812:
```
old: && python3 scripts/check_paths.py && ./tests/run_fixture.sh; echo "exit=$?"
new: && python3 scripts/check_paths.py --root /Users/andrew.mueller/Academic/research-claude && ./tests/run_fixture.sh; echo "exit=$?"
```

At lines 995 and 1384 (identical substring — `replace_all: true`):
```
old: && python3 scripts/check_paths.py && python3 scripts/check_refs.py; echo "exit=$?"
new: && python3 scripts/check_paths.py --root /Users/andrew.mueller/Academic/research-claude && python3 scripts/check_refs.py --root /Users/andrew.mueller/Academic/research-claude; echo "exit=$?"
```

At line 1421:
```
old: && python3 scripts/check_paths.py && python3 scripts/check_refs.py && ./scripts/check_install.sh --all; echo "exit=$?"
new: && python3 scripts/check_paths.py --root /Users/andrew.mueller/Academic/research-claude && python3 scripts/check_refs.py --root /Users/andrew.mueller/Academic/research-claude && ./scripts/check_install.sh --all; echo "exit=$?"
```

- [ ] **Step 2: Verify each fixed chain actually reaches its end**

For each of the 7 lines fixed in Step 1, run the corrected command exactly as written (it will
run the real, current test suite and gates — expect it to pass on the current tree, since
nothing else in this plan touches the 09-16 plan's own subject matter). Confirm the final
`echo "exit=$?"` line prints, proving the chain no longer dies partway through. Do not skip
this — this is the executable check for this task ("run as written, each verification chain
aborts at the gate step," now fixed).

- [ ] **Step 3: Correct the `/obsidian-digest-sync` count**

At `docs/plans/2026-09-16-skill-defect-closeout.md:1233`:
```
old: `/obsidian-digest-sync` appears three times: the header comment and the two
new: `/obsidian-digest-sync` appears twice: the header comment and the
```
Read lines 1230-1240 first to confirm the exact surrounding wording before editing (the
digest-delivery audit found this exact off-by-one but this plan has not yet had the fix
applied to its own text).

- [ ] **Step 4: Note the `tools` baseline drift**

In Task 0's row of the plan's Progress Log (near the top, where the nine baseline character
counts are recorded), add a note next to the `tools` skill's baseline: it was 4,347 chars when
recorded and has since grown to 6,924 for unrelated reasons (this session's connectivity-check
work touches `check_refs.py`/`check_fork.sh`, not `skills/tools/SKILL.md`, so this plan's own
work does not move that number further — the note is so Task 7's re-baseline step does not
mistake old drift for new regression).

- [ ] **Step 5: Add the D2-is-moot amendment**

`docs/plans/2026-09-23_pipeline-repair.md` Phase 2.4 (ruled and gate-met 2026-09-24) renamed
the vendored `ai-audit` skill and agent from `/humanize`/`humanize-auditor` to
`/civilize`/`civilize-auditor` upstream. D2, as posed in the 09-16 plan (Task 6, Step 2), exists
because `/write humanize` (this pipeline's in-place rewriter mode) and the vendored `/humanize`
(detect-only, explicitly non-rewriting) did opposite things under near-identical names — that
premise no longer holds now that the vendored skill is named `/civilize`. Verify this directly
before editing (`grep -rn humanize skills/ agents/ ai-audit/ rules/` should show only
`skills/write/SKILL.md`'s own humanize mode and `ai-audit/VENDORED.md`'s provenance note — no
second `/humanize` skill anywhere), then add, directly above `## Task 6` in
`docs/plans/2026-09-16-skill-defect-closeout.md`:

```markdown
> **Amendment, 2026-09-24 (before resuming this task):** D2 is moot. The vendored skill this
> defect names — `ai-audit`'s `/humanize` — was renamed to `/civilize` upstream
> (`docs/plans/2026-09-23_pipeline-repair.md` Phase 2.4, gate met 2026-09-24, commit `c737ac6`).
> There is no longer a second skill named `/humanize` for `/write humanize` to collide with.
> Skip Step 2 ("Put D2 to the user") and Step 8 ("Apply D2") below — do not rename `/write
> humanize`; there is nothing left to disambiguate it from. Re-verify with
> `grep -rn humanize skills/ agents/ ai-audit/ rules/` before skipping: it should show only
> `skills/write/SKILL.md`'s own humanize mode and `ai-audit/VENDORED.md`'s provenance note.
```

- [ ] **Step 6: Commit**

```bash
cd /Users/andrew.mueller/Academic/research-claude
git add docs/plans/2026-09-16-skill-defect-closeout.md
git commit -m "docs(plans): unblock 09-16 closeout — fix --root gaps, correct count, resolve D2 as moot"
```

- [ ] **Step 7: Hand off**

The 09-16 plan is now resumable at Task 1 with a working verification recipe and one fewer
open decision (D3 — the referees scoring-source question at that plan's own Task 1 Step 2 —
remains genuinely open and must still go to the user at execution time, exactly as that plan
already specifies; this task does not answer it). Resume it with
`superpowers:subagent-driven-development` or `superpowers:executing-plans`, one task per
session, per that plan's own execution model (`docs/plans/2026-09-16-skill-defect-
closeout.md`, "How to execute this plan across cleared contexts").

---

## What this plan does not do

It does not resume `docs/plans/2026-09-23_pipeline-repair.md` Phase 5 (POGM4's native-Quarto
migration) — that work is in `~/Research/POGM4`, a different repository with its own plan
(`quality_reports/plans/2026-09-23_jrer-submission-plan.md`), out of this repo's scope. It does
not re-litigate the divergence register (`docs/decisions/clo-author-divergences.md`) or the
six `§4.5` audit defects the closeout handoff listed — both were verified closed on 2026-09-24
by reading the current source directly (registry entries, gate code, skill text), not by
trusting either plan's own claims about itself: every divergence entry now carries either
`DELIBERATE DIVERGENCE`/`OBSOLETE`/`INHERITED` or an explicit `CLOSED 2026-09-24`, and all six
`§4.5` items (`ai-audit` wiring, `/promote` vendor warnings, `state strike`, registry
visibility, the four skill conflicts, `/submit deposit`) have working code behind them today.
