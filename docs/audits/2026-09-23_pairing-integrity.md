# Creator ↔ Critic Pairing Integrity Audit

**Date:** 2026-09-23
**Scope:** `~/Academic/research-claude` @ branch `jrer-rebase`
**Method:** every file named in the brief read to EOF; behavioral claims re-derived by running the
code against a purpose-built fixture project.
**Mode:** read-only reconnaissance. **No pipeline file was changed.**

Every claim below is labelled:

- **`tested:`** — I ran it in this session and observed the output quoted.
- **`per file:`** — I read the file in full and am quoting it.

Fixture used for every `tested:` claim:
`/private/tmp/claude-504/…/scratchpad/fixture/` — a minimal project with `CLAUDE.md`
(`manuscript: paper.qmd`), a copy of `rules/registry.yaml` at `.claude/rules/`, copies of
`pipeline.py` / `registry_lib.py` / `prose_number_check.py` at `.claude/scripts/`, and copies of
`critic-pairing.py` / `dispatch-log.py` at `.claude/hooks/`. Hook tests ran under an isolated
`HOME` so no sentinel was written to the real `~/.claude/sessions/`.

**Files read in full:** `rules/registry.yaml`, `rules/agents.md`, `hooks/critic-pairing.py`,
`hooks/dispatch-log.py`, `hooks/README.md`, `scripts/pipeline.py`, `scripts/registry_lib.py`,
`scripts/sync-ai-audit.sh`, all 18 files under `agents/`, both files under `ai-audit/agents/`,
`skills/{analyze,strategize,lit-position,review,write,talk,submit,revise,discover,pipeline,tools}/SKILL.md`,
all 13 files under `skills/pipeline/references/`, and both files under `ai-audit/skills/`.

**`rules/critic-pairing` does not exist.** `tested:` `ls rules/ | grep -i pair` returns nothing.
The only artifacts with that name are `hooks/critic-pairing.py` and the
`critic-pairing-blocked.json` sentinel it writes. Pairing doctrine lives in `rules/agents.md` §1;
pairing *data* lives only in `rules/registry.yaml`.

---

## Executive summary

The **declaration layer is sound**. Every creator has a critic, every critic has a creator, the
registry validates, the weights sum, the component names skills pass are exactly the ones
`pipeline.py` accepts, and `state strike` exists.

The **execution layer is broken in one specific, load-bearing way**: nine of the thirteen
report-producing agents have no tool that can create a file, and six of those are instructed —
inside their own agent file or by the dispatching skill — to write one anyway. The system works
today only because two agents (`writer-critic`, `verifier`) happen to carry `Bash`, and because
one skill (`/review`) happens to spell out that the *orchestrator* saves reports. Everywhere else
the report either errors loudly or evaporates silently, and **nothing downstream notices** —
`record-score` accepts a `--report` path that does not exist, and `pipeline.py post <creator>`
never evaluates a critic's own `produces`.

The peer-review chain (`editor` → two referees → `editor`) is the worst case: **all four of its
declared output files are written by agents that have neither `Write` nor `Bash`**, and Phase 3
requires the editor to *read back* two files its referees could not have produced.

---

## 1. The complete pair matrix

### 1.1 Creators → critic (registry `agents.<name>.critic`)

`per file:` `rules/registry.yaml`, and `tested:` re-derived by running `registry_lib.creators()` /
`critic_of()` against it:

```
  lit-position  -> lit-critic
  explorer      -> explorer-critic
  strategist    -> strategist-critic
  theorist      -> theorist-critic
  data-engineer -> coder-critic
  coder         -> coder-critic
  writer        -> writer-critic
  storyteller   -> storyteller-critic
```

| Creator | `kind` | Critic | Component | Weight | Escalation target | Dispatching skill |
|---|---|---|---|---|---|---|
| `lit-position` | **skill** | `lit-critic` | `literature` | 10 | `user` | `/lit-position` Step 7 |
| `explorer` | agent | `explorer-critic` | `data` | 10 | `user` | `/discover data` Step 6 |
| `strategist` | agent | `strategist-critic` | `strategy` | 25 | `user` | `/strategize` Step 4 |
| `theorist` | agent | `theorist-critic` | `theory` (conditional) | 20 | `user` | `/strategize theory` Step 4 |
| `data-engineer` | agent | `coder-critic` | `code` (`quality_weight: 0`, `scored_under: code`) | 0 | `strategist-critic` | `/analyze` Step 2 |
| `coder` | agent | `coder-critic` | `code` | 15 | `strategist-critic` | `/analyze` Step 3, `/submit package`, `/revise`, `/review --replicate` |
| `writer` | agent | `writer-critic` | `manuscript` | 10 | `user` | `/write` Step 5, `/revise` Step 5 |
| `storyteller` | agent | `storyteller-critic` | `none` | 0 | `writer` | `/talk create` Step 3 |

### 1.2 Critics → creator

