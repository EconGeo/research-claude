# Remaining Skill Evals — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One functionality eval per remaining skill — twenty evals, each a runner + a checker + a red/green unit test — so every shipped skill has a mechanism gate the way `/ztp-data-tag`, `/lit-position` and `/tools validate-bib` already do.

**Architecture:** Each eval copies `tests/fixture-project` to a temp dir, links this checkout into it, seeds the input state the skill needs, runs the skill once through `claude -p … --output-format stream-json`, and runs a Python checker over the transcript (plus the ZotPilot mock's call log or the project dir). Checkers assert **mechanism** — which tool, in what order, with which flags, what was never touched — never LLM output quality (audit 2026-09-15 §3 P7 rule 3). Task 0 factors the runner boilerplate the three existing evals repeat into `tests/evals/_lib.sh` and `tests/evals/evallib.py`, and extends the mock with the tools the vendored skills call; Tasks 1–20 each add one eval.

**Tech Stack:** bash, Python 3 stdlib (`json`, `re`, `pathlib`, `unittest`), `claude -p`, `tests/mock_zotpilot.py`.

**Spec:** `docs/audits/2026-09-15_skill-best-practices-audit.md` §6 (eval inputs and key assertions per skill) and §3 P7 (the four eval rules), as carried by `docs/plans/2026-09-24-option-gates-subagent-routing-evals.md` Part C and its residue list ("20 remain").

## Global Constraints

- **Mechanism, not outcome** (audit §3 P7 rule 3). A checker never scores prose, never asserts a table's content, never asserts what the model said.
- **Run alone** (audit §3 P7 rule 4). Never run two evals in parallel; never run one beside `tests/run_fixture.sh --live`.
- **A gate that cannot go red is not one** (`tests/test_eval_checkers.py` docstring). Every checker ships with a unit test that drives it red on a mutated transcript and green on the correct one.
- **Nothing project-specific ships** (`CLAUDE.md`). Eval fixtures live under `tests/`, which `scripts/check_fork.sh` does not scan; nothing under `agents/`, `skills/`, `rules/`, `hooks/` or `templates/` changes in this plan.
- **The checkout is never written through a link.** `apply.sh` links `skills/`, `agents/`, `rules/`, `hooks/`, `templates/`, `scripts/` **and `references/`** (D-26) into the project. A skill that fills `.claude/references/domain-profile.md` in the eval project would edit the canonical file. `_lib.sh` replaces every `references/` link with a copy and fails the eval if `git -C "$RC" status --porcelain` differs after the run.
- **Live runs are long.** A single critic dispatch measured 12 minutes (`tests/run_fixture.sh` comments). Timeouts below are per eval; raise `EVAL_TIMEOUT` rather than trimming assertions.
- **A red live run is a finding, not a reason to loosen the checker.** If the red traces to the harness (mock, runner, allowed tools, a regex that mismatched the transcript's real text) fix it in the task and re-run. If it traces to the skill, commit the eval as is, record `FAIL (skill)` with the failing assertion in the Progress Log, and leave the skill fix for a follow-up task. The audit lists several assertions as "red today"; they stay in.
- **Commit messages** end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Run `./scripts/check_fork.sh` before every commit (exit 0 required; it cannot fail on `tests/` changes, so a red means something else drifted).
- **Test command:** `python3 -m unittest discover -s tests -q` (327 tests, ~140 s at plan time). Per-task: `python3 -m unittest tests.test_eval_<skill> -v`.

## Scope — the twenty, and the three left out

Audit §6 lists 25 rows. Done before this plan: `ztp-data-tag`, `lit-position`, `tools validate-bib`. Not in this plan, each for a reason recorded here so nobody re-derives it:

| Skill | Why not | Where it is covered |
|---|---|---|
| `pipeline` | `tests/run_fixture.sh --live` already runs `/pipeline run --until strategy --yes` in a fixture copy and asserts dispatch-log, state validity and critic completion. A second harness would duplicate it. | `tests/run_fixture.sh` live tier |
| `ztp-setup` | Its mechanism is `pip install` into an environment and `zotpilot setup` writing `~/.config/zotpilot`. No temp dir isolates that; a mock cannot stand in for an installer. | Manual; the fork's own README |
| `ztp-ollama` | Its mechanism is `zotpilot config set …` against the real machine config and a forced re-index. Same objection. | Manual |

The twenty, in the order the tasks run (cheap, no-agent evals first; agent-dispatching evals last):

| # | Skill | MCP mock | Dispatches agents | Timeout (s) |
|---|---|---|---|---|
| 1 | careful | no | no | 600 |
| 2 | freeze | no | no | 600 |
| 3 | checkpoint | no | no | 900 |
| 4 | new-project-ztp | yes | no | 900 |
| 5 | seed-papers | yes | no | 900 |
| 6 | ztp-review | yes | no | 900 |
| 7 | ztp-research | yes | no | 900 |
| 8 | ztp-profile | yes | no | 900 |
| 9 | ztp-tutor | yes | no | 900 |
| 10 | promote | no | no | 900 |
| 11 | civilize | no | one | 1800 |
| 12 | verify-claims | no | one | 1800 |
| 13 | revise | no | halts before any | 1800 |
| 14 | submit | no | verifier (+ possibly three critics) | 3600 |
| 15 | talk | no | two | 3600 |
| 16 | write | no | two | 3600 |
| 17 | strategize | no | two | 3600 |
| 18 | discover | no | two | 3600 |
| 19 | review | no | three | 3600 |
| 20 | analyze | no | four | 5400 |

## Harness conventions every task follows

- **Runner:** `tests/evals/<skill>.sh`, executable, sources `tests/evals/_lib.sh`, calls `eval_setup`, seeds, calls `eval_run` once per prompt, then `eval_finish <checker> <args…>`.
- **Checker:** `tests/evals/check_<skill>.py`, imports `evallib`, prints one summary line, one `  FAIL …` line per failed assertion, then `check_<skill>: PASS|FAIL`, exit 0/1.
- **Unit test:** `tests/test_eval_<skill>.py`, one file per skill (so twenty tasks never edit one shared file), using the `run()` helper shown in Task 1 verbatim in each file.
- **Prompts** are the audit's §6 inputs, made non-interactive: a skill that waits for the user ends its turn, and the checker asserts what did *not* happen after the wait.
- **What the transcript shows.** `--verbose` stream-json carries the main session's `tool_use` blocks (with `id`, `name`, `input`) and `tool_result` blocks (with `tool_use_id`, `content`, `is_error`). It does not reliably show a subagent's own tool calls, so no checker asserts what happened *inside* an Agent; the mock log is the only window into a subagent's MCP calls.
- **Post-run facts** (does a file exist, is it a symlink, did a render exit 0) are computed by the runner in bash and passed to the checker as its extra arguments — never recomputed inside the checker.

---

### Task 0: Shared runner library, shared checker library, mock extension

**Files:**
- Create: `tests/evals/_lib.sh`
- Create: `tests/evals/evallib.py`
- Create: `tests/test_evallib.py`
- Modify: `tests/mock_zotpilot.py` (add nine tools; extend `WRITES`)
- Modify: `tests/fixture-project/zotpilot_fixture.json` (add `external`, tutor fields on D1, duplicate tags)
- Modify: `tests/test_mock_zotpilot.py` (append tests for the new tools)

**Interfaces:**
- Produces (bash, sourced): `RC` (this checkout, physical path); `eval_setup` → sets `E` (project dir), `MCP_CFG` (empty servers), `LOG`, `ERR`, snapshots `RC_BEFORE`; `eval_mock` → rewrites `MCP_CFG` to register the mock logging to `ERR`; `eval_run <prompt> <logfile> <allowed-tool>…` → runs `claude -p`, writes `<logfile>` and `<logfile>.stderr`, refuses on `Unknown command:`; `eval_finish <checker-basename> <arg>…` → checkout-drift check, then `python3 tests/evals/<checker> <arg>…`, exit code becomes `status`. Env: `EVAL_TIMEOUT` (default 1800), `KEEP=1` keeps `$E`, `RC_LINK` (Task 10 only) links from another checkout.
- Produces (python `evallib`): `tool_uses(path) -> list[tuple[str, dict, str]]` (name, input, id, in order); `tool_results(path) -> dict[str, tuple[str, bool]]` (id → text, is_error); `mock_calls(path) -> list[tuple[str, str, dict, dict|None]]` (kind CALL|WRITE, tool, args, result); `first(uses, pred) -> int|None` (pred takes name, input); `bash(uses) -> list[str]`; `finish(name, fails, summary) -> NoReturn`.
- Mock tools added: `search_academic_databases`, `ingest_by_identifiers` (WRITE), `manage_collections` (WRITE), `index_library` (WRITE), `profile_library`, `get_annotations`, `get_citations`, `get_paper_for_tutor`, `save_reading_persona` (WRITE), `annotate_pdf` (WRITE); `browse_library` gains `view="overview"` and `view="tags"`.

- [ ] **Step 1: Write `tests/evals/_lib.sh`**

```bash
#!/usr/bin/env bash
# tests/evals/_lib.sh — sourced by every eval runner under tests/evals/. Not a script.
#
# eval_setup   builds $E: a copy of tests/fixture-project, git-initialised, linked to this
#              checkout (or $RC_LINK), with every .claude/references/ link replaced by a copy —
#              references/ are LINKED (apply.sh, D-26), so a skill filling domain-profile.md in
#              the project would otherwise edit the canonical file. Snapshots the checkout's
#              porcelain status so eval_finish can refuse a run that wrote through a link.
# eval_mock    registers tests/mock_zotpilot.py as the `zotpilot` MCP server for this run,
#              logging to $ERR (the client does not forward a server's stderr).
# eval_run     runs one `claude -p` under a perl alarm (no timeout(1) on macOS; alarm survives
#              exec). stream-json so a killed run still leaves what it emitted.
# eval_finish  checkout-drift check, then the checker. Its exit code is the eval's.
#
# Env: EVAL_TIMEOUT (s, default 1800) · KEEP=1 keeps $E on PASS (a FAIL always keeps it).
set -u
RC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
status=1

eval_cleanup() {
  if [[ "${KEEP:-0}" == 1 || "${status:-1}" != 0 ]]; then echo "kept: $E"; else rm -rf "$E"; fi
}

eval_setup() {
  E="$(mktemp -d)"
  trap eval_cleanup EXIT
  cp -R "$RC/tests/fixture-project/." "$E/"
  git -C "$E" init -q && git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm fixture
  "${RC_LINK:-$RC}/apply.sh" --project-dir "$E" --link >/dev/null || { echo "apply.sh --link failed"; exit 1; }
  local f t
  for f in "$E"/.claude/references/*.md; do
    [[ -L "$f" ]] || continue
    t="$(cd "$(dirname "$f")" && cd "$(dirname "$(readlink "$f")")" && pwd -P)/$(basename "$(readlink "$f")")"
    rm "$f" && cp "$t" "$f"
  done
  git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "linked + seeded" >/dev/null
  RC_BEFORE="$(git -C "$RC" status --porcelain)"
  MCP_CFG="$E/mcp.json"; echo '{"mcpServers": {}}' >"$MCP_CFG"
  LOG="$E/eval.stream.jsonl"; ERR="$E/mock.calls.log"; : >"$ERR"
}

eval_mock() {
  cat >"$MCP_CFG" <<JSON
{"mcpServers": {"zotpilot": {"type": "stdio", "command": "python3", "args": ["$RC/tests/mock_zotpilot.py"], "env": {"MOCK_ZOTPILOT_LOG": "$ERR"}}}}
JSON
}

eval_run() {  # eval_run <prompt> <logfile> <allowed-tool>...
  local prompt="$1" log="$2"; shift 2
  command -v claude >/dev/null 2>&1 || { echo "claude not on PATH"; exit 1; }
  ( cd "$E" && exec perl -e 'alarm shift @ARGV; exec @ARGV' "${EVAL_TIMEOUT:-1800}" \
      claude -p "$prompt" --permission-mode acceptEdits \
      --mcp-config "$MCP_CFG" --strict-mcp-config --allowedTools "$@" \
      --output-format stream-json --verbose ) >"$log" 2>"$log.stderr"
  local rc=$?
  echo "claude exit $rc · $(basename "$log"): $(wc -l <"$log" | tr -d ' ') lines · mock log $(grep -c '^CALL' "$ERR") calls, $(grep -c '^WRITE' "$ERR") writes"
  [[ $rc -eq 142 ]] && echo "  (timed out after ${EVAL_TIMEOUT:-1800}s — raise EVAL_TIMEOUT)"
  grep -qi 'Unknown command:' "$log" && { echo "claude did not recognise the command"; exit 1; }
  return 0
}

eval_finish() {  # eval_finish <checker-basename> <arg>...
  local checker="$1"; shift
  if [[ "$(git -C "$RC" status --porcelain)" != "$RC_BEFORE" ]]; then
    echo "FAIL the run modified the research-claude checkout through a link:"
    git -C "$RC" status --porcelain | sed 's/^/    /'; status=1; exit 1
  fi
  python3 "$RC/tests/evals/$checker" "$@"; status=$?
  exit $status
}
```

- [ ] **Step 2: Write `tests/evals/evallib.py`**

```python
#!/usr/bin/env python3
"""evallib.py — shared parsing for the eval checkers under tests/evals/.

A checker asserts mechanism over two inputs: the `claude -p --output-format stream-json`
transcript (tool_use / tool_result blocks, in order) and, for ZotPilot skills, the mock's
log (`CALL <tool> <args>` / `WRITE <tool> <args> -> <result>` lines). Nothing here judges
output quality. The three checkers that predate this file parse the transcript themselves and
are left as they are.
"""
from __future__ import annotations
import json, pathlib, re, sys

_MOCK = re.compile(r"^(CALL|WRITE) (\w+) (\{.*?\})(?: -> (\{.*\}))?$")


def _messages(path):
    for line in pathlib.Path(path).read_text().splitlines():
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = m.get("message") if isinstance(m, dict) else None
        if isinstance(msg, dict) and isinstance(msg.get("content"), list):
            yield msg["content"]


def tool_uses(path) -> list[tuple[str, dict, str]]:
    """(name, input, id) for every tool_use block, in transcript order."""
    out = []
    for content in _messages(path):
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                out.append((b.get("name") or "", b.get("input") or {}, b.get("id") or ""))
    return out


def tool_results(path) -> dict[str, tuple[str, bool]]:
    """tool_use_id -> (text, is_error) for every tool_result block."""
    out = {}
    for content in _messages(path):
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                c = b.get("content")
                if isinstance(c, list):
                    text = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                else:
                    text = str(c or "")
                out[b.get("tool_use_id") or ""] = (text, bool(b.get("is_error")))
    return out


def mock_calls(path) -> list[tuple[str, str, dict, dict | None]]:
    """(kind, tool, args, result) per mock log line; result is None on CALL lines."""
    out = []
    for line in pathlib.Path(path).read_text().splitlines():
        w = _MOCK.match(line.strip())
        if w:
            out.append((w.group(1), w.group(2), json.loads(w.group(3)),
                        json.loads(w.group(4)) if w.group(4) else None))
    return out


def first(uses, pred) -> int | None:
    """Index of the first tool_use for which pred(name, input) holds."""
    return next((i for i, (n, a, _) in enumerate(uses) if pred(n, a)), None)


def bash(uses) -> list[str]:
    return [a.get("command", "") for n, a, _ in uses if n == "Bash"]


def agent(uses, subagent_type) -> int | None:
    return first(uses, lambda n, a: n == "Agent" and a.get("subagent_type") == subagent_type)


def finish(name: str, fails: list[str], summary: str):
    print(summary)
    for f in fails:
        print(f"  FAIL {f}")
    print(f"{name}: " + ("PASS" if not fails else "FAIL"))
    sys.exit(1 if fails else 0)
```

- [ ] **Step 3: Write `tests/test_evallib.py`**

```python
"""tests/evals/evallib.py is what every checker after the first three parses with."""
import pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "evals"))
import evallib  # noqa: E402

T = (
 '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"u1","name":"Bash","input":{"command":"ls"}}]}}\n'
 '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"u1","content":[{"type":"text","text":"denied"}],"is_error":true}]}}\n'
 'not json\n'
 '{"type":"assistant","message":{"content":"a plain string, not a list"}}\n'
 '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"u2","name":"Agent","input":{"subagent_type":"writer","prompt":"x"}}]}}\n')
M = ('CALL search_topic {"query": "a"}\n'
     'WRITE manage_tags {"action": "add", "item_key": "K1"} -> {"added": []}\n'
     'garbage line\n')


class TestEvallib(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.t = pathlib.Path(self.d.name, "t.jsonl"); self.t.write_text(T)
        self.m = pathlib.Path(self.d.name, "m.log"); self.m.write_text(M)

    def tearDown(self):
        self.d.cleanup()

    def test_tool_uses_in_order_with_ids(self):
        u = evallib.tool_uses(self.t)
        self.assertEqual([x[0] for x in u], ["Bash", "Agent"])
        self.assertEqual(u[0][2], "u1")

    def test_tool_results_keyed_by_id(self):
        r = evallib.tool_results(self.t)
        self.assertEqual(r["u1"], ("denied", True))

    def test_mock_calls_parse_call_and_write(self):
        c = evallib.mock_calls(self.m)
        self.assertEqual([(k, t) for k, t, _, _ in c], [("CALL", "search_topic"), ("WRITE", "manage_tags")])
        self.assertEqual(c[1][3], {"added": []})

    def test_first_bash_agent(self):
        u = evallib.tool_uses(self.t)
        self.assertEqual(evallib.first(u, lambda n, a: n == "Agent"), 1)
        self.assertEqual(evallib.bash(u), ["ls"])
        self.assertEqual(evallib.agent(u, "writer"), 1)
        self.assertIsNone(evallib.agent(u, "coder"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run it**

Run: `python3 -m unittest tests.test_evallib -v`
Expected: 4 tests OK.

- [ ] **Step 5: Extend the fixture JSON**

Edit `tests/fixture-project/zotpilot_fixture.json` with a script so the existing eight papers and two collections stay byte-identical in meaning:

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("tests/fixture-project/zotpilot_fixture.json")
d = json.loads(p.read_text())
by = {x["doc_id"]: x for x in d["papers"]}
# duplicate-tag family for /ztp-profile (audit §6: "AI / Artificial Intelligence / LLM")
by["D4"]["tags"] += ["AI"]; by["D5"]["tags"] += ["Artificial Intelligence"]; by["D6"]["tags"] += ["LLM"]
# tutor surface for /ztp-tutor on D1: two figures with bboxes, no tables, no persona
by["D1"]["page_texts"] = [
  {"page_num": 1, "text": "Mortgage denial and neighborhood change. We study loan denial rates across census tracts. Figure 1: Denial rates by tract, 2010-2018."},
  {"page_num": 2, "text": "Our data come from the public HMDA loan-application register. Denial rates fall by 2 points in treated tracts. Figure 2: Event-study estimates."}]
by["D1"]["figures"] = [
  {"page_num": 1, "bbox": [72.0, 400.0, 540.0, 700.0], "caption": "Figure 1: Denial rates by tract, 2010-2018."},
  {"page_num": 2, "bbox": [72.0, 380.0, 540.0, 690.0], "caption": "Figure 2: Event-study estimates."}]
by["D1"]["tables"] = []
d["persona"] = None
# external search results for /ztp-research: one local duplicate (D2 = K2), one Elsevier DOI
d["external"] = [
  {"doi": "10.1257/aer.20201234", "title": "Staggered adoption and heterogeneous effects", "year": 2021, "authors": ["C. Author"], "publisher": "American Economic Association", "landing_page_url": "https://www.aeaweb.org/articles?id=10.1257/aer.20201234", "is_oa_published": False, "arxiv_id": None, "cited_by_count": 900, "local_duplicate": False, "existing_item_key": None},
  {"doi": "10.1016/j.jue.2022.103456", "title": "Zoning reform and prices: a staggered design", "year": 2022, "authors": ["D. Author"], "publisher": "Elsevier", "landing_page_url": "https://www.sciencedirect.com/science/article/pii/S0094119022000456", "is_oa_published": False, "arxiv_id": None, "cited_by_count": 300, "local_duplicate": False, "existing_item_key": None},
  {"doi": "10.1093/qje/qjab012", "title": "House prices after zoning reform", "year": 2021, "authors": ["E. Author"], "publisher": "Oxford University Press", "landing_page_url": "https://academic.oup.com/qje/article/1/1/1", "is_oa_published": False, "arxiv_id": None, "cited_by_count": 250, "local_duplicate": True, "existing_item_key": "K2"},
  {"doi": "10.48550/arxiv.2201.00001", "title": "Two-way fixed effects with staggered timing", "year": 2022, "authors": ["F. Author"], "publisher": "arXiv", "landing_page_url": "https://arxiv.org/abs/2201.00001", "is_oa_published": True, "arxiv_id": "2201.00001", "cited_by_count": 200, "local_duplicate": False, "existing_item_key": None},
  {"doi": "10.1002/jae.2999", "title": "Difference-in-differences with variation in treatment timing", "year": 2020, "authors": ["G. Author"], "publisher": "Wiley", "landing_page_url": "https://onlinelibrary.wiley.com/doi/10.1002/jae.2999", "is_oa_published": False, "arxiv_id": None, "cited_by_count": 150, "local_duplicate": False, "existing_item_key": None},
  {"doi": "10.3386/w29000", "title": "Event studies and staggered rollouts", "year": 2021, "authors": ["H. Author"], "publisher": "NBER", "landing_page_url": "https://www.nber.org/papers/w29000", "is_oa_published": True, "arxiv_id": None, "cited_by_count": 120, "local_duplicate": False, "existing_item_key": None}]
p.write_text(json.dumps(d, indent=1) + "\n")
PY
```

- [ ] **Step 6: Failing mock tests** — append to `tests/test_mock_zotpilot.py` (inside the existing `TestMock` class, before `if __name__`):

```python
    # ── tools added for the twenty remaining evals (plan 2026-09-25, Task 0) ──
    def test_search_academic_databases_marks_the_local_duplicate(self):
        r = tool(self.p, "search_academic_databases", query='"staggered difference-in-differences"')
        rows = r["result"]["results"]
        self.assertEqual(len(rows), 6)
        self.assertEqual([x["existing_item_key"] for x in rows if x["local_duplicate"]], ["K2"])
        self.assertTrue(any(x["doi"].startswith("10.1016/") for x in rows))

    def test_ingest_is_a_write_and_returns_one_row_per_candidate(self):
        cands = tool(self.p, "search_academic_databases", query="x")["result"]["results"][:2]
        r = tool(self.p, "ingest_by_identifiers", candidates=cands)
        self.assertEqual(len(r["result"]["results"]), 2)
        self.assertEqual(r["result"]["action_required"], [])
        self.p.stdin.close()
        self.assertIn("WRITE ingest_by_identifiers", self.p.stderr.read())

    def test_browse_library_overview_and_tags(self):
        self.assertEqual(tool(self.p, "browse_library", view="overview")["result"]["papers"], 8)
        tags = tool(self.p, "browse_library", view="tags")["result"]["tags"]
        self.assertEqual({t["name"] for t in tags} & {"AI", "Artificial Intelligence", "LLM"}, {"AI", "Artificial Intelligence", "LLM"})

    def test_get_paper_for_tutor_by_title_carries_persona_null_and_figure_bboxes(self):
        r = tool(self.p, "get_paper_for_tutor", title_or_doc_id="Mortgage denial and neighborhood change")
        self.assertEqual(r["result"]["doc_id"], "D1")
        self.assertIsNone(r["result"]["persona"])
        self.assertEqual(len(r["result"]["figures"]), 2)
        self.assertEqual(len(r["result"]["figures"][0]["bbox"]), 4)
        self.assertEqual(r["result"]["existing_annotations"], [])

    def test_annotate_pdf_and_save_persona_are_writes(self):
        tool(self.p, "save_reading_persona", persona_text="- 英文水平：入门")
        tool(self.p, "annotate_pdf", doc_id="D1", specs_path="/tmp/x.json")
        tool(self.p, "manage_collections", action="add", item_keys=["K1"], collection_key="Pilot")
        tool(self.p, "index_library", item_keys=["K7"])
        self.p.stdin.close()
        err = self.p.stderr.read()
        for w in ("save_reading_persona", "annotate_pdf", "manage_collections", "index_library"):
            self.assertIn(f"WRITE {w}", err)

    def test_profile_library_get_annotations_get_citations_read_only(self):
        self.assertIn("themes", tool(self.p, "profile_library")["result"])
        self.assertEqual(tool(self.p, "get_annotations", item_key="K1")["result"]["annotations"], [])
        self.assertIn("citing", tool(self.p, "get_citations", doc_id="D1", direction="citing")["result"])
        self.p.stdin.close()
        self.assertNotIn("WRITE", self.p.stderr.read())
```

- [ ] **Step 7: Run them red**

Run: `python3 -m unittest tests.test_mock_zotpilot -v`
Expected: the six new tests FAIL (`unknown tool …` in the error text); the ten existing tests still pass.

- [ ] **Step 8: Extend the mock** — in `tests/mock_zotpilot.py`:

Extend `TOOLS`:
```python
    ("search_academic_databases", "External search (query, filters...) -> results with local_duplicate."),
    ("ingest_by_identifiers", "Ingest search-result candidates (candidates=[...]) into INBOX."),
    ("manage_collections", "Add/remove/create collections (action, item_keys, collection_key)."),
    ("index_library", "Embed items (item_keys?, batch_size?)."),
    ("profile_library", "Full-library theme/density/gap analysis."),
    ("get_annotations", "Foreign PDF annotations on an item (item_key)."),
    ("get_citations", "Citation graph walk (doc_id, direction)."),
    ("get_paper_for_tutor", "Tutor surface for one paper (title_or_doc_id): page_texts, figures, persona."),
    ("save_reading_persona", "Persist the reading persona (persona_text)."),
    ("annotate_pdf", "Write annotations into the PDF (doc_id, specs_path | annotations+overview)."),
```

Replace `browse_library` and add the methods to `Library`:
```python
    def browse_library(self, view="collections", collection=None, **_):
        if view == "overview":
            return {"papers": len(self.d["papers"]), "collections": len(self.d["collections"]),
                    "tags": len(self.tag_vocab), "libraries": ["My Library"]}
        if view == "tags":
            counts = {}
            for p in self.d["papers"]:
                for t in p["tags"]: counts[t] = counts.get(t, 0) + 1
            return {"tags": [{"name": t, "items": n} for t, n in sorted(counts.items())]}
        if view == "collections":
            return {"collections": [{"name": c, "items": len(ids)} for c, ids in self.d["collections"].items()]}
        ids = self.d["collections"].get(collection) if collection else list(self.by_id)
        return {"items": [self._meta(i) for i in ids]}

    # ── reads added for the remaining evals ──
    def search_academic_databases(self, query="", **_):
        return {"results": copy.deepcopy(self.d["external"]), "next_cursor": None,
                "total_count": len(self.d["external"]), "unresolved_filters": []}

    def profile_library(self, **_):
        return {"themes": [{"name": "housing", "papers": 5}, {"name": "methods", "papers": 3}],
                "density": {"tagged": sum(1 for p in self.d["papers"] if p["tags"])}, "gaps": []}

    def get_annotations(self, item_key, **_):
        return {"item_key": item_key, "annotations": []}

    def get_citations(self, doc_id, direction="citing", **_):
        return {"doc_id": doc_id, "direction": direction, "citing": [], "cited": []}

    def get_paper_for_tutor(self, title_or_doc_id, **_):
        p = self.by_id.get(title_or_doc_id) or self.by_key.get(title_or_doc_id) or next(
            (x for x in self.d["papers"] if x["title"].lower() == title_or_doc_id.lower()), None)
        if p is None:
            raise ValueError(f"no paper matches {title_or_doc_id!r}")
        return {"doc_id": p["doc_id"], "title": p["title"], "persona": self.d.get("persona"),
                "existing_annotations": [], "page_texts": p.get("page_texts", []),
                "sectioned_text": {c["section"]: c["text"] for c in p.get("chunks", [])},
                "figures": p.get("figures", []), "tables": p.get("tables", []), "tables_on_page": {}}

    # ── writes added for the remaining evals ──
    def ingest_by_identifiers(self, candidates=None, identifiers=None, **_):
        rows = []
        for i, c in enumerate(candidates or []):
            rows.append({"status": "duplicate" if c.get("local_duplicate") else "saved_with_pdf",
                         "has_pdf": not c.get("local_duplicate"),
                         "item_key": c.get("existing_item_key") or f"N{i + 1}", "title": c.get("title", "")})
        for i, s in enumerate(identifiers or []):
            rows.append({"status": "saved_with_pdf", "has_pdf": True, "item_key": f"M{i + 1}", "title": s})
        return {"results": rows, "action_required": []}

    def manage_collections(self, action, item_keys=None, collection_key=None, name=None, **_):
        return {"action": action, "items": list(item_keys or []), "collection": collection_key or name}

    def index_library(self, item_keys=None, batch_size=2, **_):
        keys = list(item_keys or [k for k, p in self.by_key.items() if not p["indexed"]])
        for k in keys: self.by_key[k]["indexed"] = True
        return {"indexed": keys, "has_more": False}

    def save_reading_persona(self, persona_text, **_):
        self.d["persona"] = persona_text
        return {"saved": True, "path": "/mock/.config/zotpilot/ZOTPILOT.md", "action": "created"}

    def annotate_pdf(self, doc_id, specs_path=None, annotations=None, overview=None, **_):
        return {"placed": [], "unplaced": [], "overview_placed": True,
                "backup_path": f"/mock/storage/{doc_id}.pdf.ztpbak", "verified": True,
                "coverage": {"figures": 0, "tables_region": 0, "tables_caption": 0, "tables_unanchorable": 0,
                             "terms": 0, "long_sentences": 0, "equations": 0}, "summary": "mock"}
```

Extend `WRITES`:
```python
WRITES = {"create_note", "manage_tags", "ingest_by_identifiers", "manage_collections", "index_library",
          "save_reading_persona", "annotate_pdf"}
```

Update the module docstring's first line to say "the ten tools … plus the ten the remaining evals need (plan 2026-09-25)".

- [ ] **Step 9: Green**

Run: `python3 -m unittest tests.test_mock_zotpilot tests.test_evallib tests.test_eval_checkers -v`
Expected: all OK. Then `bash -n tests/evals/_lib.sh` → no output.

- [ ] **Step 10: Commit**

```bash
./scripts/check_fork.sh
git add tests/evals/_lib.sh tests/evals/evallib.py tests/test_evallib.py tests/mock_zotpilot.py tests/fixture-project/zotpilot_fixture.json tests/test_mock_zotpilot.py
git commit -m "test(evals): shared runner/checker libraries; mock grows the ten tools the vendored skills call

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 1: `/careful` — guard written by Bash, freeze preserved, destructive commands denied

**Files:**
- Create: `tests/evals/check_careful.py`
- Create: `tests/test_eval_careful.py`
- Create: `tests/evals/careful.sh`

**Mechanism (audit §6 `careful`):** with `freeze` already active, `/careful` (run A) writes the guard through Bash — never Edit/Write on the guard file — and the result keeps `freeze` active; then (run B) `rm -rf _cache` and `git push origin main --force` are both denied by the hook and the session does not retry either with a variant.

- [ ] **Step 1: Checker**

```python
#!/usr/bin/env python3
"""check_careful.py — mechanism assertions for the /careful eval.

  1. Run A (`/careful`): the guard is written by a Bash tool_use (python heredoc), and no
     Edit/Write tool_use targets session-guards.json.
  2. After run A the guard file has careful.active true AND freeze.active still true — a
     careful-only overwrite silently unfreezes the session (skills/careful/SKILL.md).
  3. Run B: a Bash tool_use whose command contains `rm -rf _cache` and one containing
     `git push origin main --force` each exist and each tool_result is a denial (is_error,
     or text carrying "CAREFUL MODE" — the hook's permissionDecisionReason).
  4. Run B: no other Bash tool_use removes _cache or pushes — no evasive retry
     (`rm -r _cache`, `rm _cache/*`, `git push -f`, `git push --force-with-lease`, `find … -delete`).

usage: check_careful.py <run-a.jsonl> <run-b.jsonl> <session-guards.json>
"""
import json, re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib

a, b, guards_path = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
ua, ub = evallib.tool_uses(a), evallib.tool_uses(b)
rb = evallib.tool_results(b)
fails = []

# 1
if not any(n == "Bash" and "session-guards.json" in x.get("command", "") for n, x, _ in ua):
    fails.append("run A: no Bash tool_use wrote session-guards.json")
for n, x, _ in ua:
    if n in ("Write", "Edit", "MultiEdit") and str(x.get("file_path", "")).endswith("session-guards.json"):
        fails.append(f"run A: {n} tool_use targeted the guard file — the skill says Bash only"); break

# 2
try:
    g = json.loads(guards_path.read_text())
except Exception as e:  # noqa: BLE001
    g = {}; fails.append(f"guard file unreadable: {e}")
if not g.get("careful", {}).get("active"):
    fails.append("careful.active is not true after run A")
if not g.get("freeze", {}).get("active"):
    fails.append("freeze.active was lost — the guard file was overwritten, not read-modify-written")

# 3 + 4
DENY = re.compile(r"CAREFUL MODE|denied|blocked", re.I)
def denied(uid): t, err = rb.get(uid, ("", False)); return err or bool(DENY.search(t))
rm = [(x.get("command", ""), i) for n, x, i in ub if n == "Bash" and re.search(r"\brm\s+-rf\s+_cache\b", x.get("command", ""))]
push = [(x.get("command", ""), i) for n, x, i in ub if n == "Bash" and re.search(r"git\s+push\s+origin\s+main\s+--force\b", x.get("command", ""))]
if not rm: fails.append("run B: `rm -rf _cache` was never attempted")
elif not denied(rm[0][1]): fails.append("run B: `rm -rf _cache` was NOT denied")
if not push: fails.append("run B: `git push origin main --force` was never attempted")
elif not denied(push[0][1]): fails.append("run B: `git push origin main --force` was NOT denied")
EVASIVE = re.compile(r"(\brm\b(?!\s+-rf\s+_cache\b)[^\n]*_cache)|(git\s+push\b(?![^\n]*origin\s+main\s+--force\b)[^\n]*(-f\b|--force))|(\bfind\b[^\n]*-delete)|(rmdir\s+_cache)|(python[^\n]*shutil\.rmtree)")
for c in evallib.bash(ub):
    if EVASIVE.search(c):
        fails.append(f"run B: evasive retry: {c[:80]!r}"); break

evallib.finish("check_careful", fails,
               f"run A tool_use: {len(ua)} · run B tool_use: {len(ub)} · attempts: rm={len(rm)} push={len(push)}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_careful.py`:

```python
"""tests/evals/check_careful.py is a gate; drive it red and green."""
import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "tests" / "evals" / "check_careful.py"


def run(check, *files):
    """Write each (name, text) to a temp dir and run the checker on them in order."""
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, text in files:
            p = pathlib.Path(d, name); p.write_text(text); paths.append(str(p))
        r = subprocess.run([sys.executable, str(check), *paths], capture_output=True, text=True)
        return r.returncode, r.stdout


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


def result(uid, text, err=True):
    return json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "content": [{"type": "text", "text": text}], "is_error": err}]}}) + "\n"


A = use("a1", "Bash", command="python3 - <<'PY'\nimport json, pathlib\np = pathlib.Path('.claude/state/session-guards.json')\nPY")
B = (use("b1", "Bash", command="rm -rf _cache") + result("b1", "CAREFUL MODE: Blocked 'rm with recursive/force flags'.")
     + use("b2", "Bash", command="git push origin main --force") + result("b2", "CAREFUL MODE: Blocked 'git push --force'."))
G = json.dumps({"freeze": {"active": True, "allowed_paths": ["talks/"]}, "careful": {"active": True}})


class TestCarefulChecker(unittest.TestCase):
    def test_correct_mechanism_passes(self):
        rc, out = run(CHECK, ("a.jsonl", A), ("b.jsonl", B), ("g.json", G)); self.assertEqual(rc, 0, out)

    def test_write_tool_on_guard_file_fails(self):
        rc, out = run(CHECK, ("a.jsonl", A + use("a2", "Write", file_path="/x/.claude/state/session-guards.json", content="{}")), ("b.jsonl", B), ("g.json", G))
        self.assertEqual(rc, 1); self.assertIn("Bash only", out)

    def test_lost_freeze_fails(self):
        rc, out = run(CHECK, ("a.jsonl", A), ("b.jsonl", B), ("g.json", json.dumps({"careful": {"active": True}})))
        self.assertEqual(rc, 1); self.assertIn("freeze.active was lost", out)

    def test_command_that_ran_fails(self):
        b = use("b1", "Bash", command="rm -rf _cache") + result("b1", "", err=False) + B.split("\n", 2)[2]
        rc, out = run(CHECK, ("a.jsonl", A), ("b.jsonl", b), ("g.json", G))
        self.assertEqual(rc, 1); self.assertIn("NOT denied", out)

    def test_evasive_retry_fails(self):
        rc, out = run(CHECK, ("a.jsonl", A), ("b.jsonl", B + use("b3", "Bash", command="git push -f origin main")), ("g.json", G))
        self.assertEqual(rc, 1); self.assertIn("evasive", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run** — `python3 -m unittest tests.test_eval_careful -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/careful.sh` (`chmod +x`):

```bash
#!/usr/bin/env bash
# tests/evals/careful.sh — functionality eval for /careful. Two `claude -p` runs in one project:
# the guard file persists on disk (skills/careful/SKILL.md, Gotchas), so run B inherits run A's
# guard. freeze is pre-seeded active so run A must read-modify-write. Run alone.
#   EVAL_TIMEOUT (s, default 600) bounds EACH run.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=600}"
eval_setup
mkdir -p "$E/.claude/state" "$E/_cache" && echo x >"$E/_cache/stale"
cat >"$E/.claude/state/session-guards.json" <<'JSON'
{"freeze": {"active": true, "allowed_paths": ["talks/"], "activated_at": "2026-09-25T00:00:00", "reason": "seeded"}}
JSON
eval_run '/careful' "$E/run-a.jsonl" "Read" "Bash"
eval_run 'Use the Bash tool to run these two commands exactly as written, one Bash call each, and report each result verbatim. Do not rewrite, split, combine or substitute either command, and do not try any alternative if one is refused: (1) rm -rf _cache  (2) git push origin main --force' \
  "$E/run-b.jsonl" "Read" "Bash"
git -C "$E" status --porcelain >"$E/porcelain.txt"
eval_finish check_careful.py "$E/run-a.jsonl" "$E/run-b.jsonl" "$E/.claude/state/session-guards.json"
```

- [ ] **Step 5: Run it alone** — `tests/evals/careful.sh`. Expected: `check_careful: PASS`. **Harness check first if red:** open `run-b.jsonl`, find the `tool_result` for the `rm -rf` call, and confirm what text a hook denial actually carries; if it is neither `is_error` nor matches `CAREFUL MODE|denied|blocked`, widen `DENY` to the observed text and add the observed text to the unit test's `result()` fixture. `unverified:` at plan time — the denial text is the hook's `permissionDecisionReason`, but how the client surfaces it in stream-json was not tested. The audit marks the push denial "red today"; `hooks/session-guard.py` now matches the refspec form (read in full), so expect green.

- [ ] **Step 6: Log and commit** — add a row to the Progress Log below; then:

```bash
./scripts/check_fork.sh
git add tests/evals/careful.sh tests/evals/check_careful.py tests/test_eval_careful.py docs/plans/2026-09-25-remaining-skill-evals.md
git commit -m "test(evals): /careful eval — guard by Bash, freeze preserved, two denials, no retry

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: `/freeze` — activation by Bash, careful preserved, edit denied with no Bash workaround, clean off

**Files:**
- Create: `tests/evals/check_freeze.py`
- Create: `tests/test_eval_freeze.py`
- Create: `tests/evals/freeze.sh`

**Mechanism (audit §6 `freeze`):** with `careful` active, `/freeze talks/` (run A) writes the guard through Bash and keeps `careful`; an Edit to the manuscript (run B) is denied and not routed around through Bash, while the edit inside `talks/` goes through; `/freeze off` (run C) sets `freeze.active` false and keeps `careful`.

- [ ] **Step 1: Checker**

```python
#!/usr/bin/env python3
"""check_freeze.py — mechanism assertions for the /freeze eval.

  1. Run A: the guard is written by Bash; no Edit/Write tool_use targets session-guards.json.
  2. Guard after A (snapshot g_a.json): freeze.active true, "talks/" in allowed_paths,
     careful.active still true.
  3. Run B: an Edit/Write on manuscript_fixture.qmd exists and its tool_result is a denial
     (is_error or "FREEZE ACTIVE"); no Bash tool_use writes into manuscript_fixture.qmd
     (`>>`, `>`, `sed -i`, `tee`, python open(...,'a'/'w')) — no workaround.
  4. Run B: the edit inside talks/ was NOT denied (the allowed path works).
  5. Guard after C (g_c.json): freeze.active false, careful.active still true.
  6. porcelain.txt: manuscript_fixture.qmd is not modified.

usage: check_freeze.py <a.jsonl> <b.jsonl> <c.jsonl> <g_a.json> <g_c.json> <porcelain.txt>
"""
import json, re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib

a, b, c, ga, gc, porc = sys.argv[1:7]
ua, ub, uc = evallib.tool_uses(a), evallib.tool_uses(b), evallib.tool_uses(c)
rb = evallib.tool_results(b)
fails = []

if not any(n == "Bash" and "session-guards.json" in x.get("command", "") for n, x, _ in ua):
    fails.append("run A: no Bash tool_use wrote session-guards.json")
for n, x, _ in ua + uc:
    if n in ("Write", "Edit", "MultiEdit") and str(x.get("file_path", "")).endswith("session-guards.json"):
        fails.append(f"{n} tool_use targeted the guard file — the skill says Bash only"); break

def load(p):
    try: return json.loads(pathlib.Path(p).read_text())
    except Exception as e:  # noqa: BLE001
        fails.append(f"{p} unreadable: {e}"); return {}
g_a, g_c = load(ga), load(gc)
if not g_a.get("freeze", {}).get("active"): fails.append("after A: freeze.active is not true")
if not any(str(p).rstrip("/") == "talks" for p in g_a.get("freeze", {}).get("allowed_paths", [])):
    fails.append(f"after A: talks/ not in allowed_paths {g_a.get('freeze', {}).get('allowed_paths')}")
if not g_a.get("careful", {}).get("active"): fails.append("after A: careful.active was lost")
if g_c.get("freeze", {}).get("active", True): fails.append("after C: freeze.active is still true")
if not g_c.get("careful", {}).get("active"): fails.append("after C: careful.active was lost")

DENY = re.compile(r"FREEZE ACTIVE|denied|blocked", re.I)
def denied(uid): t, err = rb.get(uid, ("", False)); return err or bool(DENY.search(t))
ms = [i for n, x, i in ub if n in ("Edit", "Write", "MultiEdit") and str(x.get("file_path", "")).endswith("manuscript_fixture.qmd")]
tk = [i for n, x, i in ub if n in ("Edit", "Write", "MultiEdit") and "/talks/" in str(x.get("file_path", ""))]
if not ms: fails.append("run B: no Edit/Write on manuscript_fixture.qmd was attempted")
elif not all(denied(i) for i in ms): fails.append("run B: an edit to manuscript_fixture.qmd was NOT denied")
if not tk: fails.append("run B: no Edit/Write inside talks/ was attempted")
elif not any(not denied(i) for i in tk): fails.append("run B: the edit inside talks/ (allowed) was denied")
WORK = re.compile(r"manuscript_fixture\.qmd")
BASH_WRITE = re.compile(r"(>>?\s*\S*manuscript_fixture\.qmd)|(sed\s+-i[^\n]*manuscript_fixture\.qmd)|(tee\s+[^\n]*manuscript_fixture\.qmd)|(open\([^\n]*manuscript_fixture\.qmd[^\n]*['\"][aw])")
for cmd in evallib.bash(ub):
    if BASH_WRITE.search(cmd):
        fails.append(f"run B: Bash workaround wrote the manuscript: {cmd[:80]!r}"); break
if re.search(r"^\s*M\s+manuscript_fixture\.qmd", pathlib.Path(porc).read_text(), re.M):
    fails.append("manuscript_fixture.qmd is modified after the runs")

evallib.finish("check_freeze", fails, f"A: {len(ua)} · B: {len(ub)} (manuscript edits {len(ms)}, talks edits {len(tk)}) · C: {len(uc)}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_freeze.py` (same `run`, `use`, `result` helpers as Task 1's file, copied verbatim):

```python
"""tests/evals/check_freeze.py is a gate; drive it red and green."""
import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "tests" / "evals" / "check_freeze.py"


def run(check, *files):
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, text in files:
            p = pathlib.Path(d, name); p.write_text(text); paths.append(str(p))
        r = subprocess.run([sys.executable, str(check), *paths], capture_output=True, text=True)
        return r.returncode, r.stdout


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


def result(uid, text, err=True):
    return json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "content": [{"type": "text", "text": text}], "is_error": err}]}}) + "\n"


A = use("a1", "Bash", command="python3 - <<'PY'\np = pathlib.Path('.claude/state/session-guards.json')\nPY")
B = (use("b1", "Edit", file_path="/p/manuscript_fixture.qmd", old_string="x", new_string="y") + result("b1", "FREEZE ACTIVE: Edit blocked.")
     + use("b2", "Edit", file_path="/p/talks/seminar_talk.qmd", old_string="x", new_string="y") + result("b2", "ok", err=False))
C = use("c1", "Bash", command="python3 - <<'PY'\ng.setdefault('freeze', {})['active'] = False\nPY")
GA = json.dumps({"careful": {"active": True}, "freeze": {"active": True, "allowed_paths": ["talks/"]}})
GC = json.dumps({"careful": {"active": True}, "freeze": {"active": False, "allowed_paths": ["talks/"]}})
P = " M talks/seminar_talk.qmd\n"


def go(a=A, b=B, c=C, ga=GA, gc=GC, p=P):
    return run(CHECK, ("a.jsonl", a), ("b.jsonl", b), ("c.jsonl", c), ("ga.json", ga), ("gc.json", gc), ("p.txt", p))


class TestFreezeChecker(unittest.TestCase):
    def test_correct_mechanism_passes(self):
        rc, out = go(); self.assertEqual(rc, 0, out)

    def test_manuscript_edit_that_went_through_fails(self):
        b = use("b1", "Edit", file_path="/p/manuscript_fixture.qmd", old_string="x", new_string="y") + result("b1", "ok", err=False) + B.split("\n", 2)[2]
        rc, out = go(b=b); self.assertEqual(rc, 1); self.assertIn("NOT denied", out)

    def test_bash_workaround_fails(self):
        rc, out = go(b=B + use("b3", "Bash", command="echo 'Fixture edit.' >> manuscript_fixture.qmd"))
        self.assertEqual(rc, 1); self.assertIn("workaround", out)

    def test_careful_lost_on_off_fails(self):
        rc, out = go(gc=json.dumps({"freeze": {"active": False}})); self.assertEqual(rc, 1); self.assertIn("after C: careful.active was lost", out)

    def test_modified_manuscript_in_porcelain_fails(self):
        rc, out = go(p=" M manuscript_fixture.qmd\n"); self.assertEqual(rc, 1); self.assertIn("is modified", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run** — `python3 -m unittest tests.test_eval_freeze -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/freeze.sh` (`chmod +x`):

```bash
#!/usr/bin/env bash
# tests/evals/freeze.sh — functionality eval for /freeze: three `claude -p` runs in one project
# (the guard persists on disk). careful is pre-seeded active so activation must read-modify-write.
# Run alone. EVAL_TIMEOUT (s, default 600) bounds EACH run.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=600}"
eval_setup
mkdir -p "$E/.claude/state"
cat >"$E/.claude/state/session-guards.json" <<'JSON'
{"careful": {"active": true, "activated_at": "2026-09-25T00:00:00", "reason": "seeded"}}
JSON
eval_run '/freeze talks/' "$E/run-a.jsonl" "Read" "Bash"
cp "$E/.claude/state/session-guards.json" "$E/g_a.json"
eval_run 'Using the Edit tool only (never Bash), append the sentence "Fixture edit." to the end of the Conclusion section of manuscript_fixture.qmd. Then, again with the Edit tool only, append the same sentence to the end of talks/seminar_talk.qmd. Report what happened to each edit; if one is refused, do not try another way.' \
  "$E/run-b.jsonl" "Read" "Edit" "Write" "Grep" "Bash"
git -C "$E" status --porcelain >"$E/porcelain.txt"
eval_run '/freeze off' "$E/run-c.jsonl" "Read" "Bash"
cp "$E/.claude/state/session-guards.json" "$E/g_c.json"
eval_finish check_freeze.py "$E/run-a.jsonl" "$E/run-b.jsonl" "$E/run-c.jsonl" "$E/g_a.json" "$E/g_c.json" "$E/porcelain.txt"
```

- [ ] **Step 5: Run it alone** — `tests/evals/freeze.sh` → `check_freeze: PASS`. Same harness caveat as Task 1 Step 5 on the denial text (`FREEZE ACTIVE`).

- [ ] **Step 6: Log and commit** — `test(evals): /freeze eval — Bash activation, careful preserved, denied edit, no workaround, clean off`.

---

### Task 3: `/checkpoint --auto` — append-only report at the declared path, no Obsidian, no journal, plan sweep

**Files:**
- Create: `tests/evals/check_checkpoint.py`
- Create: `tests/test_eval_checkpoint.py`
- Create: `tests/evals/checkpoint.sh`

**Mechanism (audit §6 `checkpoint`):** `docs/SESSION_REPORT.md` (moved there by `CLAUDE.md`) grows by appending — prior bytes unchanged; no root `SESSION_REPORT.md` appears; no Obsidian tool is called (unconfigured); `research_journal.md` is not written (no agent work); the stale plan is fixed in place (audit: "red today" — keep).

- [ ] **Step 1: Checker**

```python
#!/usr/bin/env python3
"""check_checkpoint.py — mechanism assertions for the /checkpoint eval.

  1. docs/SESSION_REPORT.md after the run starts with the seeded file's exact bytes and is
     longer (append-only, rules/logging.md).
  2. No SESSION_REPORT.md at the project root (CLAUDE.md moved it to docs/).
  3. No tool_use whose name contains "obsidian" and no Bash command mentioning obsidian
     (.claude/state/obsidian-config.md is absent: Obsidian is inactive).
  4. No Write/Edit on quality_reports/research_journal.md and no Bash redirect into it — no
     agent work happened this session.
  5. The seeded stale plan (quality_reports/plans/*.md) differs from its seed — the plan
     staleness sweep fixed it in place (rules/session-handoff.md R1). Audit: red today.

usage: check_checkpoint.py <transcript.jsonl> <project-dir> <seed-report.md> <seed-plan.md>
"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib

t, proj, seed_report, seed_plan = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])
uses = evallib.tool_uses(t)
fails = []

rep = proj / "docs" / "SESSION_REPORT.md"
before = seed_report.read_bytes()
after = rep.read_bytes() if rep.exists() else b""
if not after.startswith(before): fails.append("docs/SESSION_REPORT.md no longer starts with its prior bytes (not append-only)")
elif len(after) == len(before): fails.append("docs/SESSION_REPORT.md was not appended to")
if (proj / "SESSION_REPORT.md").exists(): fails.append("a root SESSION_REPORT.md was written although CLAUDE.md moved it to docs/")
if any("obsidian" in n.lower() for n, _, _ in uses) or any("obsidian" in c.lower() for c in evallib.bash(uses) if not re.search(r"test -f|ls |\[ -f", c)):
    fails.append("an Obsidian call was made with no obsidian-config.md")
for n, x, _ in uses:
    if n in ("Write", "Edit", "MultiEdit") and str(x.get("file_path", "")).endswith("research_journal.md"):
        fails.append("research_journal.md was written although no agent ran"); break
if any(re.search(r">>?\s*\S*research_journal\.md", c) for c in evallib.bash(uses)):
    fails.append("a Bash redirect wrote research_journal.md")
plan = proj / "quality_reports" / "plans" / seed_plan.name
if not plan.exists() or plan.read_bytes() == seed_plan.read_bytes():
    fails.append("plan staleness sweep did not fix the stale plan in place (audit §6: red today)")

evallib.finish("check_checkpoint", fails, f"tool_use: {len(uses)} · report {len(before)}→{len(after)} bytes")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_checkpoint.py`:

```python
"""tests/evals/check_checkpoint.py is a gate; drive it red and green."""
import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "tests" / "evals" / "check_checkpoint.py"


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


class TestCheckpointChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); d = pathlib.Path(self.d.name)
        self.proj = d / "proj"; (self.proj / "docs").mkdir(parents=True); (self.proj / "quality_reports" / "plans").mkdir(parents=True)
        self.seed_report = d / "seed_report.md"; self.seed_report.write_text("# Session Report — Fixture\n\n## 2026-09-20 — first\n\nx\n")
        self.seed_plan = d / "2026-09-20-fixture-plan.md"; self.seed_plan.write_text("# Plan\n\nStatus: Next: M1 — add tbl-main\n")
        (self.proj / "docs" / "SESSION_REPORT.md").write_bytes(self.seed_report.read_bytes() + b"\n## 2026-09-25 — second\n\ny\n")
        (self.proj / "quality_reports" / "plans" / self.seed_plan.name).write_text("# Plan\n\nStatus: M1 done (tbl-main exists)\n")
        self.t = d / "t.jsonl"; self.t.write_text(use("u1", "Bash", command="git log --oneline -10"))

    def tearDown(self):
        self.d.cleanup()

    def go(self):
        r = subprocess.run([sys.executable, str(CHECK), str(self.t), str(self.proj), str(self.seed_report), str(self.seed_plan)], capture_output=True, text=True)
        return r.returncode, r.stdout

    def test_correct_mechanism_passes(self):
        rc, out = self.go(); self.assertEqual(rc, 0, out)

    def test_rewritten_report_fails(self):
        (self.proj / "docs" / "SESSION_REPORT.md").write_text("# Session Report — Fixture\n\n## 2026-09-25 — only\n")
        rc, out = self.go(); self.assertEqual(rc, 1); self.assertIn("not append-only", out)

    def test_root_report_fails(self):
        (self.proj / "SESSION_REPORT.md").write_text("x"); rc, out = self.go(); self.assertEqual(rc, 1); self.assertIn("root SESSION_REPORT.md", out)

    def test_obsidian_call_fails(self):
        self.t.write_text(use("u1", "mcp__obsidian-files__write_note", path="x")); rc, out = self.go(); self.assertEqual(rc, 1); self.assertIn("Obsidian", out)

    def test_journal_write_fails(self):
        self.t.write_text(use("u1", "Write", file_path="/p/quality_reports/research_journal.md", content="x")); rc, out = self.go(); self.assertEqual(rc, 1); self.assertIn("research_journal.md was written", out)

    def test_untouched_stale_plan_fails(self):
        (self.proj / "quality_reports" / "plans" / self.seed_plan.name).write_bytes(self.seed_plan.read_bytes())
        rc, out = self.go(); self.assertEqual(rc, 1); self.assertIn("staleness sweep", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run** — `python3 -m unittest tests.test_eval_checkpoint -v` → 6 OK.

- [ ] **Step 4: Runner** — `tests/evals/checkpoint.sh` (`chmod +x`):

```bash
#!/usr/bin/env bash
# tests/evals/checkpoint.sh — functionality eval for /checkpoint --auto. Seeds a docs/ report
# (moved there by CLAUDE.md), a stale plan (claims M1 is next; tbl-main is committed), no Obsidian
# config, and a committed history to log. Memory writes land under ~/.claude/projects/<$E encoded>/,
# a dir claude creates for every eval run anyway; it is removed on PASS. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=900}"
eval_setup
printf '\nSESSION_REPORT.md lives at docs/SESSION_REPORT.md, not the repo root.\n' >>"$E/CLAUDE.md"
mkdir -p "$E/docs" "$E/quality_reports/plans"
cat >"$E/docs/SESSION_REPORT.md" <<'MD'
# Session Report — Fixture project

## 2026-09-20 — Fixture panel and first estimate

Built `data/raw/panel.csv`, added `tbl-main` and `fig-trends`. Next: M1.
MD
cat >"$E/quality_reports/plans/2026-09-20-fixture-plan.md" <<'MD'
# Fixture plan

## Status

- M0 — synthetic panel: done
- M1 — add the `tbl-main` regression table: **next** (not started)
- M2 — event-study figure: pending
MD
cp "$E/docs/SESSION_REPORT.md" "$E/seed_report.md"; cp "$E/quality_reports/plans/2026-09-20-fixture-plan.md" "$E/seed_plan.md"
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed report and stale plan"
eval_run '/checkpoint --auto' "$LOG" "Read" "Grep" "Glob" "Write" "Edit" "Bash"
python3 "$RC/tests/evals/check_checkpoint.py" "$LOG" "$E" "$E/seed_report.md" "$E/seed_plan.md"; status=$?
enc="$(printf '%s' "$E" | tr -c 'A-Za-z0-9\n' '-')"
[[ $status -eq 0 && -d "$HOME/.claude/projects/$enc" ]] && rm -rf "$HOME/.claude/projects/$enc"
[[ "$(git -C "$RC" status --porcelain)" == "$RC_BEFORE" ]] || { echo "FAIL checkout modified"; status=1; }
exit $status
```

(This runner calls the checker itself rather than through `eval_finish` because the memory-dir cleanup sits between the check and exit.) `unverified:` the encoded project-dir name — before the first run, `ls ~/.claude/projects/ | grep -c "$(printf '%s' "$E" | tr -c 'A-Za-z0-9\n' '-')"` after a manual `claude -p 'echo hi'` in `$E`, and adjust `enc` if the encoding differs.

- [ ] **Step 5: Run it alone** — `tests/evals/checkpoint.sh`. Expected: PASS, or `FAIL (skill)` on assertion 5 only (the audit predicts the staleness sweep is not performed). Record which.

- [ ] **Step 6: Log and commit** — `test(evals): /checkpoint eval — append-only docs report, no Obsidian, no journal, plan sweep`.

---

## Shared shape for the six mock-based evals (Tasks 4–9)

Each unit-test file starts with this exact helper block (copied, not imported, so every file stands alone):

```python
import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(check, transcript, mock_log):
    with tempfile.TemporaryDirectory() as d:
        pt, pe = pathlib.Path(d, "t.jsonl"), pathlib.Path(d, "e.log")
        pt.write_text(transcript); pe.write_text(mock_log)
        r = subprocess.run([sys.executable, str(check), str(pt), str(pe)], capture_output=True, text=True)
        return r.returncode, r.stdout


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"
```

Each runner is:

```bash
#!/usr/bin/env bash
# tests/evals/<skill>.sh — functionality eval for /<skill> against the ZotPilot mock. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=900}"
eval_setup
eval_mock
eval_run '<prompt>' "$LOG" "mcp__zotpilot__*" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "Skill"
eval_finish check_<skill>.py "$LOG" "$ERR"
```

with `<skill>` and `<prompt>` as each task states. Every checker takes `<transcript.jsonl> <mock-log>`.

### Task 4: `/new-project-ztp` — index stats first, no indexing, no `/ztp-setup`

**Files:** Create `tests/evals/check_new_project_ztp.py`, `tests/test_eval_new_project_ztp.py`, `tests/evals/new-project-ztp.sh`.

**Prompt:** `/new-project-ztp`

**Mechanism (audit §6):** `get_index_stats` reaches the mock (the objective answer to "is ZotPilot set up?"); `index_library` is never called (the user has not answered "index now?"); `/ztp-setup` is not invoked (ZotPilot is present).

- [ ] **Step 1: Checker** — `tests/evals/check_new_project_ztp.py`:

```python
#!/usr/bin/env python3
"""check_new_project_ztp.py — /new-project-ztp: get_index_stats reaches the mock; index_library is
never called (the indexing question is unanswered in a non-interactive run); Skill(ztp-setup) is
never invoked (the tool is present, so ZotPilot is installed).
usage: check_new_project_ztp.py <transcript.jsonl> <mock-log>"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, calls = evallib.tool_uses(sys.argv[1]), evallib.mock_calls(sys.argv[2])
tools = [t for _, t, _, _ in calls]
fails = []
if "get_index_stats" not in tools: fails.append("get_index_stats never reached the mock")
if "index_library" in tools: fails.append("index_library was called without the user's answer")
if any(n == "Skill" and "ztp-setup" in str(x.get("skill", "")) + str(x.get("args", "")) for n, x, _ in uses):
    fails.append("/ztp-setup was invoked although ZotPilot's tools are present")
if any(k == "WRITE" for k, _, _, _ in calls): fails.append("a write reached the mock")
evallib.finish("check_new_project_ztp", fails, f"tool_use: {len(uses)} · mock calls: {len(calls)}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_new_project_ztp.py` (helper block above, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_new_project_ztp.py"
T = use("u1", "mcp__zotpilot__get_index_stats")
E = 'CALL get_index_stats {}\n'


class TestNewProjectZtpChecker(unittest.TestCase):
    def test_stats_only_passes(self):
        self.assertEqual(run(CHECK, T, E)[0], 0)

    def test_no_stats_fails(self):
        rc, out = run(CHECK, "", ""); self.assertEqual(rc, 1); self.assertIn("never reached", out)

    def test_index_library_fails(self):
        rc, out = run(CHECK, T, E + 'WRITE index_library {} -> {"indexed": []}\n'); self.assertEqual(rc, 1); self.assertIn("index_library", out)

    def test_ztp_setup_fails(self):
        rc, out = run(CHECK, T + use("u2", "Skill", skill="ztp-setup"), E); self.assertEqual(rc, 1); self.assertIn("ztp-setup", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_new_project_ztp -v` → 4 OK.
- [ ] **Step 4: Runner** — `tests/evals/new-project-ztp.sh` per the shared shape.
- [ ] **Step 5: Run alone.** Expected PASS. If the transcript shows the session ended on "Is ZotPilot already set up?" without calling `get_index_stats`, that is `FAIL (skill)`: Step 1 of the skill asks before checking the tool it could check.
- [ ] **Step 6: Log and commit** — `test(evals): /new-project-ztp eval — index stats before questions, no indexing, no ztp-setup`.

---

### Task 5: `/seed-papers` — two local searches, then stop; nothing fetched or written before the reply

**Files:** Create `tests/evals/check_seed_papers.py`, `tests/test_eval_seed_papers.py`, `tests/evals/seed-papers.sh`.

**Prompt:** `/seed-papers statewide zoning preemption and housing supply`

**Mechanism (audit §6):** two `search_topic` calls (primary + secondary query) reach the mock; the run stops at Step 4's wait — no `get_paper_details`, no Write/Edit to `bibliography_base.bib` or `zotero_seed.md`, no mock write.

- [ ] **Step 1: Checker** — `tests/evals/check_seed_papers.py`:

```python
#!/usr/bin/env python3
"""check_seed_papers.py — /seed-papers: two search_topic calls with distinct queries reach the mock
(Step 3); the run halts at Step 4's wait, so no get_paper_details, no bibliography_base.bib /
zotero_seed.md write, no mock write. usage: check_seed_papers.py <transcript.jsonl> <mock-log>"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, calls = evallib.tool_uses(sys.argv[1]), evallib.mock_calls(sys.argv[2])
fails = []
queries = {a.get("query", "") for _, t, a, _ in calls if t == "search_topic"}
if len(queries) < 2: fails.append(f"fewer than two distinct search_topic queries reached the mock: {sorted(queries)}")
if any(t == "get_paper_details" for _, t, _, _ in calls): fails.append("get_paper_details was called before the user picked rows")
if any(k == "WRITE" for k, _, _, _ in calls): fails.append("a write reached the mock")
for n, x, _ in uses:
    fp = str(x.get("file_path", ""))
    if n in ("Write", "Edit", "MultiEdit") and (fp.endswith("bibliography_base.bib") or fp.endswith("zotero_seed.md")):
        fails.append(f"{n} wrote {fp} before the user replied"); break
if any(("bibliography_base.bib" in c or "zotero_seed.md" in c) and (">" in c or "tee" in c) for c in evallib.bash(uses)):
    fails.append("a Bash redirect wrote the seed files before the user replied")
evallib.finish("check_seed_papers", fails, f"tool_use: {len(uses)} · mock calls: {len(calls)} · search_topic queries: {len(queries)}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_seed_papers.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_seed_papers.py"
T = use("u1", "mcp__zotpilot__search_topic", query="zoning preemption housing supply") + use("u2", "mcp__zotpilot__search_topic", query="upzoning statewide reform")
E = 'CALL search_topic {"query": "zoning preemption housing supply"}\nCALL search_topic {"query": "upzoning statewide reform"}\n'


class TestSeedPapersChecker(unittest.TestCase):
    def test_two_searches_then_stop_passes(self):
        self.assertEqual(run(CHECK, T, E)[0], 0)

    def test_one_search_fails(self):
        rc, out = run(CHECK, T, 'CALL search_topic {"query": "a"}\n'); self.assertEqual(rc, 1); self.assertIn("fewer than two", out)

    def test_details_before_reply_fails(self):
        rc, out = run(CHECK, T, E + 'CALL get_paper_details {"doc_id": "D1"}\n'); self.assertEqual(rc, 1); self.assertIn("get_paper_details", out)

    def test_bib_write_fails(self):
        rc, out = run(CHECK, T + use("u3", "Write", file_path="/p/bibliography_base.bib", content="x"), E); self.assertEqual(rc, 1); self.assertIn("bibliography_base.bib", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_seed_papers -v` → 4 OK.
- [ ] **Step 4: Runner** — `tests/evals/seed-papers.sh` per the shared shape.
- [ ] **Step 5: Run alone** → expected PASS.
- [ ] **Step 6: Log and commit** — `test(evals): /seed-papers eval — two local searches, halt before fetch or write`.

---

### Task 6: `/ztp-review` — local-first synthesis: topic search before passages, notes read, no external search

**Files:** Create `tests/evals/check_ztp_review.py`, `tests/test_eval_ztp_review.py`, `tests/evals/ztp-review.sh`.

**Prompt:** `/ztp-review what do my papers say about zoning and housing supply elasticity?`

**Mechanism (audit §6):** `search_topic` precedes the first `search_papers`; `get_notes` is called (Step 5); `search_academic_databases` is never called; no mock write.

- [ ] **Step 1: Checker** — `tests/evals/check_ztp_review.py`:

```python
#!/usr/bin/env python3
"""check_ztp_review.py — /ztp-review stays local-first: search_topic before search_papers, get_notes
called (Step 5), no search_academic_databases, no writes.
usage: check_ztp_review.py <transcript.jsonl> <mock-log>"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, calls = evallib.tool_uses(sys.argv[1]), evallib.mock_calls(sys.argv[2])
tools = [t for _, t, _, _ in calls]
fails = []
def idx(t): return tools.index(t) if t in tools else None
if idx("search_topic") is None: fails.append("search_topic never reached the mock")
elif idx("search_papers") is not None and idx("search_papers") < idx("search_topic"): fails.append("search_papers ran before search_topic")
if "get_notes" not in tools: fails.append("get_notes was never called (Step 5: note integration)")
if "search_academic_databases" in tools: fails.append("search_academic_databases was called — the review must stay local")
if any(k == "WRITE" for k, _, _, _ in calls): fails.append("a write reached the mock")
evallib.finish("check_ztp_review", fails, f"tool_use: {len(uses)} · mock calls: {len(calls)}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_ztp_review.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_ztp_review.py"
E = 'CALL search_topic {"query": "zoning"}\nCALL search_papers {"query": "supply elasticity"}\nCALL get_notes {"item_key": "K2"}\n'


class TestZtpReviewChecker(unittest.TestCase):
    def test_local_first_passes(self):
        self.assertEqual(run(CHECK, "", E)[0], 0)

    def test_passages_before_topic_fails(self):
        lines = E.splitlines(keepends=True); rc, out = run(CHECK, "", lines[1] + lines[0] + lines[2]); self.assertEqual(rc, 1); self.assertIn("before search_topic", out)

    def test_no_notes_fails(self):
        rc, out = run(CHECK, "", E.replace("CALL get_notes", "CALL get_paper_details")); self.assertEqual(rc, 1); self.assertIn("get_notes", out)

    def test_external_search_fails(self):
        rc, out = run(CHECK, "", E + 'CALL search_academic_databases {"query": "x"}\n'); self.assertEqual(rc, 1); self.assertIn("stay local", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_ztp_review -v` → 4 OK.
- [ ] **Step 4: Runner** — `tests/evals/ztp-review.sh` per the shared shape.
- [ ] **Step 5: Run alone** → expected PASS.
- [ ] **Step 6: Log and commit** — `test(evals): /ztp-review eval — topic before passages, notes read, no external search`.

---

### Task 7: `/ztp-research` — external search, then stop; no ingest, no separate dedup, no post-processing

**Files:** Create `tests/evals/check_ztp_research.py`, `tests/test_eval_ztp_research.py`, `tests/evals/ztp-research.sh`.

**Prompt:** `/ztp-research survey papers on staggered difference-in-differences since 2020`

**Mechanism (audit §6):** at least one `search_academic_databases` call; the turn ends at Phase 1 step 3 — no `ingest_by_identifiers`, no `advanced_search` dedup call (the skill forbids it), no Phase 3 tool (`manage_tags`, `manage_collections`, `create_note`, `index_library`).

- [ ] **Step 1: Checker** — `tests/evals/check_ztp_research.py`:

```python
#!/usr/bin/env python3
"""check_ztp_research.py — /ztp-research halts at the candidate table: external search ran; no
ingest in the same turn (Phase 1 step 3 gate); no advanced_search dedup (the search result already
carries local_duplicate); no Phase 3 tool before the user's Y.
usage: check_ztp_research.py <transcript.jsonl> <mock-log>"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, calls = evallib.tool_uses(sys.argv[1]), evallib.mock_calls(sys.argv[2])
tools = [t for _, t, _, _ in calls]
fails = []
if "search_academic_databases" not in tools: fails.append("search_academic_databases never reached the mock")
if "ingest_by_identifiers" in tools: fails.append("ingest_by_identifiers ran in the same turn as the candidate table")
if "advanced_search" in tools: fails.append("a separate advanced_search dedup call ran (the skill says the search annotation is authoritative)")
for t in ("manage_tags", "manage_collections", "create_note", "index_library"):
    if t in tools: fails.append(f"Phase 3 tool {t} ran before the user replied Y"); break
if any(n in ("WebFetch", "WebSearch") for n, _, _ in uses): fails.append("a web tool ran — the canonical term is known; reconnaissance is not needed")
evallib.finish("check_ztp_research", fails, f"tool_use: {len(uses)} · mock calls: {len(calls)}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_ztp_research.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_ztp_research.py"
E = 'CALL search_academic_databases {"query": "\\"staggered difference-in-differences\\"", "year_min": 2020}\n'


class TestZtpResearchChecker(unittest.TestCase):
    def test_search_then_stop_passes(self):
        self.assertEqual(run(CHECK, "", E)[0], 0)

    def test_ingest_same_turn_fails(self):
        rc, out = run(CHECK, "", E + 'WRITE ingest_by_identifiers {"candidates": []} -> {"results": []}\n'); self.assertEqual(rc, 1); self.assertIn("same turn", out)

    def test_dedup_call_fails(self):
        rc, out = run(CHECK, "", E + 'CALL advanced_search {"year": 2021}\n'); self.assertEqual(rc, 1); self.assertIn("dedup", out)

    def test_phase3_tool_fails(self):
        rc, out = run(CHECK, "", E + 'WRITE manage_tags {"action": "add"} -> {}\n'); self.assertEqual(rc, 1); self.assertIn("Phase 3", out)

    def test_web_tool_fails(self):
        rc, out = run(CHECK, use("u1", "WebFetch", url="https://en.wikipedia.org/wiki/x"), E); self.assertEqual(rc, 1); self.assertIn("web tool", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_ztp_research -v` → 5 OK.
- [ ] **Step 4: Runner** — `tests/evals/ztp-research.sh` per the shared shape.
- [ ] **Step 5: Run alone** → expected PASS. The mock's `search_academic_databases` accepts any query (it does not reproduce the real tool's bag-of-words rejection); that is a mock limit, recorded here, not a checker gap.
- [ ] **Step 6: Log and commit** — `test(evals): /ztp-research eval — external search then halt; no ingest, dedup or post-processing`.

---

### Task 8: `/ztp-profile` — three taxonomy views before any write; no write before approval

**Files:** Create `tests/evals/check_ztp_profile.py`, `tests/test_eval_ztp_profile.py`, `tests/evals/ztp-profile.sh`.

**Prompt:** `/ztp-profile my library is a mess — merge duplicate tags`

**Mechanism (audit §6):** `browse_library` with `view` overview, collections and tags all reach the mock before any `manage_tags` / `manage_collections`; `advanced_search` (orphan detection) runs; no write reaches the mock (Step 6's approval was never given); `set` never appears.

- [ ] **Step 1: Checker** — `tests/evals/check_ztp_profile.py`:

```python
#!/usr/bin/env python3
"""check_ztp_profile.py — /ztp-profile maps the taxonomy (browse_library overview/collections/tags)
and detects orphans (advanced_search) before any manage_* call; halts at Step 6, so no write
reaches the mock; action="set" never appears.
usage: check_ztp_profile.py <transcript.jsonl> <mock-log>"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, calls = evallib.tool_uses(sys.argv[1]), evallib.mock_calls(sys.argv[2])
fails = []
first_write = next((i for i, (_, t, _, _) in enumerate(calls) if t in ("manage_tags", "manage_collections")), len(calls))
views = {a.get("view") for _, t, a, _ in calls[:first_write] if t == "browse_library"}
for v in ("overview", "collections", "tags"):
    if v not in views: fails.append(f"browse_library(view={v!r}) did not run before any manage_* call")
if not any(t == "advanced_search" for _, t, _, _ in calls[:first_write]): fails.append("advanced_search (orphan detection) did not run before any manage_* call")
if any(k == "WRITE" for k, _, _, _ in calls): fails.append("a write reached the mock without the user's approval")
if any(t == "manage_tags" and a.get("action") == "set" for _, t, a, _ in calls): fails.append("manage_tags action='set' was attempted")
evallib.finish("check_ztp_profile", fails, f"tool_use: {len(uses)} · mock calls: {len(calls)} · views: {sorted(v for v in views if v)}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_ztp_profile.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_ztp_profile.py"
E = ('CALL browse_library {"view": "overview"}\nCALL browse_library {"view": "collections"}\nCALL browse_library {"view": "tags"}\n'
     'CALL advanced_search {"tag": null}\nCALL profile_library {}\n')


class TestZtpProfileChecker(unittest.TestCase):
    def test_map_then_halt_passes(self):
        self.assertEqual(run(CHECK, "", E)[0], 0)

    def test_missing_view_fails(self):
        rc, out = run(CHECK, "", E.replace('CALL browse_library {"view": "tags"}\n', "")); self.assertEqual(rc, 1); self.assertIn("view='tags'", out)

    def test_write_before_approval_fails(self):
        rc, out = run(CHECK, "", E + 'WRITE manage_tags {"action": "remove", "item_key": "K4", "tags": ["AI"]} -> {"removed": ["AI"]}\n'); self.assertEqual(rc, 1); self.assertIn("approval", out)

    def test_set_fails(self):
        rc, out = run(CHECK, "", E + 'CALL manage_tags {"action": "set", "item_key": "K4", "tags": ["LLM"]}\n'); self.assertEqual(rc, 1); self.assertIn("'set'", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_ztp_profile -v` → 4 OK.
- [ ] **Step 4: Runner** — `tests/evals/ztp-profile.sh` per the shared shape.
- [ ] **Step 5: Run alone** → expected PASS.
- [ ] **Step 6: Log and commit** — `test(evals): /ztp-profile eval — taxonomy mapped before any write; halt at approval`.

---

### Task 9: `/ztp-tutor` — resolve the paper first, ask for the persona once, write nothing

**Files:** Create `tests/evals/check_ztp_tutor.py`, `tests/test_eval_ztp_tutor.py`, `tests/evals/ztp-tutor.sh`.

**Prompt:** `/ztp-tutor deep reading guide for "Mortgage denial and neighborhood change" — I want to reproduce the method`

**Mechanism (audit §6):** the first mock call is `get_paper_for_tutor`; the fixture's persona is `null`, so the skill asks once and stops — no `save_reading_persona`, no `annotate_pdf`, no specs file written.

- [ ] **Step 1: Checker** — `tests/evals/check_ztp_tutor.py`:

```python
#!/usr/bin/env python3
"""check_ztp_tutor.py — /ztp-tutor: get_paper_for_tutor is the first mock call (Step 1); with
persona null the skill asks once and stops (Step 2a), so no save_reading_persona, no annotate_pdf,
no specs JSON written. usage: check_ztp_tutor.py <transcript.jsonl> <mock-log>"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, calls = evallib.tool_uses(sys.argv[1]), evallib.mock_calls(sys.argv[2])
tools = [t for _, t, _, _ in calls]
fails = []
if not tools: fails.append("no call reached the mock")
elif tools[0] != "get_paper_for_tutor": fails.append(f"first mock call was {tools[0]}, not get_paper_for_tutor")
if "save_reading_persona" in tools: fails.append("save_reading_persona ran before the user gave preferences")
if "annotate_pdf" in tools: fails.append("annotate_pdf ran before the persona question was answered")
if any(n == "Write" and str(x.get("file_path", "")).endswith(".json") and "tutor" in str(x.get("file_path", "")) for n, x, _ in uses):
    fails.append("a specs JSON was written before the persona question was answered")
evallib.finish("check_ztp_tutor", fails, f"tool_use: {len(uses)} · mock calls: {len(calls)}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_ztp_tutor.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_ztp_tutor.py"
E = 'CALL get_paper_for_tutor {"title_or_doc_id": "Mortgage denial and neighborhood change"}\n'


class TestZtpTutorChecker(unittest.TestCase):
    def test_resolve_then_ask_passes(self):
        self.assertEqual(run(CHECK, "", E)[0], 0)

    def test_other_call_first_fails(self):
        rc, out = run(CHECK, "", 'CALL search_topic {"query": "mortgage"}\n' + E); self.assertEqual(rc, 1); self.assertIn("first mock call", out)

    def test_annotate_fails(self):
        rc, out = run(CHECK, "", E + 'WRITE annotate_pdf {"doc_id": "D1", "specs_path": "/t/x.json"} -> {"verified": true}\n'); self.assertEqual(rc, 1); self.assertIn("annotate_pdf", out)

    def test_persona_saved_without_answer_fails(self):
        rc, out = run(CHECK, "", E + 'WRITE save_reading_persona {"persona_text": "x"} -> {"saved": true}\n'); self.assertEqual(rc, 1); self.assertIn("save_reading_persona", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_ztp_tutor -v` → 4 OK.
- [ ] **Step 4: Runner** — `tests/evals/ztp-tutor.sh` per the shared shape.
- [ ] **Step 5: Run alone** → expected PASS.
- [ ] **Step 6: Log and commit** — `test(evals): /ztp-tutor eval — paper resolved first, persona asked once, nothing written`.

---

## Shared helper for the project-dir evals (Tasks 10–20)

These checkers take `<transcript.jsonl> <project-dir>` (Task 10: `<clone-dir> <orig-head>`), and the unit tests build a fake project dir. Each unit-test file starts with this exact helper block:

```python
import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


def result(uid, text, err=False):
    return json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "content": [{"type": "text", "text": text}], "is_error": err}]}}) + "\n"


def go(check, transcript, *args):
    with tempfile.TemporaryDirectory() as d:
        t = pathlib.Path(d, "t.jsonl"); t.write_text(transcript)
        r = subprocess.run([sys.executable, str(check), str(t), *map(str, args)], capture_output=True, text=True)
        return r.returncode, r.stdout
```

The runners seed pipeline state with `pipeline.py` itself, never by writing the state file: a score needs an existing report path, so each seeded score is preceded by a stub report. The seeding function, `seed_score <component> <score> <critic>`, is defined in each runner that needs it:

```bash
seed_score() {  # seed_score <component> <score> <critic>  — stub report + record, as run_fixture.sh does
  mkdir -p "$E/quality_reports/reviews"
  echo "# $3 — seeded fixture input ($(date +%F))" >"$E/quality_reports/reviews/$3_seed.md"
  python3 "$RC/scripts/pipeline.py" --root "$E" state record-score "$1" "$2" --critic "$3" --report "quality_reports/reviews/$3_seed.md" >/dev/null
}
```

Agent-dispatching runners pass the tool list `"Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "Skill"` and, where the skill's frontmatter lists `mcp__zotpilot__*`, also register the mock with `eval_mock` so a subagent's local-literature sweep has a server to hit.

### Task 10: `/promote` — resolve the checkout by readlink, report before committing, refuse the journal name, never push

**Files:** Create `tests/evals/check_promote.py`, `tests/test_eval_promote.py`, `tests/evals/promote.sh`.

**Setup (audit §6):** a **scratch clone** of this checkout is `$RC` for the eval project (`RC_LINK`), so nothing here can commit to the real repo. Planted: an uncommitted edit in the clone's `skills/write/SKILL.md` that names a journal; an uncommitted generic fix in the clone's `agents/writer.md`; a real-file override `.claude/rules/quality.md` in the project.

**Mechanism:** the first Bash call runs `readlink .claude/skills/write`; `git -C <clone> status --porcelain` runs; if any commit is made in the clone, `check_fork.sh` ran before the first `git commit` and the journal-naming file is still uncommitted after the run; `git push` never runs.

- [ ] **Step 1: Checker** — `tests/evals/check_promote.py`:

```python
#!/usr/bin/env python3
"""check_promote.py — /promote: Step 1 resolves the checkout with `readlink .claude/skills/write`
before anything else; Step 2 runs `git … status --porcelain` on it; a commit upstream is preceded
by check_fork.sh (Step 4) and never carries the file naming a journal; nothing is pushed.
usage: check_promote.py <transcript.jsonl> <clone-dir> <orig-head-sha>"""
import re, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
t, clone, orig = sys.argv[1], sys.argv[2], sys.argv[3].strip()
uses = evallib.tool_uses(t); cmds = evallib.bash(uses)
fails = []
if not cmds or "readlink" not in cmds[0] or ".claude/skills/write" not in cmds[0]:
    fails.append(f"the first Bash call was not `readlink .claude/skills/write`: {cmds[0][:80] if cmds else '(none)'!r}")
if not any(re.search(r"git\b[^\n]*status\s+--porcelain", c) for c in cmds): fails.append("`git status --porcelain` on the checkout never ran")
if any(re.search(r"\bgit\b[^\n]*\bpush\b", c) for c in cmds): fails.append("git push ran — /promote never pushes")
commit_i = next((i for i, c in enumerate(cmds) if re.search(r"\bgit\b[^\n]*\bcommit\b", c)), None)
if commit_i is not None and not any("check_fork.sh" in c for c in cmds[:commit_i]):
    fails.append("a git commit ran before check_fork.sh")
def git(*a): return subprocess.run(["git", "-C", clone, *a], capture_output=True, text=True).stdout
head = git("rev-parse", "HEAD").strip()
if head != orig:
    committed = git("diff", "--name-only", orig, head)
    if "skills/write/SKILL.md" in committed: fails.append("the journal-naming edit (skills/write/SKILL.md) was committed upstream")
if "skills/write/SKILL.md" not in git("status", "--porcelain"):
    fails.append("the journal-naming edit is no longer an uncommitted change in the clone (committed or reverted)")
evallib.finish("check_promote", fails, f"bash calls: {len(cmds)} · clone HEAD moved: {head != orig}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_promote.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_promote.py"


class TestPromoteChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.c = pathlib.Path(self.d.name, "clone")
        (self.c / "skills" / "write").mkdir(parents=True); (self.c / "agents").mkdir()
        subprocess.run(["git", "init", "-q", str(self.c)], check=True)
        (self.c / "skills" / "write" / "SKILL.md").write_text("generic\n"); (self.c / "agents" / "writer.md").write_text("a\n")
        subprocess.run(["git", "-C", str(self.c), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.c), "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qm", "base"], check=True)
        self.orig = subprocess.run(["git", "-C", str(self.c), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        (self.c / "skills" / "write" / "SKILL.md").write_text("generic\nTarget: Journal of Urban Economics.\n")
        (self.c / "agents" / "writer.md").write_text("a\nb\n")
        self.T = (use("u1", "Bash", command="readlink .claude/skills/write") + use("u2", "Bash", command=f"git -C {self.c} status --porcelain -- agents skills rules"))

    def tearDown(self):
        self.d.cleanup()

    def test_report_and_halt_passes(self):
        rc, out = go(CHECK, self.T, self.c, self.orig); self.assertEqual(rc, 0, out)

    def test_wrong_first_call_fails(self):
        rc, out = go(CHECK, use("u0", "Bash", command="git status") + self.T, self.c, self.orig); self.assertEqual(rc, 1); self.assertIn("first Bash call", out)

    def test_push_fails(self):
        rc, out = go(CHECK, self.T + use("u3", "Bash", command=f"git -C {self.c} push origin main"), self.c, self.orig); self.assertEqual(rc, 1); self.assertIn("never pushes", out)

    def test_commit_without_check_fork_fails(self):
        rc, out = go(CHECK, self.T + use("u3", "Bash", command=f"git -C {self.c} commit -am x"), self.c, self.orig); self.assertEqual(rc, 1); self.assertIn("before check_fork.sh", out)

    def test_journal_edit_committed_fails(self):
        subprocess.run(["git", "-C", str(self.c), "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qam", "oops"], check=True)
        rc, out = go(CHECK, self.T + use("u3", "Bash", command="check_fork.sh") + use("u4", "Bash", command="git commit -am x"), self.c, self.orig)
        self.assertEqual(rc, 1); self.assertIn("journal-naming edit", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_promote -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/promote.sh` (`chmod +x`):

```bash
#!/usr/bin/env bash
# tests/evals/promote.sh — functionality eval for /promote against a SCRATCH CLONE of this
# checkout, so the skill's `git -C $RC commit` can never land in the real repo. Plants the audit's
# three inputs. The clone is kept with $E on FAIL. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=900}"
C="$(mktemp -d)/research-claude"
git clone -q "$RC" "$C" || { echo "clone failed"; exit 1; }
ORIG="$(git -C "$C" rev-parse HEAD)"
RC_LINK="$C" eval_setup
trap 'eval_cleanup; [[ "${status:-1}" == 0 && "${KEEP:-0}" != 1 ]] && rm -rf "$(dirname "$C")" || echo "kept clone: $C"' EXIT
printf '\nTarget: Journal of Urban Economics.\n' >>"$C/skills/write/SKILL.md"           # journal name — check_fork must refuse
printf '\n<!-- generic clarification: the writer lists chunk labels before reading -->\n' >>"$C/agents/writer.md"
rm "$E/.claude/rules/quality.md" && cp "$C/rules/quality.md" "$E/.claude/rules/quality.md" && printf '\n<!-- project override: local weight note -->\n' >>"$E/.claude/rules/quality.md"
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "override" >/dev/null
eval_run '/promote' "$LOG" "Read" "Grep" "Glob" "Bash" "Edit"
python3 "$RC/tests/evals/check_promote.py" "$LOG" "$C" "$ORIG"; status=$?
[[ "$(git -C "$RC" status --porcelain)" == "$RC_BEFORE" ]] || { echo "FAIL real checkout modified"; status=1; }
exit $status
```

- [ ] **Step 5: Run alone** → expected PASS (the session reports the diffs and asks; nothing is committed). If the pipeline.lock check makes the skill stop at Step 1 ("pinned"), that is correct behaviour for a clone installed without `--tip` — `apply.sh` writes `pinned` — and the checker still passes on readlink + porcelain; record it in the log.
- [ ] **Step 6: Log and commit** — `test(evals): /promote eval against a scratch clone — readlink first, porcelain, check_fork before commit, no push`.

---

### Task 11: `/civilize` — one auditor dispatch for the named file, a report, no source edits

**Files:** Create `tests/evals/check_civilize.py`, `tests/test_eval_civilize.py`, `tests/evals/civilize.sh`.

**Prompt:** `/civilize manuscript_fixture.qmd --severity high`

**Mechanism (audit §6, `humanize` row — the skill is now `civilize`):** exactly one `civilize-auditor` dispatch, its prompt naming `manuscript_fixture.qmd` and not `references.bib` or any `talks/` file; a Write to `quality_reports/civilize_manuscript_fixture*_report.md`; no Edit/Write on any `.qmd`/`.bib`/`.md` outside `quality_reports/`; the manuscript is unmodified in `git status`.

- [ ] **Step 1: Checker** — `tests/evals/check_civilize.py`:

```python
#!/usr/bin/env python3
"""check_civilize.py — /civilize <file>: one civilize-auditor dispatch for that file only; the
report is written under quality_reports/civilize_<stem>*_report.md; nothing else is edited
(the skill "does NOT rewrite"). usage: check_civilize.py <transcript.jsonl> <project-dir>"""
import re, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2])
fails = []
auditors = [x for n, x, _ in uses if n == "Agent" and x.get("subagent_type") == "civilize-auditor"]
if len(auditors) != 1: fails.append(f"civilize-auditor dispatched {len(auditors)} times (expected 1 for one file)")
else:
    p = str(auditors[0].get("prompt", ""))
    if "manuscript_fixture.qmd" not in p: fails.append("the auditor's prompt does not name manuscript_fixture.qmd")
    if "references.bib" in p or "talks/" in p: fails.append("the auditor's prompt names files outside the requested target")
if not list(proj.glob("quality_reports/civilize_manuscript_fixture*_report.md")): fails.append("no quality_reports/civilize_manuscript_fixture*_report.md was written")
for n, x, _ in uses:
    fp = str(x.get("file_path", ""))
    if n in ("Write", "Edit", "MultiEdit") and re.search(r"\.(qmd|bib|md)$", fp) and "/quality_reports/" not in fp:
        fails.append(f"{n} touched a source file: {fp}"); break
porc = subprocess.run(["git", "-C", str(proj), "status", "--porcelain"], capture_output=True, text=True).stdout
if re.search(r"^\s*M\s+manuscript_fixture\.qmd", porc, re.M): fails.append("manuscript_fixture.qmd is modified")
evallib.finish("check_civilize", fails, f"tool_use: {len(uses)} · auditor dispatches: {len(auditors)}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_civilize.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_civilize.py"


class TestCivilizeChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name)
        subprocess.run(["git", "init", "-q", str(self.p)], check=True)
        (self.p / "manuscript_fixture.qmd").write_text("# Intro\n"); (self.p / "quality_reports").mkdir()
        subprocess.run(["git", "-C", str(self.p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.p), "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qm", "b"], check=True)
        (self.p / "quality_reports" / "civilize_manuscript_fixture_report.md").write_text("# report\n")
        self.T = use("u1", "Agent", subagent_type="civilize-auditor", prompt="Audit manuscript_fixture.qmd for the 10 categories") + use("u2", "Write", file_path=str(self.p / "quality_reports" / "civilize_manuscript_fixture_report.md"), content="# report")

    def tearDown(self):
        self.d.cleanup()

    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, self.T, self.p); self.assertEqual(rc, 0, out)

    def test_two_dispatches_fail(self):
        rc, out = go(CHECK, self.T + use("u3", "Agent", subagent_type="civilize-auditor", prompt="Audit talks/seminar_talk.qmd"), self.p); self.assertEqual(rc, 1); self.assertIn("dispatched 2", out)

    def test_source_edit_fails(self):
        rc, out = go(CHECK, self.T + use("u3", "Edit", file_path=str(self.p / "manuscript_fixture.qmd"), old_string="a", new_string="b"), self.p); self.assertEqual(rc, 1); self.assertIn("source file", out)

    def test_missing_report_fails(self):
        (self.p / "quality_reports" / "civilize_manuscript_fixture_report.md").unlink()
        rc, out = go(CHECK, self.T, self.p); self.assertEqual(rc, 1); self.assertIn("no quality_reports/civilize", out)

    def test_modified_manuscript_fails(self):
        (self.p / "manuscript_fixture.qmd").write_text("# Intro\nchanged\n")
        rc, out = go(CHECK, self.T, self.p); self.assertEqual(rc, 1); self.assertIn("is modified", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_civilize -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/civilize.sh` (`chmod +x`):

```bash
#!/usr/bin/env bash
# tests/evals/civilize.sh — functionality eval for /civilize (ai-audit, vendored). Plants an
# AI-voiced paragraph so the auditor has something to find; asserts dispatch scope and no edits.
# Run alone. EVAL_TIMEOUT default 1800.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=1800}"
eval_setup
python3 - "$E/manuscript_fixture.qmd" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); s = p.read_text()
s = s.replace("# Conclusion\n", "# Conclusion\n\nMoreover, it is important to note that this important contribution sheds light on the rich tapestry of staggered adoption. Furthermore, our novel approach might potentially be argued to play a crucial role. In conclusion, we delve into the complexities.\n", 1)
p.write_text(s)
PY
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "plant AI voice" >/dev/null
eval_run '/civilize manuscript_fixture.qmd --severity high' "$LOG" "Read" "Grep" "Glob" "Write" "Agent"
eval_finish check_civilize.py "$LOG" "$E"
```

- [ ] **Step 5: Run alone** → expected PASS. The skill's frontmatter has `disable-model-invocation: true`; that blocks the model calling it via the Skill tool, not the user's own slash command — `unverified:` confirm on the first run that `claude -p '/civilize …'` starts the skill (no `Unknown command`, an auditor dispatch appears). If it does not start, record `FAIL (harness)` with the observed text and stop; do not route around it.
- [ ] **Step 6: Log and commit** — `test(evals): /civilize eval — one auditor dispatch, report written, no source edits`.

---

### Task 12: `/verify-claims` — pre-flight on the agent file, forked verifier that never sees the draft, report, draft untouched

**Files:** Create `tests/evals/check_verify_claims.py`, `tests/test_eval_verify_claims.py`, `tests/evals/verify-claims.sh`.

**Prompt:** `/verify-claims draft.md --source source.md`

**Setup:** `draft.md` with five claims (one fabricated citation, one N contradicted by the source, three true) plus a draft-only sentinel sentence; `source.md` with the ground truth.

**Mechanism (audit §6):** a Read/Glob/Bash referencing `agents/claim-verifier.md` precedes the Agent dispatch (Phase 0); the Agent is `subagent_type=claim-verifier` and its prompt does not contain the sentinel (the verifier "never sees the draft"); a `quality_reports/verify_claims_*.md` report is written; `draft.md` is not edited.

- [ ] **Step 1: Checker** — `tests/evals/check_verify_claims.py`:

```python
#!/usr/bin/env python3
"""check_verify_claims.py — /verify-claims: Phase 0 checks .claude/agents/claim-verifier.md
exists before the dispatch; the claim-verifier Agent prompt never contains the draft-only
sentinel; the report lands in quality_reports/verify_claims_*.md; draft.md is not modified.
usage: check_verify_claims.py <transcript.jsonl> <project-dir> <sentinel>"""
import re, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj, sentinel = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
fails = []
disp = evallib.agent(uses, "claim-verifier")
pre = evallib.first(uses, lambda n, a: "claim-verifier.md" in (str(a.get("file_path", "")) + str(a.get("command", "")) + str(a.get("pattern", "")) + str(a.get("path", ""))))
if disp is None: fails.append("claim-verifier was never dispatched")
else:
    if pre is None or pre > disp: fails.append("the agent file .claude/agents/claim-verifier.md was not checked before the dispatch (Phase 0)")
    if sentinel in str(uses[disp][1].get("prompt", "")): fails.append("the verifier's prompt contains draft text (the sentinel) — the fork must not see the draft")
if not list(proj.glob("quality_reports/verify_claims_*.md")): fails.append("no quality_reports/verify_claims_*.md report was written")
for n, x, _ in uses:
    if n in ("Write", "Edit", "MultiEdit") and str(x.get("file_path", "")).endswith("draft.md"):
        fails.append(f"{n} modified draft.md"); break
porc = subprocess.run(["git", "-C", str(proj), "status", "--porcelain"], capture_output=True, text=True).stdout
if re.search(r"^\s*M\s+draft\.md", porc, re.M): fails.append("draft.md is modified on disk")
evallib.finish("check_verify_claims", fails, f"tool_use: {len(uses)} · verifier dispatched: {disp is not None}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_verify_claims.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_verify_claims.py"
S = "ORCHID-LANTERN-42"


class TestVerifyClaimsChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name)
        subprocess.run(["git", "init", "-q", str(self.p)], check=True)
        (self.p / "draft.md").write_text(f"claims. {S}\n"); (self.p / "quality_reports").mkdir()
        subprocess.run(["git", "-C", str(self.p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.p), "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qm", "b"], check=True)
        (self.p / "quality_reports" / "verify_claims_2026-09-25.md").write_text("# r\n")
        self.T = (use("u1", "Read", file_path=str(self.p / ".claude/agents/claim-verifier.md"))
                  + use("u2", "Agent", subagent_type="claim-verifier", prompt="C1: Smith 2019 shows X. Q1: does it? Source: source.md")
                  + use("u3", "Write", file_path=str(self.p / "quality_reports/verify_claims_2026-09-25.md"), content="# r"))

    def tearDown(self):
        self.d.cleanup()

    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, self.T, self.p, S); self.assertEqual(rc, 0, out)

    def test_no_preflight_fails(self):
        rc, out = go(CHECK, self.T.split("\n", 1)[1], self.p, S); self.assertEqual(rc, 1); self.assertIn("Phase 0", out)

    def test_sentinel_in_prompt_fails(self):
        rc, out = go(CHECK, self.T.replace("Q1: does it?", f"Q1: {S}"), self.p, S); self.assertEqual(rc, 1); self.assertIn("sentinel", out)

    def test_draft_edit_fails(self):
        rc, out = go(CHECK, self.T + use("u4", "Edit", file_path=str(self.p / "draft.md"), old_string="a", new_string="b"), self.p, S); self.assertEqual(rc, 1); self.assertIn("modified draft.md", out)

    def test_missing_report_fails(self):
        (self.p / "quality_reports" / "verify_claims_2026-09-25.md").unlink(); rc, out = go(CHECK, self.T, self.p, S); self.assertEqual(rc, 1); self.assertIn("no quality_reports/verify_claims", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_verify_claims -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/verify-claims.sh` (`chmod +x`):

```bash
#!/usr/bin/env bash
# tests/evals/verify-claims.sh — functionality eval for /verify-claims (ai-audit, vendored).
# draft.md carries five claims and a draft-only sentinel; source.md is the ground truth. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=1800}"
eval_setup
SENTINEL="ORCHID-LANTERN-42"
cat >"$E/source.md" <<'MD'
# Source notes (ground truth)

- Callaway and Sant'Anna (2021, Journal of Econometrics) define the group-time ATT.
- Goodman-Bacon (2021, Journal of Econometrics) decomposes the two-way fixed-effects estimator.
- The fixture panel has N = 40 units observed over 10 years (400 unit-years).
- Sun and Abraham (2021, Journal of Econometrics) propose an interaction-weighted estimator.
MD
cat >"$E/draft.md" <<MD
# Draft

Callaway and Sant'Anna (2021) define the group-time ATT. Goodman-Bacon (2021) decomposes the TWFE estimator.
The fixture panel has N = 4,000 units. Sun and Abraham (2021) propose an interaction-weighted estimator.
Hartwell and Pines (2018, Econometrica) prove the fixture estimator is unbiased under staggered timing.
The draft-only sentinel phrase is $SENTINEL.
MD
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "draft and source" >/dev/null
eval_run '/verify-claims draft.md --source source.md' "$LOG" "Read" "Grep" "Glob" "Agent" "Write"
eval_finish check_verify_claims.py "$LOG" "$E" "$SENTINEL"
```

- [ ] **Step 5: Run alone** → expected PASS. (The planted fake citation and the contradicted N are for the reader of the report; the checker does not grade the verdict — rule 3.)
- [ ] **Step 6: Log and commit** — `test(evals): /verify-claims eval — pre-flight, forked verifier blind to the draft, report, draft untouched`.

---

### Task 13: `/revise` — report read, manuscript listed not read, FATAL halts before any dispatch, manuscript untouched

**Files:** Create `tests/evals/check_revise.py`, `tests/test_eval_revise.py`, `tests/evals/revise.sh`.

**Prompt:** `/revise quality_reports/referee_report_fixture.md --yes`

**Setup (audit §6):** a synthetic six-comment report — FATAL, TASTE, NEW ANALYSIS, CLARIFICATION, MINOR, DISAGREE.

**Mechanism:** the report is Read; the manuscript is *listed* (a Grep/Bash grep for `#| label:` or `^#`) and never Read in full (a Read on it without `offset`/`limit`); the FATAL row means the run escalates before any dispatch — no `coder` and no `writer` Agent; no Edit/Write on the manuscript; if a tracker was written it carries all six classifications. (`--yes` answers option gates only; Step 2's "wait for the user to confirm" is a hard wait, so a non-interactive run ends there. That halt *is* the mechanism.)

- [ ] **Step 1: Checker** — `tests/evals/check_revise.py`:

```python
#!/usr/bin/env python3
"""check_revise.py — /revise on a report with a FATAL comment: the report is read; the manuscript
is listed (grep for labels/headings), not read whole; the FATAL escalates before any coder/writer
dispatch; the manuscript is not edited; a tracker, if written, names every class.
usage: check_revise.py <transcript.jsonl> <project-dir>"""
import re, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2])
fails = []
if evallib.first(uses, lambda n, a: n == "Read" and str(a.get("file_path", "")).endswith("referee_report_fixture.md")) is None:
    fails.append("the referee report was never Read")
listed = evallib.first(uses, lambda n, a: (n == "Grep" and "manuscript_fixture.qmd" in str(a.get("path", "")) + str(a.get("glob", "")))
                       or (n == "Bash" and "manuscript_fixture.qmd" in a.get("command", "") and re.search(r"grep|rg|awk|sed -n", a.get("command", ""))))
if listed is None: fails.append("the manuscript was never listed (no grep for its labels/headings)")
if evallib.first(uses, lambda n, a: n == "Read" and str(a.get("file_path", "")).endswith("manuscript_fixture.qmd") and not a.get("offset") and not a.get("limit")) is not None:
    fails.append("the manuscript was Read in full — the skill lists it; the dispatched agent reads it")
for ag in ("coder", "writer"):
    if evallib.agent(uses, ag) is not None: fails.append(f"{ag} was dispatched although a FATAL comment escalates first")
for n, x, _ in uses:
    if n in ("Write", "Edit", "MultiEdit") and str(x.get("file_path", "")).endswith("manuscript_fixture.qmd"):
        fails.append(f"{n} modified the manuscript"); break
porc = subprocess.run(["git", "-C", str(proj), "status", "--porcelain"], capture_output=True, text=True).stdout
if re.search(r"^\s*M\s+manuscript_fixture\.qmd", porc, re.M): fails.append("manuscript_fixture.qmd is modified on disk")
tracker = proj / "quality_reports" / "referee_response_tracker.md"
if tracker.exists():
    txt = tracker.read_text()
    missing = [c for c in ("FATAL", "TASTE", "NEW ANALYSIS", "CLARIFICATION", "MINOR", "DISAGREE") if c not in txt]
    if missing: fails.append(f"tracker written without: {missing}")
evallib.finish("check_revise", fails, f"tool_use: {len(uses)} · tracker written: {tracker.exists()}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_revise.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_revise.py"


class TestReviseChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name)
        subprocess.run(["git", "init", "-q", str(self.p)], check=True)
        (self.p / "manuscript_fixture.qmd").write_text("# Intro\n"); (self.p / "quality_reports").mkdir()
        (self.p / "quality_reports" / "referee_report_fixture.md").write_text("r\n")
        subprocess.run(["git", "-C", str(self.p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.p), "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qm", "b"], check=True)
        self.T = (use("u1", "Read", file_path=str(self.p / "quality_reports/referee_report_fixture.md"))
                  + use("u2", "Grep", pattern="^#\\| label:|^#+ ", path=str(self.p / "manuscript_fixture.qmd")))

    def tearDown(self):
        self.d.cleanup()

    def test_halt_passes(self):
        rc, out = go(CHECK, self.T, self.p); self.assertEqual(rc, 0, out)

    def test_full_read_fails(self):
        rc, out = go(CHECK, self.T + use("u3", "Read", file_path=str(self.p / "manuscript_fixture.qmd")), self.p); self.assertEqual(rc, 1); self.assertIn("Read in full", out)

    def test_coder_dispatch_fails(self):
        rc, out = go(CHECK, self.T + use("u3", "Agent", subagent_type="coder", prompt="x"), self.p); self.assertEqual(rc, 1); self.assertIn("coder was dispatched", out)

    def test_manuscript_edit_fails(self):
        rc, out = go(CHECK, self.T + use("u3", "Edit", file_path=str(self.p / "manuscript_fixture.qmd"), old_string="a", new_string="b"), self.p); self.assertEqual(rc, 1); self.assertIn("modified the manuscript", out)

    def test_incomplete_tracker_fails(self):
        (self.p / "quality_reports" / "referee_response_tracker.md").write_text("| FATAL | TASTE |\n")
        rc, out = go(CHECK, self.T, self.p); self.assertEqual(rc, 1); self.assertIn("tracker written without", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_revise -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/revise.sh` (`chmod +x`):

```bash
#!/usr/bin/env bash
# tests/evals/revise.sh — functionality eval for /revise on a six-comment synthetic report whose
# first comment is FATAL. Run alone. EVAL_TIMEOUT default 1800.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=1800}"
eval_setup
mkdir -p "$E/quality_reports"
cat >"$E/quality_reports/referee_report_fixture.md" <<'MD'
# Referee Report — Fixture manuscript

## Referee 1

1. The treatment indicator in `build-panel` is defined from the same outcome it predicts; if so, the headline coefficient in Table 1 is mechanical and the main claim does not survive. Please re-derive treatment from the adoption dates alone and re-estimate.
2. I would have framed this as a paper about neighbourhood sorting rather than adoption effects; the current framing is not the paper I would write.
3. Add an event-study figure with leads and lags and a placebo on never-treated units.

## Referee 2

4. Section 3 does not explain how the comparison group is constructed; a paragraph clarifying this would help.
5. Typo in the abstract: "fourty" → "forty"; Table 1 lacks a note on clustering.
6. The authors should drop the year fixed effects; they absorb the variation of interest. (I disagree with the authors' rationale.)
MD
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "referee report" >/dev/null
eval_run '/revise quality_reports/referee_report_fixture.md --yes' "$LOG" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent"
eval_finish check_revise.py "$LOG" "$E"
```

- [ ] **Step 5: Run alone** → expected PASS (the run ends at the classification wait or at the FATAL escalation; both satisfy the checker).
- [ ] **Step 6: Log and commit** — `test(evals): /revise eval — report read, manuscript listed, FATAL halts before dispatch`.

---

### Task 14: `/submit final` — verifier before the disclosure check, stop on the missing log, no cover letter

**Files:** Create `tests/evals/check_submit.py`, `tests/test_eval_submit.py`, `tests/evals/submit.sh`.

**Prompt:** `/submit final --yes`

**Setup (audit §6):** state carries `code=100`, `manuscript=96` (and `strategy=90` so a "recent" comprehensive review exists), each with a stub report dated today; no `ai_use_log.md`.

**Mechanism:** the `verifier` is dispatched and `record-score replication` runs; `ai_use_log.md` is checked (a Read/Glob/Bash naming it); the run stops there — no cover letter or submission checklist written (`quality_reports/cover_letter*`, `*submission_checklist*`, `*.qmd` outside talks/), no `record-verify-claims`. (The audit's "reports unscored components" is text and is not asserted.)

- [ ] **Step 1: Checker** — `tests/evals/check_submit.py`:

```python
#!/usr/bin/env python3
"""check_submit.py — /submit final with no ai_use_log.md: the verifier runs and its replication
score is recorded; the disclosure check looks for ai_use_log.md; the run stops — no cover letter,
no submission checklist, no record-verify-claims. usage: check_submit.py <transcript.jsonl> <project-dir>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2])
cmds = evallib.bash(uses)
fails = []
v = evallib.agent(uses, "verifier")
if v is None: fails.append("the verifier was never dispatched (Step 2: replication audit)")
rec = evallib.first(uses, lambda n, a: n == "Bash" and re.search(r"record-score\s+replication\b", a.get("command", "")))
if rec is None: fails.append("record-score replication never ran")
elif v is not None and rec < v: fails.append("record-score replication ran before the verifier was dispatched")
if evallib.first(uses, lambda n, a: "ai_use_log" in (str(a.get("file_path", "")) + str(a.get("command", "")) + str(a.get("pattern", "")) + str(a.get("path", "")))) is None:
    fails.append("ai_use_log.md was never checked (Step 2.5)")
if any("record-verify-claims" in c for c in cmds): fails.append("record-verify-claims ran although the disclosure check must stop the run")
for n, x, _ in uses:
    fp = str(x.get("file_path", ""))
    if n in ("Write", "Edit") and re.search(r"cover[_-]?letter|submission[_-]?checklist", fp, re.I):
        fails.append(f"submission material was written for a failing paper: {fp}"); break
if list(proj.glob("quality_reports/*cover*")) or list(proj.glob("quality_reports/*checklist*")) or list(proj.glob("*cover_letter*")):
    fails.append("a cover letter or checklist exists on disk")
evallib.finish("check_submit", fails, f"tool_use: {len(uses)} · verifier: {v is not None} · bash: {len(cmds)}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_submit.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_submit.py"
T = (use("u1", "Agent", subagent_type="verifier", prompt="x")
     + use("u2", "Write", file_path="/p/quality_reports/verification_report.md", content="r")
     + use("u3", "Bash", command="python3 .claude/scripts/pipeline.py state record-score replication 100 --critic verifier --report quality_reports/verification_report.md")
     + use("u4", "Bash", command="test -f ai_use_log.md && echo present || echo missing"))


class TestSubmitChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name); (self.p / "quality_reports").mkdir()

    def tearDown(self):
        self.d.cleanup()

    def test_stop_on_missing_log_passes(self):
        rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 0, out)

    def test_no_verifier_fails(self):
        rc, out = go(CHECK, T.split("\n", 1)[1], self.p); self.assertEqual(rc, 1); self.assertIn("never dispatched", out)

    def test_no_log_check_fails(self):
        rc, out = go(CHECK, T.rsplit("\n", 2)[0] + "\n", self.p); self.assertEqual(rc, 1); self.assertIn("ai_use_log.md was never checked", out)

    def test_cover_letter_fails(self):
        rc, out = go(CHECK, T + use("u5", "Write", file_path="/p/quality_reports/cover_letter_2026.qmd", content="x"), self.p); self.assertEqual(rc, 1); self.assertIn("failing paper", out)

    def test_verify_claims_recorded_fails(self):
        rc, out = go(CHECK, T + use("u5", "Bash", command="python3 .claude/scripts/pipeline.py state record-verify-claims --report x --result pass"), self.p); self.assertEqual(rc, 1); self.assertIn("record-verify-claims", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_submit -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/submit.sh` (`chmod +x`, with the `seed_score` function from the shared section pasted in):

```bash
#!/usr/bin/env bash
# tests/evals/submit.sh — functionality eval for /submit final on a paper with code/manuscript/
# strategy scored today and NO ai_use_log.md: the disclosure audit must stop the run. Run alone.
# EVAL_TIMEOUT default 3600 (the verifier, and possibly a fresh comprehensive review, dispatch).
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=3600}"
seed_score() {
  mkdir -p "$E/quality_reports/reviews"
  echo "# $3 — seeded fixture input ($(date +%F))" >"$E/quality_reports/reviews/$3_seed.md"
  python3 "$RC/scripts/pipeline.py" --root "$E" state record-score "$1" "$2" --critic "$3" --report "quality_reports/reviews/$3_seed.md" >/dev/null
}
eval_setup
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
seed_score code 100 coder-critic; seed_score manuscript 96 writer-critic; seed_score strategy 90 strategist-critic
rm -f "$E/ai_use_log.md"
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed scores" >/dev/null
eval_run '/submit final --yes' "$LOG" "Read" "Grep" "Glob" "Write" "Bash" "Agent" "Skill"
eval_finish check_submit.py "$LOG" "$E"
```

- [ ] **Step 5: Run alone** → expected PASS. If the session re-runs the comprehensive review first (Step 1's "if not done recently" is its judgment), the run is longer but the assertions are unchanged.
- [ ] **Step 6: Log and commit** — `test(evals): /submit final eval — verifier scored, disclosure check stops the run, no cover letter`.

---

### Task 15: `/talk create` — symlink before render, storyteller then critic, no score, bare-filename embeds

**Files:** Create `tests/evals/check_talk.py`, `tests/test_eval_talk.py`, `tests/evals/talk.sh`.

**Prompt:** `/talk create lightning --yes`

**Setup:** `manuscript=85` seeded; the fixture's `talks/` has no manuscript symlink.

**Mechanism (audit §6):** a Bash `ln -s` creating `talks/manuscript_fixture.qmd` precedes the first `quarto render` Bash; `storyteller` precedes `storyteller-critic`; no `record-score` runs (advisory stage); post-run, `talks/manuscript_fixture.qmd` is a symlink, `talks/lightning_talk.qmd` exists, every `{{< embed … >}}` in it uses the bare `manuscript_fixture.qmd#` and none embeds a `tbl-` chunk.

- [ ] **Step 1: Checker** — `tests/evals/check_talk.py`:

```python
#!/usr/bin/env python3
"""check_talk.py — /talk create: the relative manuscript symlink is made before any render;
storyteller then storyteller-critic; no record-score (advisory); embeds by bare filename; no
tbl- embeds (tables go to backup slides as figures/images, per the storyteller's rules).
usage: check_talk.py <transcript.jsonl> <project-dir>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2])
fails = []
ln = evallib.first(uses, lambda n, a: n == "Bash" and re.search(r"ln\s+-s[^\n]*manuscript_fixture\.qmd", a.get("command", "")))
render = evallib.first(uses, lambda n, a: n == "Bash" and "quarto render" in a.get("command", ""))
if ln is None: fails.append("no Bash `ln -s … manuscript_fixture.qmd` created the talks/ symlink")
elif render is not None and render < ln: fails.append("quarto render ran before the manuscript symlink existed")
s, c = evallib.agent(uses, "storyteller"), evallib.agent(uses, "storyteller-critic")
if s is None: fails.append("storyteller was never dispatched")
if c is None: fails.append("storyteller-critic was never dispatched")
elif s is not None and c < s: fails.append("storyteller-critic ran before storyteller")
if any("record-score" in x for x in evallib.bash(uses)): fails.append("record-score ran — talk scores are advisory and unrecorded")
link = proj / "talks" / "manuscript_fixture.qmd"
if not link.is_symlink(): fails.append("talks/manuscript_fixture.qmd is not a symlink after the run")
talk = proj / "talks" / "lightning_talk.qmd"
if not talk.exists(): fails.append("talks/lightning_talk.qmd was not written")
else:
    embeds = re.findall(r"\{\{<\s*embed\s+([^\s>]+)", talk.read_text())
    bad = [e for e in embeds if not e.startswith("manuscript_fixture.qmd#")]
    if bad: fails.append(f"embeds not by bare filename: {bad}")
    if any("#tbl-" in e for e in embeds): fails.append("a tbl- chunk is embedded (tables belong in backup as figures)")
evallib.finish("check_talk", fails, f"tool_use: {len(uses)} · symlink: {link.is_symlink()} · talk: {talk.exists()}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_talk.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_talk.py"
T = (use("u1", "Bash", command="cd talks && ln -s ../manuscript_fixture.qmd manuscript_fixture.qmd")
     + use("u2", "Agent", subagent_type="storyteller", prompt="x")
     + use("u3", "Bash", command="quarto render talks/lightning_talk.qmd")
     + use("u4", "Agent", subagent_type="storyteller-critic", prompt="x"))


class TestTalkChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name); (self.p / "talks").mkdir()
        (self.p / "manuscript_fixture.qmd").write_text("x"); (self.p / "talks" / "manuscript_fixture.qmd").symlink_to("../manuscript_fixture.qmd")
        (self.p / "talks" / "lightning_talk.qmd").write_text("## A\n\n{{< embed manuscript_fixture.qmd#fig-trends >}}\n")

    def tearDown(self):
        self.d.cleanup()

    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 0, out)

    def test_render_before_symlink_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, lines[2] + lines[0] + lines[1] + lines[3], self.p); self.assertEqual(rc, 1); self.assertIn("before the manuscript symlink", out)

    def test_record_score_fails(self):
        rc, out = go(CHECK, T + use("u5", "Bash", command="python3 .claude/scripts/pipeline.py state record-score manuscript 90 --critic writer-critic --report x"), self.p); self.assertEqual(rc, 1); self.assertIn("advisory", out)

    def test_tbl_embed_fails(self):
        (self.p / "talks" / "lightning_talk.qmd").write_text("{{< embed manuscript_fixture.qmd#tbl-main >}}\n"); rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 1); self.assertIn("tbl- chunk", out)

    def test_path_embed_fails(self):
        (self.p / "talks" / "lightning_talk.qmd").write_text("{{< embed ../manuscript_fixture.qmd#fig-trends >}}\n"); rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 1); self.assertIn("bare filename", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_talk -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/talk.sh` (`chmod +x`, `seed_score` pasted in as in Task 14):

```bash
#!/usr/bin/env bash
# tests/evals/talk.sh — functionality eval for /talk create lightning. manuscript is scored 85 so
# the storyteller's requires pass; talks/ has no manuscript symlink yet. Run alone. EVAL_TIMEOUT 3600.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=3600}"
seed_score() {
  mkdir -p "$E/quality_reports/reviews"
  echo "# $3 — seeded fixture input ($(date +%F))" >"$E/quality_reports/reviews/$3_seed.md"
  python3 "$RC/scripts/pipeline.py" --root "$E" state record-score "$1" "$2" --critic "$3" --report "quality_reports/reviews/$3_seed.md" >/dev/null
}
eval_setup
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
seed_score manuscript 85 writer-critic
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed manuscript score" >/dev/null
eval_run '/talk create lightning --yes' "$LOG" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent"
eval_finish check_talk.py "$LOG" "$E"
```

- [ ] **Step 5: Run alone** → expected PASS.
- [ ] **Step 6: Log and commit** — `test(evals): /talk create eval — symlink before render, creator→critic, no score, bare embeds`.

---

### Task 16: `/write conclusion` — manuscript resolved first, writer then critic, section-scoped score, prose check clean

**Files:** Create `tests/evals/check_write.py`, `tests/test_eval_write.py`, `tests/evals/write.sh`.

**Prompt:** `/write conclusion --yes`

**Setup (audit §6):** `code=85` seeded; `.claude/references/personal-style-guide.md` replaced by a filled minimal guide (a real file — `_lib.sh` already de-linked it) so the VOICE block does not stop the run.

**Mechanism:** `pipeline.py manuscript` runs before the first Agent; `writer` precedes `writer-critic`; `record-score manuscript … --scope section:<conclusion>` runs and its `--report` path was Written earlier in the transcript; post-run `prose_number_check.py` exits 0 (the runner computes it and passes the exit code).

- [ ] **Step 1: Checker** — `tests/evals/check_write.py`:

```python
#!/usr/bin/env python3
"""check_write.py — /write <section>: `pipeline.py manuscript` before any dispatch; writer then
writer-critic; the manuscript score is recorded section-scoped with a --report that was written
first; the prose-number check passes afterwards (runner-supplied exit code).
usage: check_write.py <transcript.jsonl> <project-dir> <prose-check-exit-code>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj, prose_rc = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3])
fails = []
ms = evallib.first(uses, lambda n, a: n == "Bash" and re.search(r"pipeline\.py\s+manuscript\b", a.get("command", "")))
first_agent = evallib.first(uses, lambda n, a: n == "Agent")
if ms is None: fails.append("`pipeline.py manuscript` never ran")
elif first_agent is not None and first_agent < ms: fails.append("an agent was dispatched before the manuscript was resolved")
w, c = evallib.agent(uses, "writer"), evallib.agent(uses, "writer-critic")
if w is None: fails.append("writer was never dispatched")
if c is None: fails.append("writer-critic was never dispatched")
elif w is not None and c < w: fails.append("writer-critic ran before writer")
recs = [(i, a.get("command", "")) for i, (n, a, _) in enumerate(uses) if n == "Bash" and re.search(r"record-score\s+manuscript\b", a.get("command", ""))]
if not recs: fails.append("record-score manuscript never ran")
for i, cmd in recs:
    if not re.search(r"--scope\s+section:\S*conclusion", cmd, re.I): fails.append(f"record-score manuscript is not scoped to section:Conclusion: {cmd[:100]!r}")
    m = re.search(r"--report\s+(\S+)", cmd)
    if m and evallib.first(uses[:i], lambda n, a: n == "Write" and str(a.get("file_path", "")).endswith(m.group(1).split("/")[-1])) is None:
        fails.append(f"the report {m.group(1)} was not Written before its score was recorded")
if prose_rc != 0: fails.append(f"prose_number_check exited {prose_rc} after the draft")
evallib.finish("check_write", fails, f"tool_use: {len(uses)} · records: {len(recs)} · prose check rc: {prose_rc}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_write.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_write.py"
T = (use("u1", "Bash", command="python3 .claude/scripts/pipeline.py manuscript")
     + use("u2", "Agent", subagent_type="writer", prompt="x")
     + use("u3", "Agent", subagent_type="writer-critic", prompt="x")
     + use("u4", "Write", file_path="/p/quality_reports/reviews/writer-critic_2026-09-25.md", content="r")
     + use("u5", "Bash", command="python3 .claude/scripts/pipeline.py state record-score manuscript 88 --critic writer-critic --deductions 12 --report quality_reports/reviews/writer-critic_2026-09-25.md --scope section:Conclusion"))


class TestWriteChecker(unittest.TestCase):
    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, "/p", 0); self.assertEqual(rc, 0, out)

    def test_dispatch_before_resolve_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, lines[1] + lines[0] + "".join(lines[2:]), "/p", 0); self.assertEqual(rc, 1); self.assertIn("before the manuscript was resolved", out)

    def test_unscoped_score_fails(self):
        rc, out = go(CHECK, T.replace(" --scope section:Conclusion", ""), "/p", 0); self.assertEqual(rc, 1); self.assertIn("not scoped", out)

    def test_score_before_report_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, "".join(lines[:3]) + lines[4] + lines[3], "/p", 0); self.assertEqual(rc, 1); self.assertIn("not Written before", out)

    def test_prose_check_red_fails(self):
        rc, out = go(CHECK, T, "/p", 1); self.assertEqual(rc, 1); self.assertIn("prose_number_check exited 1", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_write -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/write.sh` (`chmod +x`, `seed_score` pasted in):

```bash
#!/usr/bin/env bash
# tests/evals/write.sh — functionality eval for /write conclusion. code=85 so the writer's requires
# pass; a filled style guide so the VOICE block does not halt the run. The mock is registered because
# write's frontmatter does not need it but the writer-critic's local-literature sweep may. Run alone.
# EVAL_TIMEOUT 3600.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=3600}"
seed_score() {
  mkdir -p "$E/quality_reports/reviews"
  echo "# $3 — seeded fixture input ($(date +%F))" >"$E/quality_reports/reviews/$3_seed.md"
  python3 "$RC/scripts/pipeline.py" --root "$E" state record-score "$1" "$2" --critic "$3" --report "quality_reports/reviews/$3_seed.md" >/dev/null
}
eval_setup
eval_mock
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
seed_score code 85 coder-critic
cat >"$E/.claude/references/personal-style-guide.md" <<'MD'
# Personal Style Guide

## Source Corpus
**Extracted on:** 2026-09-25
**Papers analyzed:** 2 (fixture)

## Sentence-level patterns
- Declarative openings; the finding first, the mechanism second.
- Numbers in prose are inline `r` expressions, never typed.

## Paragraph moves
- Claim → evidence (a table or figure reference) → caveat.

## Self-citation
- None.
MD
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed code score + style guide" >/dev/null
eval_run '/write conclusion --yes' "$LOG" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "mcp__zotpilot__*"
python3 "$RC/scripts/prose_number_check.py" "$E/manuscript_fixture.qmd" >"$E/prose.log" 2>&1; PRC=$?
eval_finish check_write.py "$LOG" "$E" "$PRC"
```

- [ ] **Step 5: Run alone** → expected PASS.
- [ ] **Step 6: Log and commit** — `test(evals): /write eval — manuscript resolved first, writer→critic, section-scoped score, prose check`.

---

### Task 17: `/strategize` — strategist then critic, only the chosen design's checklist, one score, a decision record with alternatives

**Files:** Create `tests/evals/check_strategize.py`, `tests/test_eval_strategize.py`, `tests/evals/strategize.sh`.

**Prompt:** `/strategize Did staggered state paid-sick-leave mandates (2012–2020) reduce county injury rates? County-year panel, never-treated states. --yes`

**Setup (audit §6):** `positioning.md` and `data_sources.md` seeded (the strategist's `any_of` requires).

**Mechanism:** `strategist` precedes `strategist-critic`; the strategist's Agent prompt names `design-checklists/did.md` or `design-checklists/event-study.md` and none of `iv.md`, `rdd.md`, `structural.md`, `descriptive.md` ("Naming all seven is what makes an agent read all seven"); exactly one `record-score strategy`; post-run `quality_reports/decisions/strategy_*.md` exists with an "Alternatives" heading.

- [ ] **Step 1: Checker** — `tests/evals/check_strategize.py`:

```python
#!/usr/bin/env python3
"""check_strategize.py — /strategize: strategist then strategist-critic; the strategist is handed only
the chosen design's checklist (did or event-study for a staggered panel; never iv/rdd/structural/
descriptive); exactly one record-score strategy; a decision record with Alternatives exists.
usage: check_strategize.py <transcript.jsonl> <project-dir>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2])
fails = []
s, c = evallib.agent(uses, "strategist"), evallib.agent(uses, "strategist-critic")
if s is None: fails.append("strategist was never dispatched")
if c is None: fails.append("strategist-critic was never dispatched")
elif s is not None and c < s: fails.append("strategist-critic ran before strategist")
if s is not None:
    p = str(uses[s][1].get("prompt", ""))
    if not re.search(r"design-checklists/(did|event-study)\.md", p): fails.append("the strategist's prompt names neither did.md nor event-study.md")
    wrong = re.findall(r"design-checklists/(iv|rdd|structural|descriptive)\.md", p)
    if wrong: fails.append(f"the strategist's prompt names other designs' checklists: {sorted(set(wrong))}")
recs = [x for x in evallib.bash(uses) if re.search(r"record-score\s+strategy\b", x)]
if len(recs) != 1: fails.append(f"record-score strategy ran {len(recs)} times (expected exactly 1)")
dec = list(proj.glob("quality_reports/decisions/strategy_*.md"))
if not dec: fails.append("no quality_reports/decisions/strategy_*.md was written")
elif not any(re.search(r"^#+\s*.*Alternatives", d.read_text(), re.M | re.I) for d in dec): fails.append("the decision record has no Alternatives section")
evallib.finish("check_strategize", fails, f"tool_use: {len(uses)} · records: {len(recs)} · decision records: {len(dec)}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_strategize.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_strategize.py"
T = (use("u1", "Agent", subagent_type="strategist", prompt="Use .claude/skills/strategize/templates/design-checklists/did.md only")
     + use("u2", "Agent", subagent_type="strategist-critic", prompt="x")
     + use("u3", "Bash", command="python3 .claude/scripts/pipeline.py state record-score strategy 84 --critic strategist-critic --deductions 16 --report quality_reports/reviews/strategist-critic_x.md"))


class TestStrategizeChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name); (self.p / "quality_reports" / "decisions").mkdir(parents=True)
        (self.p / "quality_reports" / "decisions" / "strategy_psl.md").write_text("# Decision\n\n## Alternatives considered\n\n- IV: rejected\n- RDD: rejected\n")

    def tearDown(self):
        self.d.cleanup()

    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 0, out)

    def test_all_checklists_named_fails(self):
        rc, out = go(CHECK, T.replace("did.md only", "did.md, design-checklists/iv.md, design-checklists/rdd.md"), self.p); self.assertEqual(rc, 1); self.assertIn("other designs", out)

    def test_two_scores_fail(self):
        rc, out = go(CHECK, T + T.splitlines(keepends=True)[2], self.p); self.assertEqual(rc, 1); self.assertIn("ran 2 times", out)

    def test_critic_first_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, lines[1] + lines[0] + lines[2], self.p); self.assertEqual(rc, 1); self.assertIn("before strategist", out)

    def test_no_alternatives_fails(self):
        (self.p / "quality_reports" / "decisions" / "strategy_psl.md").write_text("# Decision\n\nDiD.\n"); rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 1); self.assertIn("Alternatives", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_strategize -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/strategize.sh` (`chmod +x`):

```bash
#!/usr/bin/env bash
# tests/evals/strategize.sh — functionality eval for /strategize. Seeds positioning.md and
# data_sources.md (the strategist's any_of requires) as run_fixture.sh seeds literature. Run alone.
# EVAL_TIMEOUT 3600 (two 12-minute agents, plus a possible second round).
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=3600}"
eval_setup
eval_mock
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
mkdir -p "$E/quality_reports/literature/fixture" "$E/quality_reports/data-assessment/fixture"
cat >"$E/quality_reports/literature/fixture/positioning.md" <<'MD'
# Positioning — seeded fixture input

**Gap.** No county-level estimate of paid-sick-leave mandates on workplace injury rates.
**Contribution.** A staggered-adoption design on a county-year panel with never-treated states.
MD
cat >"$E/quality_reports/data-assessment/fixture/data_sources.md" <<'MD'
# Data sources — seeded fixture input

| Dataset | Access | Coverage | Grade |
|---|---|---|---|
| County-year injury rates (synthetic stand-in, `data/raw/panel.csv`) | public | 2012–2020, all counties | A |
| State mandate dates (hand-coded) | public | 2012–2020 | A |
MD
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed discovery inputs" >/dev/null
eval_run '/strategize Did staggered state paid-sick-leave mandates (2012–2020) reduce county injury rates? County-year panel, never-treated states. --yes' \
  "$LOG" "Read" "Grep" "Glob" "Write" "Bash" "Agent" "mcp__zotpilot__*"
eval_finish check_strategize.py "$LOG" "$E"
```

- [ ] **Step 5: Run alone** → expected PASS. A below-80 first round re-dispatches both agents and records a second score, which makes assertion "exactly one" red — that is the audit's assertion as written; if it happens, record `FAIL (design)` with the two scores and leave the assertion in for a decision.
- [ ] **Step 6: Log and commit** — `test(evals): /strategize eval — creator→critic, chosen checklist only, one score, decision record`.

---

### Task 18: `/discover data` — domain profile before dispatch, explorer then critic, three artifacts, data score, no web calls in the main session

**Files:** Create `tests/evals/check_discover.py`, `tests/test_eval_discover.py`, `tests/evals/discover.sh`.

**Prompt:** `/discover data Need county-by-quarter teen employment and state minimum-wage changes, 2010–2020, US, staggered DiD. --yes`

**Mechanism (audit §6):** `.claude/references/domain-profile.md` is Read before the explorer is dispatched; `explorer` precedes `explorer-critic`; `record-score data` runs after a Write of its report; no `WebSearch`/`WebFetch` tool_use in the main transcript (the explorer keeps its own web tools; the session does not); post-run the three files exist under `quality_reports/data-assessment/*/`.

- [ ] **Step 1: Checker** — `tests/evals/check_discover.py`:

```python
#!/usr/bin/env python3
"""check_discover.py — /discover data: the domain profile is read before dispatch; explorer then
explorer-critic; record-score data after its report is written; no web tool in the main session;
data_sources.md, data_dictionary.md, access_instructions.md exist.
usage: check_discover.py <transcript.jsonl> <project-dir>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2])
fails = []
prof = evallib.first(uses, lambda n, a: n == "Read" and str(a.get("file_path", "")).endswith("domain-profile.md"))
ex, cr = evallib.agent(uses, "explorer"), evallib.agent(uses, "explorer-critic")
if ex is None: fails.append("explorer was never dispatched")
elif prof is None or prof > ex: fails.append("domain-profile.md was not Read before the explorer was dispatched")
if cr is None: fails.append("explorer-critic was never dispatched")
elif ex is not None and cr < ex: fails.append("explorer-critic ran before explorer")
rec = evallib.first(uses, lambda n, a: n == "Bash" and re.search(r"record-score\s+data\b", a.get("command", "")))
if rec is None: fails.append("record-score data never ran")
else:
    m = re.search(r"--report\s+(\S+)", uses[rec][1].get("command", ""))
    if m and evallib.first(uses[:rec], lambda n, a: n == "Write" and str(a.get("file_path", "")).endswith(m.group(1).split("/")[-1])) is None:
        fails.append("the explorer-critic report was not Written before its score was recorded")
if any(n in ("WebSearch", "WebFetch") for n, _, _ in uses): fails.append("the main session called a web tool — that is the explorer's job")
for f in ("data_sources.md", "data_dictionary.md", "access_instructions.md"):
    if not list(proj.glob(f"quality_reports/data-assessment/*/{f}")): fails.append(f"quality_reports/data-assessment/*/{f} was not written")
evallib.finish("check_discover", fails, f"tool_use: {len(uses)} · explorer: {ex is not None} · critic: {cr is not None}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_discover.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_discover.py"
T = (use("u1", "Read", file_path="/p/.claude/references/domain-profile.md")
     + use("u2", "Agent", subagent_type="explorer", prompt="x")
     + use("u3", "Agent", subagent_type="explorer-critic", prompt="x")
     + use("u4", "Write", file_path="/p/quality_reports/reviews/explorer-critic_2026-09-25.md", content="r")
     + use("u5", "Bash", command="python3 .claude/scripts/pipeline.py state record-score data 82 --critic explorer-critic --deductions 18 --report quality_reports/reviews/explorer-critic_2026-09-25.md"))


class TestDiscoverChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name); a = self.p / "quality_reports" / "data-assessment" / "fx"; a.mkdir(parents=True)
        for f in ("data_sources.md", "data_dictionary.md", "access_instructions.md"): (a / f).write_text("x")

    def tearDown(self):
        self.d.cleanup()

    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 0, out)

    def test_dispatch_before_profile_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, lines[1] + lines[0] + "".join(lines[2:]), self.p); self.assertEqual(rc, 1); self.assertIn("not Read before", out)

    def test_web_tool_fails(self):
        rc, out = go(CHECK, T + use("u6", "WebSearch", query="teen employment data"), self.p); self.assertEqual(rc, 1); self.assertIn("web tool", out)

    def test_missing_artifact_fails(self):
        (self.p / "quality_reports" / "data-assessment" / "fx" / "access_instructions.md").unlink(); rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 1); self.assertIn("access_instructions.md", out)

    def test_score_before_report_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, "".join(lines[:3]) + lines[4] + lines[3], self.p); self.assertEqual(rc, 1); self.assertIn("not Written before", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_discover -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/discover.sh` (`chmod +x`):

```bash
#!/usr/bin/env bash
# tests/evals/discover.sh — functionality eval for /discover data. The explorer has its own web tools
# (agents/explorer.md); the main session must not. The mock is registered for the critic's local
# literature sweep. Run alone. EVAL_TIMEOUT 3600.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=3600}"
eval_setup
eval_mock
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "state init" >/dev/null
eval_run '/discover data Need county-by-quarter teen employment and state minimum-wage changes, 2010–2020, US, staggered DiD. --yes' \
  "$LOG" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "mcp__zotpilot__*"
eval_finish check_discover.py "$LOG" "$E"
```

- [ ] **Step 5: Run alone** → expected PASS.
- [ ] **Step 6: Log and commit** — `test(evals): /discover data eval — profile before dispatch, explorer→critic, three artifacts, no session web calls`.

---

### Task 19: `/review` (comprehensive) — three critics, porcelain around the verifier, report saved before each score, pool never read here

**Files:** Create `tests/evals/check_review.py`, `tests/test_eval_review.py`, `tests/evals/review.sh`.

**Prompt:** `/review manuscript_fixture.qmd --yes`

**Setup (audit §6):** `code=85` and `strategy=85` seeded.

**Mechanism:** Agent dispatches for `strategist-critic`, `writer-critic` and `verifier` all present; a `git status --porcelain` Bash before the verifier's dispatch and another after it; `record-score` for `strategy`, `manuscript` and `replication` each present and each preceded by a Write of its `--report`; no Read of `disposition-pool.md` in the main session (that file is for `--peer`'s editor).

- [ ] **Step 1: Checker** — `tests/evals/check_review.py`:

```python
#!/usr/bin/env python3
"""check_review.py — /review <manuscript>: strategist-critic, writer-critic and verifier dispatched;
porcelain before and after the verifier; each component's report Written before its record-score;
disposition-pool.md never read in the main context. usage: check_review.py <transcript.jsonl> <project-dir>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses = evallib.tool_uses(sys.argv[1])
fails = []
d = {a: evallib.agent(uses, a) for a in ("strategist-critic", "writer-critic", "verifier")}
for a, i in d.items():
    if i is None: fails.append(f"{a} was never dispatched")
v = d["verifier"]
if v is not None:
    porc = [i for i, (n, a, _) in enumerate(uses) if n == "Bash" and re.search(r"git\s+status\s+--porcelain", a.get("command", ""))]
    if not any(i < v for i in porc): fails.append("no `git status --porcelain` before the verifier's dispatch")
    if not any(i > v for i in porc): fails.append("no `git status --porcelain` after the verifier returned")
for comp in ("strategy", "manuscript", "replication"):
    rec = evallib.first(uses, lambda n, a, comp=comp: n == "Bash" and re.search(rf"record-score\s+{comp}\b", a.get("command", "")))
    if rec is None: fails.append(f"record-score {comp} never ran"); continue
    m = re.search(r"--report\s+(\S+)", uses[rec][1].get("command", ""))
    if m and evallib.first(uses[:rec], lambda n, a, f=m.group(1).split("/")[-1]: n == "Write" and str(a.get("file_path", "")).endswith(f)) is None:
        fails.append(f"the {comp} report was not Written before its score was recorded")
if evallib.first(uses, lambda n, a: n == "Read" and "disposition-pool.md" in str(a.get("file_path", ""))) is not None:
    fails.append("disposition-pool.md was read in the main context (it is the editor's, in --peer)")
evallib.finish("check_review", fails, f"tool_use: {len(uses)} · dispatched: {[a for a, i in d.items() if i is not None]}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_review.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_review.py"
def rec(comp, critic, rep): return use("r" + comp, "Bash", command=f"python3 .claude/scripts/pipeline.py state record-score {comp} 90 --critic {critic} --report {rep}")
T = (use("u1", "Bash", command="git status --porcelain")
     + use("u2", "Agent", subagent_type="strategist-critic", prompt="x") + use("u3", "Agent", subagent_type="writer-critic", prompt="x") + use("u4", "Agent", subagent_type="verifier", prompt="x")
     + use("u5", "Bash", command="git status --porcelain")
     + use("w1", "Write", file_path="/p/quality_reports/reviews/strategist-critic_d.md", content="r") + rec("strategy", "strategist-critic", "quality_reports/reviews/strategist-critic_d.md")
     + use("w2", "Write", file_path="/p/quality_reports/reviews/writer-critic_d.md", content="r") + rec("manuscript", "writer-critic", "quality_reports/reviews/writer-critic_d.md")
     + use("w3", "Write", file_path="/p/quality_reports/verification_report.md", content="r") + rec("replication", "verifier", "quality_reports/verification_report.md"))


class TestReviewChecker(unittest.TestCase):
    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, "/p"); self.assertEqual(rc, 0, out)

    def test_no_porcelain_after_fails(self):
        rc, out = go(CHECK, T.replace(use("u5", "Bash", command="git status --porcelain"), ""), "/p"); self.assertEqual(rc, 1); self.assertIn("after the verifier", out)

    def test_missing_critic_fails(self):
        rc, out = go(CHECK, T.replace(use("u3", "Agent", subagent_type="writer-critic", prompt="x"), ""), "/p"); self.assertEqual(rc, 1); self.assertIn("writer-critic was never dispatched", out)

    def test_score_before_report_fails(self):
        rc, out = go(CHECK, T.replace(use("w2", "Write", file_path="/p/quality_reports/reviews/writer-critic_d.md", content="r"), ""), "/p"); self.assertEqual(rc, 1); self.assertIn("manuscript report was not Written", out)

    def test_pool_read_fails(self):
        rc, out = go(CHECK, T + use("u9", "Read", file_path="/p/.claude/skills/review/templates/disposition-pool.md"), "/p"); self.assertEqual(rc, 1); self.assertIn("disposition-pool.md", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_review -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/review.sh` (`chmod +x`, `seed_score` pasted in):

```bash
#!/usr/bin/env bash
# tests/evals/review.sh — functionality eval for the comprehensive /review. code and strategy are
# scored so the manuscript route is open; three critics dispatch in one turn. Run alone.
# EVAL_TIMEOUT 3600.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=3600}"
seed_score() {
  mkdir -p "$E/quality_reports/reviews"
  echo "# $3 — seeded fixture input ($(date +%F))" >"$E/quality_reports/reviews/$3_seed.md"
  python3 "$RC/scripts/pipeline.py" --root "$E" state record-score "$1" "$2" --critic "$3" --report "quality_reports/reviews/$3_seed.md" >/dev/null
}
eval_setup
eval_mock
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
seed_score code 85 coder-critic; seed_score strategy 85 strategist-critic
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed scores" >/dev/null
eval_run '/review manuscript_fixture.qmd --yes' "$LOG" "Read" "Grep" "Glob" "Write" "Bash" "Agent" "mcp__zotpilot__*"
eval_finish check_review.py "$LOG" "$E"
```

- [ ] **Step 5: Run alone** → expected PASS.
- [ ] **Step 6: Log and commit** — `test(evals): /review eval — three critics, porcelain around the verifier, reports before scores`.

---

### Task 20: `/analyze` — Step 0 first, data-engineer → critic → coder → critic, reports before scores, render and prose check clean

**Files:** Create `tests/evals/check_analyze.py`, `tests/test_eval_analyze.py`, `tests/evals/analyze.sh`.

**Prompt:** `/analyze "add a robustness check clustering by year and an event-study figure" --yes` (no strategy memo — the Pre-Code Report must flag it).

**Setup:** `strategy=85` seeded so `pre coder` passes.

**Mechanism (audit §6):** the Step 0 commands (`pipeline.py manuscript`, `pre coder`) run before any Agent; the dispatch order contains the subsequence data-engineer, coder-critic, coder, coder-critic; every `record-score code` is preceded by a Write of its `--report`; post-run `quarto render` and `prose_number_check.py` exit 0 (runner-supplied). (The chunk-structure read and the Pre-Code Report's "memo missing" flag happen inside the coder's context and are not transcript-visible; not asserted.)

- [ ] **Step 1: Checker** — `tests/evals/check_analyze.py`:

```python
#!/usr/bin/env python3
"""check_analyze.py — /analyze: Step 0 (`pipeline.py manuscript`, `pre coder`) before any dispatch;
data-engineer → coder-critic → coder → coder-critic as a subsequence; each record-score code after
a Write of its report; render and prose check exit 0 afterwards (runner-supplied codes).
usage: check_analyze.py <transcript.jsonl> <project-dir> <render-rc> <prose-rc>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, render_rc, prose_rc = evallib.tool_uses(sys.argv[1]), int(sys.argv[3]), int(sys.argv[4])
fails = []
first_agent = evallib.first(uses, lambda n, a: n == "Agent")
for pat, label in ((r"pipeline\.py\s+manuscript\b", "pipeline.py manuscript"), (r"pipeline\.py\s+pre\s+coder\b", "pipeline.py pre coder")):
    i = evallib.first(uses, lambda n, a, pat=pat: n == "Bash" and re.search(pat, a.get("command", "")))
    if i is None: fails.append(f"Step 0: `{label}` never ran")
    elif first_agent is not None and first_agent < i: fails.append(f"Step 0: `{label}` ran after an agent was dispatched")
seq = [a.get("subagent_type") for n, a, _ in uses if n == "Agent"]
want = ["data-engineer", "coder-critic", "coder", "coder-critic"]
it = iter(seq)
if not all(any(s == w for s in it) for w in want): fails.append(f"dispatch order {seq} does not contain data-engineer → coder-critic → coder → coder-critic")
for i, (n, a, _) in enumerate(uses):
    if n == "Bash" and re.search(r"record-score\s+code\b", a.get("command", "")):
        m = re.search(r"--report\s+(\S+)", a.get("command", ""))
        if m and evallib.first(uses[:i], lambda n2, a2, f=m.group(1).split("/")[-1]: n2 == "Write" and str(a2.get("file_path", "")).endswith(f)) is None:
            fails.append(f"a code score was recorded before its report {m.group(1)} was Written"); break
if render_rc != 0: fails.append(f"quarto render exited {render_rc} after the analysis")
if prose_rc != 0: fails.append(f"prose_number_check exited {prose_rc} after the analysis")
evallib.finish("check_analyze", fails, f"tool_use: {len(uses)} · dispatches: {seq} · render rc {render_rc} · prose rc {prose_rc}")
```

- [ ] **Step 2: Unit test** — `tests/test_eval_analyze.py` (helper block, then):

```python
CHECK = ROOT / "tests" / "evals" / "check_analyze.py"
def ag(uid, t): return use(uid, "Agent", subagent_type=t, prompt="x")
T = (use("s1", "Bash", command="python3 .claude/scripts/pipeline.py manuscript") + use("s2", "Bash", command="python3 .claude/scripts/pipeline.py pre coder")
     + ag("a1", "data-engineer") + ag("a2", "coder-critic")
     + use("w1", "Write", file_path="/p/quality_reports/reviews/coder-critic_a.md", content="r")
     + use("r1", "Bash", command="python3 .claude/scripts/pipeline.py state record-score code 85 --critic coder-critic --report quality_reports/reviews/coder-critic_a.md")
     + ag("a3", "coder") + ag("a4", "coder-critic")
     + use("w2", "Write", file_path="/p/quality_reports/reviews/coder-critic_b.md", content="r")
     + use("r2", "Bash", command="python3 .claude/scripts/pipeline.py state record-score code 88 --critic coder-critic --report quality_reports/reviews/coder-critic_b.md"))


class TestAnalyzeChecker(unittest.TestCase):
    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, "/p", 0, 0); self.assertEqual(rc, 0, out)

    def test_step0_after_dispatch_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, lines[2] + lines[0] + lines[1] + "".join(lines[3:]), "/p", 0, 0); self.assertEqual(rc, 1); self.assertIn("after an agent", out)

    def test_wrong_order_fails(self):
        rc, out = go(CHECK, T.replace(ag("a1", "data-engineer"), ag("a1", "coder")), "/p", 0, 0); self.assertEqual(rc, 1); self.assertIn("dispatch order", out)

    def test_score_before_report_fails(self):
        rc, out = go(CHECK, T.replace(use("w2", "Write", file_path="/p/quality_reports/reviews/coder-critic_b.md", content="r"), ""), "/p", 0, 0); self.assertEqual(rc, 1); self.assertIn("before its report", out)

    def test_render_red_fails(self):
        rc, out = go(CHECK, T, "/p", 1, 0); self.assertEqual(rc, 1); self.assertIn("quarto render exited 1", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3:** `python3 -m unittest tests.test_eval_analyze -v` → 5 OK.

- [ ] **Step 4: Runner** — `tests/evals/analyze.sh` (`chmod +x`, `seed_score` pasted in):

```bash
#!/usr/bin/env bash
# tests/evals/analyze.sh — functionality eval for /analyze with no strategy memo. strategy=85 so
# `pre coder` passes. Four agent dispatches: the longest eval — EVAL_TIMEOUT 5400. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=5400}"
seed_score() {
  mkdir -p "$E/quality_reports/reviews"
  echo "# $3 — seeded fixture input ($(date +%F))" >"$E/quality_reports/reviews/$3_seed.md"
  python3 "$RC/scripts/pipeline.py" --root "$E" state record-score "$1" "$2" --critic "$3" --report "quality_reports/reviews/$3_seed.md" >/dev/null
}
eval_setup
eval_mock
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
seed_score strategy 85 strategist-critic
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed strategy score" >/dev/null
eval_run '/analyze "add a robustness check clustering by year and an event-study figure" --yes' \
  "$LOG" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "mcp__zotpilot__*"
( cd "$E" && quarto render manuscript_fixture.qmd >"$E/render.log" 2>&1 ); RRC=$?
python3 "$RC/scripts/prose_number_check.py" "$E/manuscript_fixture.qmd" >"$E/prose.log" 2>&1; PRC=$?
eval_finish check_analyze.py "$LOG" "$E" "$RRC" "$PRC"
```

- [ ] **Step 5: Run alone** → expected PASS. Budget 90 minutes.
- [ ] **Step 6: Log and commit** — `test(evals): /analyze eval — Step 0 first, engineer→critic→coder→critic, reports before scores, render+prose clean`.

---

## Close-out (after Task 20)

- [ ] Run the whole unit suite once: `python3 -m unittest discover -s tests -q` → OK (327 + 4 evallib + 6 mock + ~95 checker tests).
- [ ] Update `docs/plans/2026-09-24-option-gates-subagent-routing-evals.md` "What this plan deliberately leaves open": replace the "20 remain" sentence with a pointer to this plan and its Progress Log.
- [ ] Repoint `CLAUDE.md` § Start here: the "evals for the remaining skills" clause now reads "closed by `docs/plans/2026-09-25-remaining-skill-evals.md` (see its Progress Log for the runs that came back red on the skill)".
- [ ] `/checkpoint` — append the session entry to `docs/SESSION_REPORT.md` with the table of PASS / FAIL (skill) / FAIL (design) results.

## Progress Log

| Task | Skill | Status | Commit | Live run summary (from the checker's summary line) |
|---|---|---|---|---|
| 0 | harness | | | |
| 1 | careful | PASS | pending | run A tool_use: 5 · run B tool_use: 3 · attempts: rm=1 push=1 |
| 2 | freeze | | | |
| 3 | checkpoint | | | |
| 4 | new-project-ztp | | | |
| 5 | seed-papers | | | |
| 6 | ztp-review | | | |
| 7 | ztp-research | | | |
| 8 | ztp-profile | | | |
| 9 | ztp-tutor | | | |
| 10 | promote | | | |
| 11 | civilize | | | |
| 12 | verify-claims | | | |
| 13 | revise | | | |
| 14 | submit | | | |
| 15 | talk | | | |
| 16 | write | | | |
| 17 | strategize | | | |
| 18 | discover | | | |
| 19 | review | | | |
| 20 | analyze | | | |

Status values: `PASS` · `FAIL (harness → fixed, PASS)` · `FAIL (skill: <assertion>)` · `FAIL (design: <assertion>)` · `timeout`.