| Critic | Pairs with | Report glob it `produces` |
|---|---|---|
| `lit-critic` | `lit-position` | `quality_reports/reviews/lit-critic_*.md` |
| `explorer-critic` | `explorer` | `quality_reports/reviews/explorer-critic_*.md` |
| `strategist-critic` | `strategist` | `quality_reports/reviews/strategist-critic_*.md` |
| `theorist-critic` | `theorist` | `quality_reports/reviews/theorist-critic_*.md` |
| `coder-critic` | **`data-engineer` AND `coder`** | `quality_reports/reviews/coder-critic_*.md` |
| `writer-critic` | `writer` | `writer-critic_*.md` + `claim_evidence_*.md` |
| `storyteller-critic` | `storyteller` | `quality_reports/reviews/storyteller-critic_*.md` |

**No creator lacks a critic. No critic lacks a creator.** `tested:`
`python3 scripts/pipeline.py --root . registry check` →
`PASS [registry-complete] / PASS [registry-authority] / PASS [registry-rendered] /
PASS [weights-sum] / PASS [registry-parse-agree]`, rc=0.

### 1.3 Agents with no pair — by design

`per file:` `rules/agents.md` §1: *"**Peer review** is the one asymmetric structure: the editor
dispatches two blind referees and synthesises a decision. Referees are already reviewers and have
no critic (registry `role: referee`)."*

- `editor` — `role: infrastructure`, `critic: none`, component `referees`
- `domain-referee`, `methods-referee` — `role: referee`, `critic: none`, weight 12.5 each
- `verifier` — `role: infrastructure`, `critic: none`, component `replication`

### 1.4 Agents outside the registry entirely

`claim-verifier` and `humanize-auditor` live in `ai-audit/agents/` and are **not registry
entries**. `per file:` `scripts/pipeline.py:registry_check()` builds its roster as
`roster = {p.stem for p in (root / "agents").glob("*.md")}` — it never globs `ai-audit/agents/`,
so the "exists but is not declared" check cannot see them.

`tested:` they are nonetheless installed into every project:
`ls ~/Research/POGM4/.claude/agents/` shows 20 symlinks, including
`claim-verifier.md -> …/research-claude/ai-audit/agents/claim-verifier.md` and
`humanize-auditor.md -> …/ai-audit/agents/humanize-auditor.md`.

**Consequence:** two of the agents a project can dispatch are outside every pairing, weighting and
completeness check the registry enforces. This is defensible (they are vendored, per
`ai-audit/VENDORED.md`), but it is invisible — `registry check` prints PASS without mentioning
them.

### 1.5 Flag: skills that dispatch one half of a pair

**(a) `/write style-guide` dispatches `writer` with an explicit critic exemption.**
`per file:` `skills/write/SKILL.md:66`: *"`/write style-guide` produces no prose and is the only
exempt mode."*

The exemption exists **only in that sentence**. Neither the hook nor the driver knows about it.

`tested:` starting from a fixture where every component is CLOSED (`next: none — every component
stage is closed`), I logged a single `writer` completion and re-ran `next`:

```
OPEN      manuscript   writer completed at 2026-09-23T23:46:14.538+00:00; no manuscript score after it — dispatch writer-critic and record-score
next: manuscript (writer)
```

`tested:` the same log state makes `critic-pairing.py` emit
`{"decision": "block", … "writer → dispatch writer-critic"}`.

So the one mode that is *supposed* to skip the critic is the one mode that reopens a closed stage
and trips the Stop hook.

**(b) `/review --replicate` dispatches `coder` — a creator — and records no score.**
`per file:` `skills/review/SKILL.md:172-178`: *"Coder re-implements the manuscript's estimation
chunks in `explorations/replicate_<language>.qmd`; coder-critic reviews… Save the replicated script
and comparison report to `quality_reports/reviews/replication_<language>_<date>.md`."* No
`record-score` line appears in that mode. By the mechanism tested in (a), that `coder` dispatch
reopens the `code` stage.

**(c) `/review`, `/review --methods`, `/review --proofread`, `/review --code`, `/review --theory`
dispatch critics with no creator.** By design — `per file:` `rules/agents.md` §4 dispatch table:
`| /review | critics only, by route | — |`.

**(d) `/tools commit` Step 0 dispatches `verifier`** (`per file:` `skills/tools/SKILL.md:55`:
*"Then spawn the **verifier** agent (`Agent`, `subagent_type=verifier`)"*). `verifier` is
infrastructure with `critic: none` — correct, and the Stop hook ignores it.

`tested:` the Stop hook watches creators only. With `editor` and `domain-referee` logged and no
other agent, `critic-pairing.py` produced empty output.

---

## 2. Write capability vs. instruction

### 2.1 The finding, confirmed at the frontmatter level

`per file:` frontmatter `tools:` line of all 20 installed agent files. **No agent whose job is to
produce a review declares `Write`.** Four carry `Bash`, which is the only other way any of them can
create a file.

### 2.2 Per-agent verdict

| # | Agent | Declared `tools:` | Can create a file? | Does its **own agent file** tell it to write? | Verdict |
|---|---|---|---|---|---|
| 1 | `lit-critic` | `Read, Grep, Glob` (+ `mcpServers: zotpilot`) | **No** | **Yes** — §Report names the path | **FAILS** |
| 2 | `explorer-critic` | `Read, Grep, Glob` | **No** | No | **Nothing on disk unless the orchestrator writes it** |
| 3 | `strategist-critic` | `Read, Grep, Glob` | **No** | No | **Nothing on disk unless the orchestrator writes it** (failed today) |
| 4 | `theorist-critic` | `Read, Grep, Glob` | **No** | No | **Nothing on disk unless the orchestrator writes it** |
| 5 | `coder-critic` | `Read, Grep, Glob` | **No** | No | **Nothing on disk unless the orchestrator writes it** (failed today) |
| 6 | `writer-critic` | `Read, Grep, Glob, **Bash**` | **Yes, via Bash** | **Yes** — "Save to …" | **Succeeds — by accident, and against its own rule** |
| 7 | `storyteller-critic` | `Read, Grep, Glob` | **No** | No | **Nothing on disk unless the orchestrator writes it** |
| 8 | `domain-referee` | `Read, Grep, Glob` | **No** | **Yes** — "Write to …" | **FAILS** |
| 9 | `methods-referee` | `Read, Grep, Glob` | **No** | **Yes** — "Write to …" | **FAILS** |
| 10 | `editor` | `Read, Grep, Glob, WebSearch, WebFetch` | **No** | **Yes** — "Write to …" ×2 + "Append to …" | **FAILS (×3)** |
| 11 | `verifier` | `Read, Grep, Glob, **Bash**` | **Yes, via Bash** | **Yes** — "Save to …" | **Succeeds** |
| 12 | `claim-verifier` | `Read, Grep, Glob, WebFetch, WebSearch, **Bash**` | **Yes, via Bash** | No — returns a report | **Correct** |
| 13 | `humanize-auditor` | `Read, Grep, Glob` | **No** | **No — explicitly forbidden** | **Correct by construction** |

### 2.3 The exact wording, per agent file

**Agents told to write, that cannot:**

- `agents/lit-critic.md:29` — *"## Report / `quality_reports/reviews/lit-critic_<date>.md`: score,
  deductions by category with the missing paper named…"*
- `agents/domain-referee.md` §Report format — *"Write to
  `quality_reports/peer_review_[paper]/referee_domain.md`:"*
- `agents/methods-referee.md` §Report format — *"Write to
  `quality_reports/peer_review_[paper]/referee_methods.md`:"*
- `agents/editor.md` §Desk-review output — *"Write to
  `quality_reports/peer_review_[sanitized_paper_name]/desk_review.md`:"*; §Phase 1b — *"Append to
  `desk_review.md`:"*; §Editorial decision output — *"Write to
  `quality_reports/peer_review_[paper]/editorial_decision.md`:"*; §Variance mode — *"write **two**
  files"*

**Agents told to write, that can (via `Bash`):**

- `agents/writer-critic.md:35` — *"## Report / Save to
  `quality_reports/reviews/writer-critic_<date>.md` in the template's report format, with the
  Claim–Evidence Table path."* — **contradicting its own line 18**: *"Eight categories. Scored
  report. **Do NOT edit any file.**"* and line 10: *"You judge and score; you never rewrite a
  section or fix the YAML."*
- `agents/verifier.md` §Report — *"Save to `quality_reports/verification_report.md`."*

**The one agent that gets it right:**

- `ai-audit/agents/humanize-auditor.md` §Output — *"Structured report (the markdown block above) —
  return as your final response. / **Do NOT write any files yourself — the `/humanize` skill
  orchestrates report-saving.**"*

### 2.4 The exact wording, per skill — is it addressing the *agent* or the *orchestrator*?

| Skill | Line | Exact wording | Addressee |
|---|---|---|---|
| `/lit-position` | Step 7 | *"dispatch **lit-critic** … **It** cold-reads the three files, checks coverage…, scores the six categories … and **writes** `quality_reports/reviews/lit-critic_<date>.md`"* | **The agent** — "It … writes". Unambiguous, and wrong. |
| `/discover data` | Step 6 | *"**Save the critic's report to** `quality_reports/reviews/explorer-critic_<date>.md`."* | Ambiguous imperative |
| `/strategize` | Step 7 | *"**Save review to** `quality_reports/reviews/strategist-critic_<date>.md`"* | Ambiguous imperative |
| `/strategize pap` | §Safety and review | *"**Save review to** `quality_reports/reviews/strategist-critic_<date>.md`."* | Ambiguous imperative |
| `/strategize theory` | Step 6 | *"**Save review to** `quality_reports/reviews/theorist-critic_<date>.md`"* | Ambiguous imperative |
| `/analyze` | Step 4 | *"**Report to** `quality_reports/reviews/coder-critic_<date>.md`."* | Ambiguous, and the sentence's subject is coder-critic |
| `/write` | Step 5 | *"Dispatch **writer-critic** … **It produces** a scored report **at** `quality_reports/reviews/writer-critic_<date>.md` and the Claim–Evidence Table at `…/claim_evidence_<project>_<date>.md`."* | **The agent** — "It produces … at \<path\>" |
| `/talk create` | Step 3 | *"**Save report to** `quality_reports/reviews/storyteller-critic_<date>.md`."* | Ambiguous imperative |
| `/review` (comprehensive) | Mode Details 1–3 | *"**Save report to** `quality_reports/reviews/strategist-critic_<date>.md`"* etc. | Ambiguous — **but see below** |
| `/review --peer` | §Save Reports | *"**Save all outputs to** `quality_reports/peer_review_<manuscript-stem>/`: `desk_review.md`, `referee_domain.md`, `referee_methods.md`, `editorial_decision.md`"* | Ambiguous; the agents were separately told to write them |
| `/review --code` | §Code Review | *"**Save report to** `quality_reports/reviews/coder-critic_<date>.md`"* | Ambiguous imperative |
| `/review --methods` | §Causal Audit | *"**Save report to** `quality_reports/reviews/strategist-critic_<date>.md`"* | Ambiguous imperative |
| `/submit package` | — | *"**Save the coder-critic's report to** `quality_reports/reviews/coder-critic_<date>.md`."* | Ambiguous imperative |
| `/humanize` | Steps 4–5 | *"**Receive structured report** from the agent." / "**Write report** to `quality_reports/humanize_<filename>_report.md`."* | **The orchestrator** — explicitly two steps |

**Exactly two places in the whole repo state the contract.** `per file:`

- `skills/review/SKILL.md:45-48` — *"**Save each report the moment its critic returns**, and record
  that score then — not after all three. **Critics are read-only and return their reports as text;
  this session writes them**, so a session that dies before the last critic finishes loses every
  report not yet on disk (observed: strategist-critic done, report unsaved, run lost)."*
- `skills/pipeline/references/adopt.md:56-58` — *"**Save each report and record its score as that
  critic returns**, not after the last one. **Critics are read-only and return reports as text for
  the orchestrating session to write**…"*

Both are buried inside one mode of one skill and one adoption reference. Neither `rules/agents.md`
nor any agent file (other than `humanize-auditor`) carries it.

### 2.5 Which of the thirteen would succeed, fail, or silently produce nothing

**Succeed (2):** `writer-critic`, `verifier` — both by `Bash`, which they were given for render
checks, not for authoring. `writer-critic` succeeding is why today's run looked partially healthy.

**Fail loudly (whenever the dispatch prompt repeats a save path) (4 agents / 6 files):**
`lit-critic`, `domain-referee`, `methods-referee`, `editor`. These carry the write instruction in
their **own** file, so the agent will attempt `Write` on every run and hit "the Write tool is
disabled" — the same failure mode observed today for `coder-critic` and `strategist-critic`.

**Silently produce nothing (5):** `explorer-critic`, `strategist-critic`, `theorist-critic`,
`coder-critic`, `storyteller-critic`. Their agent files name **no** output path — they say only
*"Produce a scored report"* / *"Report only"* / *"**Do NOT edit any files**"*. Whether they error
or vanish depends entirely on whether the orchestrator pastes the skill's `Save report to <path>`
line into the dispatch prompt. Today's outcome (`coder-critic` and `strategist-critic` both hit
"the Write tool is disabled") shows the orchestrator **is** pasting it — which converts a silent
failure into a loud one, but produces a report file in neither case.

**Correct (2):** `claim-verifier` (has `Bash`, told to return text, skill writes),
`humanize-auditor` (no write tool, told not to write, skill writes).

### 2.6 The registry asserts a capability these agents do not have

`per file:` every critic entry in `rules/registry.yaml` carries:

```yaml
    writes:
      - quality_reports/reviews/
```

and `editor`, `domain-referee`, `methods-referee` carry `writes: - quality_reports/peer_review_`.
`per file:` `scripts/pipeline.py` uses `writes` only for `pipeline.py conflicts` (set intersection
between agents). Nothing cross-checks `writes` against the agent's declared `tools:`. The registry
therefore documents a write capability that nine agents provably lack, and `registry check` passes.

### 2.7 Nothing downstream notices a missing report

`tested:` `record-score` accepts a `--report` path that does not exist:

```
$ python3 .claude/scripts/pipeline.py --root . state record-score literature 85 --critic lit-critic --report r.md
recorded literature=85.0
$ ls r.md
ls: r.md: No such file or directory
$ # state now holds:
literature entry: {'score': 85.0, 'critic': 'lit-critic', 'report': 'r.md', 'at': '…', 'rounds': 1}
```

`tested:` `post <creator>` never evaluates the critic's own `produces`. With `coder` and
`coder-critic` both logged and a fresh `code` score, `post coder` reports
`ok critic-ran: coder-critic after coder, code scored at …` while
`quality_reports/reviews/` does not exist at all. Only `post coder-critic` — **which no skill ever
calls** (`per file:` `skills/pipeline/SKILL.md:50`: `post <creator>`) — catches it:

```
$ python3 .claude/scripts/pipeline.py --root . post coder-critic
MISSING path quality_reports/reviews/coder-critic_*.md (0 found, need 1)
post coder-critic: FAIL
```

**This is the integrity hole.** A critic that produced no file still closes its creator's stage,
and the state file records a dangling `report:` path as the audit trail.

---

## 3. Score recording

### 3.1 Component names — exact match, all eight

`per file:` `rules/registry.yaml` declares eight components:
`literature, data, strategy, theory, code, manuscript, referees, replication`.

`tested:` every component name any skill passes is accepted, with the critic the skill names:

```
literature  / lit-critic        -> recorded literature=85.0   (rc=0)
data        / explorer-critic   -> recorded data=85.0         (rc=0)
strategy    / strategist-critic -> recorded strategy=85.0     (rc=0)
theory      / theorist-critic   -> recorded theory=85.0       (rc=0)
code        / coder-critic      -> recorded code=85.0         (rc=0)
manuscript  / writer-critic     -> recorded manuscript=85.0   (rc=0)
referees    / editor            -> recorded referees=85.0     (rc=0)
replication / verifier          -> recorded replication=85.0  (rc=0)
```

**No mismatch. No skill records a component the registry does not weight. No weighted component
lacks a recording skill.** Mapping, `per file:`

| Component | Weight | `scored_by` | Recorded by |
|---|---|---|---|
| `literature` | 10 | `lit-critic` | `/lit-position` Step 7 |
| `data` | 10 | `explorer-critic` | `/discover data` Step 6 |
| `strategy` | 25 | `strategist-critic` | `/strategize` Step 4, `/review` (comprehensive), `/pipeline` review stage |
| `theory` | 20 (conditional) | `theorist-critic` | `/strategize theory` Step 4 |
| `code` | 15 | `coder-critic` | `/analyze` Steps 2–3, `/submit package`, `/revise`, `/review --code <manuscript>` |
| `manuscript` | 10 | `writer-critic` | `/write` Step 5 (`--scope section:`), `/write humanize`, `/review`, `/revise` |
| `referees` | 25 | `editor` | `/review --peer` Phase 3 |
| `replication` | 5 | `verifier` | `/review` (comprehensive), `/submit audit`, `/submit final` |

### 3.2 Self-scoring is genuinely blocked

`tested:`

```
$ … state record-score code 100 --critic coder --report r.md
record-score: code is scored by coder-critic, not coder (see .claude/rules/registry.yaml)   rc=1
$ … state record-score manuscript 100 --critic domain-referee --report r.md
record-score: manuscript is scored by writer-critic, not domain-referee …                   rc=1
```

`tested:` an unknown component is rejected:
`… state record-score talk 85 --critic storyteller-critic …` → `record-score: bad component or score`, rc=1.
(`storyteller` is `component: none` and correctly records nothing — `per file:`
`skills/pipeline/references/talk.md:19-21`.)

### 3.3 Minor issues in this area

- **`--deductions` is omitted for `replication` and `referees`.** `per file:`
  `skills/review/SKILL.md:42` and `:95`. Harmless for `replication` (0/100 by construction) but
  a floored `referees` score will print `deduction_note`'s *"(floored — deductions not recorded)"*
  — the exact case `pipeline.py`'s docstring says is *"where the ranking was lost."*
- **`data-engineer` carries an undeclared key `scored_under: code`.** `per file:`
  `rules/registry.yaml:257`. `registry_lib.FIELDS` does not list `scored_under`, and
  `validate_registry` only checks for *missing* fields, so the key is silently unvalidated and
  read by nothing in `pipeline.py`.
- **One `coder-critic` run closes both `data-engineer` and `coder`.** `tested:` with
  `data-engineer`, `coder`, `coder-critic` logged in that order, `critic-pairing.py` produced
  empty output — both creators counted as paired. This is documented (`per file:`
  `skills/pipeline/references/analyze.md:10-13`, `skills/pipeline/references/adopt.md:80-81`) but
  it means a `data-engineer` round can be closed by a critic that only read `coder`'s chunks.

---

## 4. The strike / escalation path

### 4.1 It exists and counts

`tested:`

```
$ … state strike strategist   (×4)
strategist: strike 1 of 3
strategist: strike 2 of 3
strategist: strike 3 of 3 — ESCALATE to user
strategist: strike 4 of 3 — ESCALATE to user
```

`per file:` `scripts/pipeline.py:488-491` — the whole implementation:

```python
if a.op == "strike":
    cr = a.args[0]; n = stt["strikes"].get(cr, 0) + 1; stt["strikes"][cr] = n; save_state(root, stt)
    lim = int(reg["limits"]["rounds_per_pair"])
    print(f"{cr}: strike {n} of {lim}" + (f" — ESCALATE to {reg['agents'][cr]['escalation_target']}" if n >= lim else "")); return 0
```

### 4.2 The escalation is **printed, not enforced**

`tested:` strike 4 of 3 is accepted and returns rc=0. There is no gate, no non-zero exit, no
`blocked_by`, no refusal of a fourth round. The counter and the message are implemented; the
*escalation* is a string the orchestrator is trusted to act on.

`per file:` **`limits.rounds_overall: 5` and `limits.verification_retries: 2` are read by
nothing.** `grep -n "rounds_per_pair\|rounds_overall\|verification_retries"` across
`scripts/pipeline.py`, `scripts/registry_lib.py` and `hooks/*.py` returns exactly one hit:
`scripts/pipeline.py:490: lim = int(reg["limits"]["rounds_per_pair"])`. `/pipeline` advertises them
(`per file:` `skills/pipeline/SKILL.md:57`: *"Limits: 3 rounds per pair, 5 overall, 2 verification
retries (`registry.yaml: limits`)"*) — two of the three are decoration.

### 4.3 The agent names skills pass are accepted — but only four creators are ever struck

`tested:` `state strike` on registry creators works (`strategist`, `lit-position`, `coder`,
`writer` all accepted).

`per file:` every `state strike` occurrence in the repo:

| Skill | Line | Creator struck |
|---|---|---|
| `skills/lit-position/SKILL.md` | 121 | `lit-position` |
| `skills/strategize/SKILL.md` | 45, 105 | `strategist` |
| `skills/analyze/SKILL.md` | 38 | `coder` |
| `skills/write/SKILL.md` | 66, 111 | `writer` |
| `skills/pipeline/SKILL.md` | 51 | `<creator>` (generic, driver-only) |

**Four of the eight creators are never struck by any skill:** `explorer`, `theorist`,
`data-engineer`, `storyteller`. Their skills describe the three-round rule in prose without the
command — `per file:` `skills/strategize/SKILL.md:143`: *"If CRITICAL issues found, iterate (max 3
rounds per three-strikes). Escalation target: User."*; `skills/talk/SKILL.md:80`: *"Re-dispatch
Storyteller with specific fixes (max 3 rounds per three-strikes rule)"*; `/discover data` Step 6
mentions no rounds at all. Their strike counters stay at zero forever, so their escalations never
fire.

### 4.4 `strike` accepts any string, and crashes at the escalation boundary

`tested:` a name that is **not** a registry agent is accepted for two strikes and then throws an
unhandled `KeyError` — at exactly the moment escalation is due:

```
$ … state strike lit-review
lit-review: strike 1 of 3
$ … state strike lit-review
lit-review: strike 2 of 3
$ … state strike lit-review
lit-review: strike 1 of 3      ← (state already saved)
Traceback (most recent call last):
  File ".../pipeline.py", line 491, in main
    print(f"{cr}: strike {n} of {lim}" + (f" — ESCALATE to {reg['agents'][cr]['escalation_target']}" …))
KeyError: 'lit-review'
```

`save_state()` runs **before** the crash, so the bad key is persisted. `tested:` this poisons the
state file permanently:

```
$ python3 .claude/scripts/pipeline.py --root . state validate
    strikes.lit-review: not a registry agent
state: INVALID          rc=1
```

`per file:` `skills/pipeline/SKILL.md:42`: *"state init (no-op if present); **state validate
(refuse on INVALID)**"*. One typo'd `state strike` name therefore bricks `/pipeline run` until a
human hand-edits `pipeline_state.json` — and there is no command to remove a strike.

`tested:` `state strike writer-critic` (a **critic**, not a creator) is also accepted and reaches
`strike 3 of 3 — ESCALATE to user`, because critics carry `escalation_target: user`. Striking a
critic is meaningless but indistinguishable from striking a creator.

---

## 5. Hook wiring: what the two hooks detect, and what they cannot

### 5.1 Both hooks are wired everywhere

`per file:` `seeds/settings.json` wires `dispatch-log.py` on `SubagentStop` and
`critic-pairing.py` on `Stop`. `tested:` all six live projects have both:

```
~/Research/BRI                    critic-pairing:YES dispatch-log:YES
~/Research/ESG                    critic-pairing:YES dispatch-log:YES
~/Research/NAR_settlement         critic-pairing:YES dispatch-log:YES
~/Research/POGM4                  critic-pairing:YES dispatch-log:YES
~/Research/affordable_housing_2026 critic-pairing:YES dispatch-log:YES
~/Research/zoning2026             critic-pairing:YES dispatch-log:YES
```

### 5.2 `dispatch-log.py` — what it does

`tested:` on a `SubagentStop` payload it appends one line:

```json
{"at": "2026-09-23T23:43:17.581+00:00", "agent": "coder", "session": "S1", "source": "hook"}
```

`tested:` it accepts `agent_type`, `agent_name` **and** `subagent_type` (a payload carrying only
`subagent_type: writer` logged correctly). `tested:` a payload with none of the three appends
nothing and exits 0.

**What it cannot do:** it records *that a subagent named X stopped*. It records nothing about what
X produced, whether X succeeded, whether X was dispatched for the artifact the stage is about, or —
critically — anything at all about a **skill**. `lit-position` is `kind: skill` and never goes
through the `Agent` tool, so it is logged only if the skill itself runs
`pipeline.py log lit-position` (`per file:` `skills/lit-position/SKILL.md:115`;
`skills/pipeline/references/literature.md:20-22`: *"orchestrated runs still need that log entry for
`post`'s `critic-ran` check, so confirm it happened before trusting `post`"*).

`tested:` the `pipeline.py log` path writes **no** `session` key —
`['agent', 'at', 'source']` — which `critic-pairing.py` deliberately treats as belonging to every
session (`per file:` its docstring, R-113).

### 5.3 `critic-pairing.py` — precisely what it detects

`per file:` lines 68-77, the entire detection:

```python
for creator in rl.creators(reg):
    crit = rl.critic_of(reg, creator)
    if not crit: continue
    last_c = max((e["at"] for e in entries if e.get("agent") == creator), default=None)
    last_k = max((e["at"] for e in entries if e.get("agent") == crit), default=None)
    if last_c and (last_k is None or last_k < last_c):
        unpaired.append((creator, crit))
```

**It detects exactly one thing:** for each of the eight registry creators, whether the timestamp of
its critic's most recent log line is older than (or missing relative to) its own.

`tested:` with `coder` and `writer` logged and no critics:

```json
{"systemMessage": "⚠ Creator ran without its critic this session: coder → dispatch coder-critic; writer → dispatch writer-critic. …",
 "hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": "…"},
 "decision": "block", "reason": "…"}
```

`tested:` blocks **once**, then goes advisory — second run in the same session dropped
`"decision"` and kept only the message. `tested:` `stop_hook_active: true` short-circuits to empty
output. `tested:` after logging both critics, output is empty.

`tested:` with **no** `session_id`, it blocks on every single Stop and never writes a sentinel —
three consecutive runs all returned `decision: block`, and the sentinel file written was from the
*earlier* keyed run. This is deliberate and documented in the code (Finding 2 comment, lines
83-88), but it means a payload without a session id turns an advisory-after-one hook into an
unconditional blocker.

### 5.4 What `critic-pairing.py` cannot detect

1. **Whether the critic produced anything.** It never opens `quality_reports/reviews/`. `tested:`
   with `coder` + `coder-critic` logged and no `quality_reports/reviews/` directory at all, the
   hook is silent.
2. **Whether a score was recorded.** It never reads `pipeline_state.json`. A critic that ran and
   scored nothing looks identical to one that scored correctly.
3. **Which creator the critic reviewed.** `tested:` one `coder-critic` line clears both
   `data-engineer` and `coder`.
4. **A creator that was never logged.** `lit-position` is a skill; if `/lit-position` skips its
   `pipeline.py log` call, the hook has nothing to compare and reports nothing. The creator most
   likely to be run outside the orchestrated loop is the one the hook is blindest to.
5. **A referee or the editor that skipped its counterpart.** `tested:` `editor` and
   `domain-referee` logged alone → silent output. Only `role: creator` entries are iterated, so the
   entire peer-review chain is outside the hook.
6. **A legitimate exemption.** `tested:` `/write style-guide` (explicitly critic-exempt) trips the
   block.
7. **Anything after the session ends.** It is a `Stop` hook; a session that never stops, or that is
   killed, never runs it.
8. **A stale critic run.** It compares only the *last* completion of each. A critic that ran early,
   then the creator ran twice more, then the critic ran once — the last critic line postdates the
   last creator line and the pair reads clean.

`per file:` `rules/agents.md` §1 is candid about the enforcement hierarchy and is accurate:
*"These are not three equal gates. Only the first refuses anything. … It blocks **once per creator
per session**, then goes advisory, so a session can pass it by stopping twice. … it means the hook
makes a session *notice*, it does not make a session *comply*."* And: *"Note that nothing forces
`pipeline.py post` to be *called*. A session that never runs it is never gated."*

---

## Prioritized defect list

### D-1 (CRITICAL) — The entire peer-review chain cannot write any of its four outputs

`editor`, `domain-referee` and `methods-referee` declare `Read, Grep, Glob` (+ `WebSearch`,
`WebFetch` for the editor) and are each instructed **in their own agent file** to `Write to` a
path. Four declared `produces` entries in the registry (`desk_review.md`, `referee_domain.md`,
`referee_methods.md`, `editorial_decision.md`) are therefore unproducible by the agents that own
them. Worse, `editor` Phase 3 is defined as *"After Referee A (domain) and Referee B (methods) have
both written their reports (`referee_domain.md`, `referee_methods.md`), you read both"* — a read of
files that cannot exist. `referees` carries **25% of the quality weight**, the joint-largest.
`/review --peer` says only *"Save all outputs to …"* without naming who saves them.

### D-2 (CRITICAL) — A critic that produced no report still closes its creator's stage

`tested:` `record-score` accepts a non-existent `--report` path; `post <creator>` evaluates the
creator's `produces` plus `critic-ran`, and `critic-ran` checks only the **dispatch log timestamp**
and the **score timestamp** — never the report file. The critic's own `produces` (the report glob)
is evaluated only by `post <critic>`, which no skill ever calls. Result: the state file's
`report:` field is an unverified string, and the pipeline's single hard gate can pass on a stage
whose review exists nowhere but in a subagent transcript that has already been discarded.

### D-3 (HIGH) — Nine agents are told to write and cannot; the contract is stated in only two places

`lit-critic`, `explorer-critic`, `strategist-critic`, `theorist-critic`, `coder-critic`,
`storyteller-critic`, `domain-referee`, `methods-referee`, `editor` all lack `Write` and `Bash`.
Ten skill call-sites say "Save report to \<path\>" without an addressee, and two
(`/lit-position` Step 7, `/write` Step 5) name the **agent** as the writer. The correct pattern
exists and is proven — `humanize-auditor` + `/humanize` Steps 4–5 — but is used nowhere in the core
pipeline. The two statements of the real contract are buried in `skills/review/SKILL.md:45-48` and
`skills/pipeline/references/adopt.md:56-58`.

### D-4 (HIGH) — The system's apparent health depends on two accidents

`writer-critic` and `verifier` carry `Bash` (given for render checks) and are the only report
producers that work. `writer-critic` does so **in direct violation of its own line 18** (*"Do NOT
edit any file"*) and line 10 (*"you never rewrite a section or fix the YAML"*). Any future
tightening of `writer-critic`'s tools to match its stated role silently breaks the `manuscript`
component.

### D-5 (HIGH) — `state strike` with an unknown name persists bad state and then crashes

`tested:` strikes 1 and 2 are accepted and saved for any string; strike 3 raises an unhandled
`KeyError` **after** `save_state()`. `state validate` then reports INVALID, and `/pipeline run`
*"refuse[s] on INVALID"* — with no command to remove a strike. A single typo bricks the driver.

### D-6 (MEDIUM) — Three-strike escalation is a printed string, not a gate

`tested:` `strike 4 of 3 — ESCALATE to user` is accepted, rc=0. `rounds_overall: 5` and
`verification_retries: 2` are declared in the registry and advertised by `/pipeline` but read by no
code anywhere in the repo.

### D-7 (MEDIUM) — Four of eight creators never get a strike recorded

`explorer`, `theorist`, `data-engineer` and `storyteller` are described as three-strike-governed in
prose but no skill issues `pipeline.py state strike` for them. Their counters stay at zero, so the
escalation targets the registry declares for them (`user`, `user`, `strategist-critic`, `writer`)
can never be reached through the counter.

### D-8 (MEDIUM) — `/write style-guide`'s critic exemption is invisible to the machinery

`tested:` logging `writer` alone flips `manuscript` from CLOSED to OPEN (`next: manuscript
(writer)`) and makes `critic-pairing.py` emit a block. The exemption lives in a single clause of
`skills/write/SKILL.md:66` and nothing else knows it. `/review --replicate` has the same shape:
it dispatches `coder` and records no `code` score.

### D-9 (MEDIUM) — The registry declares `writes:` for agents that cannot write

Every critic entry carries `writes: - quality_reports/reviews/`; the referees and editor carry
`writes: - quality_reports/peer_review_`. Nothing cross-checks `writes` against the agent file's
`tools:`, so `registry check` prints `PASS [registry-complete]` over nine false capability claims.
A `writes`-vs-`tools` check is the cheapest mechanical fix for D-1/D-3.

### D-10 (LOW) — `critic-pairing.py` is blind to the creator most likely to skip its critic

`lit-position` is `kind: skill`, so nothing logs it automatically; if the skill's
`pipeline.py log lit-position` call is missed, the hook reports nothing. The hook is also blind to
all referees and the editor, to whether any report or score exists, and to which of
`data-engineer`/`coder` a given `coder-critic` run actually reviewed.

### D-11 (LOW) — A Stop payload without `session_id` blocks unconditionally

`tested:` three consecutive runs with no `session_id` all returned `decision: block` and no
sentinel was written. Documented in the code as deliberate, but it converts "block once, then
advisory" into a hard loop for any host build that omits the field.

### D-12 (LOW) — Two installed agents are outside the registry

`claim-verifier` and `humanize-auditor` are symlinked into every project's `.claude/agents/` but
`registry_check()` globs only `<root>/agents/*.md`, so neither the "declared but missing" nor the
"exists but not declared" check sees them. They are correctly built (D-3's model), but they are
governed by nothing.

### D-13 (LOW) — `data-engineer` carries an unvalidated `scored_under: code` key

Not in `registry_lib.FIELDS`, not read by `pipeline.py`, not checked by `validate_registry`. It
documents a real constraint (`tested:` one `coder-critic` run closes both creators) that only prose
enforces.

---

## What was verified clean

- Registry completeness, authority, rendering, weight sums and PyYAML parse agreement: all PASS.
- All eight component names and their `scored_by` critics: exact match between skills, registry and
  `pipeline.py`.
- Creator self-scoring: genuinely refused.
- `dispatch-log.py`: correct timestamp format, three input-key aliases, fails open.
- `critic-pairing.py`: correct detection of its one condition, correct block-once semantics,
  correct `stop_hook_active` guard, fails open.
- Both hooks wired in all six live projects.
