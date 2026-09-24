# Forensic delivery audit — the 2026-09-15/16 skill-defect closeout

**Date:** 2026-09-23
**Auditor:** Claude Opus 5 (read-only forensic pass; nothing was fixed)
**Repo:** `/Users/andrew.mueller/Academic/research-claude`
**Branch at audit time:** `jrer-rebase`

## Question

Did the 2026-09-15/16 skill-defect closeout deliver what it promised?

## Scope

- The 41 commits in `git log --since=2026-09-14 --until=2026-09-17`
- `docs/plans/2026-09-16-skill-defect-closeout.md` (1,524 lines / 79,723 bytes)
- `docs/plans/2026-09-16-skill-token-optimization.md` (81,484 bytes)
- `docs/audits/2026-09-15_skill-best-practices-audit.md` (37,702 bytes)

## Evidence rules used in this audit

Every claim below is labelled:

- `tested:` — I ran the command or the script and read its output in this session.
- `per file:` — I read the file (to EOF, or the named chunk range) in this session.
- `unverified:` — asserted by a commit message or a plan, not independently confirmed. Nothing is built on these.

A commit message is **never** treated as evidence of current state. A grep hit is a
locator, never evidence. Both plans were read in full, in successive chunks to EOF;
the reading log is in the appendix.

---

*(sections appended below as the audit proceeded)*
## 0. Reading log

`per file:` I read both plans in full, in successive chunks, to end-of-file:

| File | Lines | Read as |
|---|---|---|
| `docs/plans/2026-09-16-skill-defect-closeout.md` | 1,524 | 1–260, 260–560, 560–860, 860–1180, 1180–1524 (EOF) |
| `docs/plans/2026-09-16-skill-token-optimization.md` | 1,561 | 1–240, 240–600, 600–1000, 1000–1330, 1330–1561 (EOF) |
| `docs/audits/2026-09-15_skill-best-practices-audit.md` | 314 | in full |

No claim in this audit rests on a grep hit. Every classification below was
established by reading the current file or running the current code.

---

## 1. The two plans, as written

`per file:` The two plans are **not** one body of work. They are sequential and the
second is the successor of the first.

| | Token-optimization plan | Defect-closeout plan |
|---|---|---|
| Header goal | "Cut the SKILL.md body text … by ~40%, bind every bundled reference file to the step that needs it" | "Close the Medium- and Low-severity defects that [the audit] §4 recorded and the token-optimization plan deliberately left open" |
| Tasks | 0–8 (nine) | 0–7 (eight) |
| Checkbox steps | 81 | 72 |
| Checkboxes ticked | **0** | **0** |
| Progress-Log rows marked `done` | **9 of 9** | **1 of 8** |
| Close-out commit | `66ca1cb` "docs: close out the skill token optimization plan" | none |

The closeout plan's own header states the relationship: *"**Predecessor:**
`docs/plans/2026-09-16-skill-token-optimization.md` (Tasks 0–8, all done, closed out
in `66ca1cb`)."*

**This distinction governs the whole audit.** The prompt's framing — "1,524 lines,
72 items, ZERO ticked" — is exactly right for the closeout plan, and the finding
below is that the closeout plan is almost entirely unexecuted. The
token-optimization plan, by contrast, was executed nearly in full. Its checkboxes
are also all unticked, because in **both** plans the checkboxes are declared
working notes and the Progress Log table is declared the handoff:

> *"The executor appends one row per completed task. The checkboxes inside a task
> are working notes; this table is the handoff."* — both plans, `## Progress Log`

So zero ticked checkboxes is **not** by itself evidence of no work. The Progress
Log is. And the two Progress Logs tell opposite stories.

---

## 2. The progress-tracking mechanism — the central finding

### 2.1 What the mechanism is

`per file:` Neither plan uses its checkboxes. Both declare a **prose status table**
(`## Progress Log`) as the authoritative handoff, and both say so in the same words.
The closeout plan's table has eight rows (Tasks 0–7). Its first row reads:

> `| 0 — Land the pending `new-project-ztp` edit; baseline | done | `fix/new-project-ztp-registration` | yes (`b0a95af`) | …`

followed by a ~1,400-character verification note recording that both mechanisms in the
pending edit were checked against the installed build, that two draft claims were dropped
as wrong, that the suite was `159 passed, 3 subtests`, and the nine-skill character
baseline.

`tested:` **That row is the only row ever marked `done`.** Rows 1–7 all read
`not started` with empty Branch, Merged and Notes cells. It was written by commit
`3ad638e` ("docs: record Task 0 in the defect close-out progress log"), whose entire
diff is `docs/plans/2026-09-16-skill-defect-closeout.md` and nothing else. `3ad638e` is
the **last commit in the window** — the plan's tracking stopped at the same moment it
started.

### 2.2 How many tasks, how many performed, how many unrecorded

| | Closeout plan | Token-optimization plan |
|---|---|---|
| Tasks defined | 8 (Tasks 0–7) | 9 (Tasks 0–8) |
| Checkbox steps defined | 72 | 81 |
| Tasks recorded `done` in the Progress Log | **1** | **9** |
| Tasks actually performed (judged by commits + current file state) | **1** | **9** |
| **Work performed but never recorded** | **0** | **0** |

`tested:` **The gap the prompt asks about — work done but untracked — is zero, in both
plans.** This is worth stating plainly because it inverts the natural reading of "72
items, zero ticked". The closeout plan is not a case of work that happened and went
unrecorded. It is a case of **work that never happened at all**, recorded accurately as
not having happened. The tracking table is the one artifact in this whole review that is
completely truthful.

The supporting evidence is unusually clean:

1. `tested:` `git log --since=2026-09-17` — there are **no commits at all** between
   `3ad638e` (2026-09-16) and `15fabeb` (2026-09-23). Seven days with an empty log.
2. `tested:` Measuring every `skills/*/SKILL.md` body the way the plan's own Task 0
   script does, **all nine baselined skills are byte-identical in size to the baseline**
   (drift = 0) except `tools`, and `tools` changed on **2026-09-23** in `15fabeb` /
   `e285f9d` / `07aa079` — today's unrelated gate work, not closeout Task 4.
3. `tested:` All six test files the closeout plan specifies verbatim are **absent**:
   `test_review_modes.py`, `test_revise_contracts.py`, `test_strike_ownership.py`,
   `test_tools_contracts.py`, `test_zotpilot_skills.py`,
   `test_low_severity_contracts.py`. So is the one file it specifies creating,
   `skills/review/templates/variance-mode.md`.
4. `tested:` Both **Open decisions** cells (D2, D3) are still empty. Task 1 Step 2 and
   Task 6 Step 2 each require putting a decision to the user *before writing anything*.
   Neither was ever asked.
5. `tested:` `docs/SESSION_REPORT.md`'s last entry is
   `## 2026-09-16 — Skill token optimization: Tasks 0–8 complete`. There is no closeout
   entry, which is Task 7's sole deliverable.
6. `tested:` `KNOWN_UNBOUND` in `tests/test_skill_contracts.py` still holds all five
   entries. Closeout constraint 8 says Tasks 2 and 4 remove three of them.

### 2.3 The one thing that *was* recorded, and it holds up

`tested:` Task 0's deliverable is real. `skills/new-project-ztp/SKILL.md` — which the
plan describes as having sat uncommitted and **live in all six linked papers** — was
committed in `ed57b0f` (17 insertions, 4 deletions) and merged in `b0a95af`. The file
is committed and the working tree is clean for it. Its recorded body size (3,966 chars)
reproduces exactly today.

Two observations on that row, both in its favour and one against:

- **In its favour:** the note is a model of the discipline the repo's own rules demand.
  It records that the edit's two claims were checked **against the installed build, not
  the vendored text**, names the commands, and says that two draft claims were found
  wrong and dropped before landing. It also reports a finding that *contradicts the
  source audit* — that the vendored `ztp-setup` step 5 and the audit's "still open"
  row on it are stale.
- **Against:** it is the plan's own baseline row. `per file:` Task 0's Step 4 is a
  measurement, and its only functional change is landing a diff that already existed in
  the working tree before either plan began. **The closeout plan's single completed task
  is the one that was already done when the plan was written.** Nothing from Tasks 1–7
  — the actual defect work the plan exists for — was attempted.

---

## 3. Token counts: the numeric claims, re-measured

`tested:` I re-ran the plan's own measurement script (strip the frontmatter with
`re.sub(r'^---\n.*?\n---\n', '', …, count=1, flags=re.S)`, count characters of the
remaining body) over every `skills/*/SKILL.md` today.

### 3.1 The nine baselined skills

| Skill | Baseline (closeout Task 0, 2026-09-16) | Today | Drift |
|---|---|---|---|
| review | 10,878 | 10,878 | **0** |
| revise | 4,109 | 4,109 | **0** |
| tools | 4,347 | **6,924** | **+2,577** |
| promote | 3,176 | 3,176 | **0** |
| lit-position | 6,093 | 6,093 | **0** |
| ztp-data-tag | 9,173 | 9,173 | **0** |
| pipeline | 4,183 | 4,183 | **0** |
| write | 7,482 | 7,482 | **0** |
| new-project-ztp | 3,966 | 3,966 | **0** |
| **All 18** | **98,894** | **101,471** | **+2,577** |

**Every character of the +2,577 is `tools`, and none of it is the closeout plan's.**
`tested:` `git log -- skills/tools/SKILL.md` shows the file untouched between
`fb457c9` (2026-09-16, the predecessor's Task 8) and `15fabeb` (2026-09-23). The growth
is today's blocking-commit-gate work. Closeout Task 4 — which would have *changed*
`tools` for entirely different reasons — never ran.

Eight of nine baselined skills are unchanged to the character. That is the same finding
as §2.2 arriving by a second, independent route.

### 3.2 Did the predecessor plan's claimed reductions hold?

The token plan's Task 8 close-out note claims: *"five skills 63,573 → 37,756 (−41%,
target ≤38,000 ✓); all 18 121,621 → 98,672; one `/pipeline run` 73,176 → 50,819
(~18.3k → ~12.7k tok, −31%)."*

`tested:` **They hold. Every one of them.**

| Skill | Pre-refactor baseline | Claimed after | Measured today | Budget cap | Verdict |
|---|---|---|---|---|---|
| review | 18,058 | 10,878 | **10,878** | 11,000 | holds |
| strategize | 15,966 | 7,967 | **7,967** | 8,000 | holds |
| write | 11,290 | 7,482 | **7,482** | 7,500 | holds |
| discover | 9,733 | 5,934 | **5,934** | 6,000 | holds |
| checkpoint | 8,526 | 5,459 | **5,495** | 5,500 | holds (see below) |
| **Five-skill total** | **63,573** | **37,756** | **37,756** | ≤38,000 | **−40.6% ✓** |
| **`/pipeline run` (8 skills)** | 73,176 | 50,819 | **50,819** | — | **−30.6% ✓** |

`per file:` The one apparent discrepancy — `checkpoint` at 5,495 rather than the
recorded 5,459 — is internally consistent, not drift. Task 7 measured 5,459; Task 8
then added the improvement-candidate lines to the same file (`fb457c9`), costing 36
chars. `tested:` Both lines are present (`skills/checkpoint/SKILL.md:75` and `:123`) and
the file is still under its 5,500 cap. The Task 8 note's "all 18 = 98,672" likewise
differs from the closeout's "98,894" by 222 chars, which is `ed57b0f`'s
new-project-ztp edit (+17/−4 lines) landing after Task 8 measured.

`tested:` The **ratchets that lock these numbers in are real and enforcing.** The full
suite runs **175 passed, 3 subtests** with exit 0, including
`test_refactored_skills_stay_under_budget` and
`test_every_bundled_file_is_bound_to_a_step_or_an_agent`. `tested:`
`./scripts/check_fork.sh` → `✓ check_fork: PASS`, exit 0.

**Conclusion on the numbers: the token-optimization plan's numeric claims are accurate,
reproducible seven days later, and mechanically defended.** This is the strongest part
of the whole body of work, and it is the *predecessor* plan, not the one under audit.

---

## 4. The promise-by-promise ledger

Every CURRENT STATE cell below was established by reading the named file in this
session or running the named command — never from a commit message.

### 4.1 Closeout plan (`2026-09-16-skill-defect-closeout.md`) — 8 tasks

#### Task 0 — land the pending `new-project-ztp` edit; baseline

| Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|
| *"it replaces the false claim that `/ztp-setup` registers the MCP server in a project `.mcp.json` with client-level registration, and points API keys at `~/.secrets.env` instead of `config.json`"* | `ed57b0f` / merge `b0a95af` | `per file:` `skills/new-project-ztp/SKILL.md` is committed, tree clean, body 3,966 chars = the recorded baseline. | **LANDED-AND-WORKS** |
| *"Paste the rows … into the Progress Log. Task 7 re-runs this."* | `3ad638e` | `tested:` The nine baseline figures are in the Progress Log and all nine reproduce today. Task 7 never re-ran them. | **LANDED-AND-WORKS** (the re-run is Task 7's failure, not this one's) |

#### Task 1 — `review`: `--theory`, `--variance`, the `--peer` score, `--stress`

`per file:` `skills/review/SKILL.md` read in full (10,878-char body, 8 mode sections).

| Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|
| *"Add the `--theory` mode section … dispatch **theorist-critic** standalone … record `record-score theory`"* | none | `--theory` appears **only** in `argument-hint` (line 4) and one routing line (line 28). `## Mode Details` holds Comprehensive, `--peer`, `--r2`, `--stress`, `--code`, `--methods`, `--proofread`, `--replicate` — **no `--theory` section, no dispatch, no `record-score theory`.** A weight-20 component (`rules/registry.yaml`) still has no critic-only route, while `pipeline/references/adopt.md` routes to it. | **NEVER-LANDED** |
| *"add `--variance N` to `argument-hint`; add one routing line … add a short `#### Variance Mode (--variance N)` subsection … **enforces the conflict rule**"* | none | `tested:` `grep -c variance skills/review/SKILL.md` → **0**; `agents/editor.md` → **8**. `agents/editor.md:124` still delegates the flag-conflict halt to a skill that has never heard of the flag. | **NEVER-LANDED** |
| *"Create `skills/review/templates/variance-mode.md`"* | none | `tested:` file **absent**. | **NEVER-LANDED** |
| *"State in the `--stress` section that it **records no score** … Make sure no `record-score referees` line is reachable from the `--stress` path"* | none | `per file:` `--stress` still reads *"Same three-phase flow as `--peer`"* (line 120) with no exception, and `--peer` Phase 3 still carries `record-score referees …/editorial_decision.md` (line 95) — a file the editor's stress mode does not write. | **NEVER-LANDED** |
| *"add an `## Editor (Peer Review Synthesis)` section to `skills/review/config/scoring-rubrics.md`"* (D3(a)) | none | `per file:` rubric headings are Writer-, Coder-, Strategist-, Theorist-, Storyteller-, Explorer-, Lit-Critic and Quality Gates. **No Editor section.** `referees` (weight 25) still has no defined source. D3 was never put to the user. | **NEVER-LANDED** |
| *"Add Theory … and Replication … rows"* to `## Scoring` | none | `per file:` the table still lists six rows: Comprehensive, Peer Review, Stress Test, Code Review, Causal Audit, Proofread. | **NEVER-LANDED** |
| *"Move the `**Save each report…**` paragraph (335 chars) and the `**Check the tree around the verifier.**` paragraph (467 chars) … to `skills/review/gotchas.md`"* | none | `per file:` both paragraphs are still inline in the Comprehensive Review section. Body still 10,878 of a 11,000 cap — **122 chars of headroom**, exactly as the plan warned. | **NEVER-LANDED** |
| *"Create `tests/test_review_modes.py`"* (6 cases, given verbatim) | none | `tested:` **absent**. | **NEVER-LANDED** |

#### Task 2 — `revise`: `allowed-tools`, `post writer`, REWRITE, the letter

`per file:` `skills/revise/SKILL.md` and `rules/revision.md` read in full.

| Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|
| *"Add `Bash` to `allowed-tools`."* | none | `allowed-tools: Read,Grep,Glob,Write,Edit,Agent`. Step 5 still runs `pipeline.py … record-score` twice. | **NEVER-LANDED** |
| *"add: Then `python3 .claude/scripts/pipeline.py post writer`. FAIL … → fix and re-dispatch; do not write the response letter against a manuscript that has not passed `post`"* | none | `tested:` `post writer` appears nowhere in the skill. `rules/revision.md:31` still requires *"Revised paper → writer-critic → pipeline.py post writer"*. Step 5 still goes straight to Step 6. **An editor-facing letter can still be written over a failed render or a critic that never ran.** | **NEVER-LANDED** |
| *"Read `rules/revision.md` and `rules/registry.yaml` in full, decide which copy is right, and make that copy the only one"* (REWRITE) | none | `per file:` `skills/revise/SKILL.md` Step 3 still routes five classes including **REWRITE**; `rules/revision.md`'s table (lines 9–13) still holds NEW ANALYSIS, CLARIFICATION, DISAGREE, MINOR, FATAL — no REWRITE. The contradiction is intact. | **NEVER-LANDED** |
| *"the letter … is a `.qmd`, saves as `…referee_response_[journal]_[date].qmd` … names where each change landed **by cross-reference** … never a page number"* | none | `per file:` Step 6 still says *"Generate the response letter (Markdown)"* with *"Page/section references for each change"*; Step 8 still saves `…_[date].md`. `templates/response-letter.qmd` still forbids hardcoded page numbers. **The skill still instructs the opposite of its own template.** | **NEVER-LANDED** |
| *"Name `…response-tracker.md` inside Step 4 and `…diplomatic-disagreement.md` inside Step 7, delete the `## Bundled Resources (Level 3)` table … remove both entries from `KNOWN_UNBOUND`"* | none | `per file:` the catalogue table is still there, both templates are named only inside it, and both are still in `KNOWN_UNBOUND`. | **NEVER-LANDED** |
| *"Create `tests/test_revise_contracts.py`"* (6 cases, verbatim) | none | `tested:` **absent**. | **NEVER-LANDED** |

#### Task 3 — `pipeline`: one owner for `state strike`

`tested:` `grep -rn "state strike" skills/ agents/ rules/ scripts/` plus reading
`scripts/pipeline.py`'s `strike` branch (lines 557–560) and
`skills/pipeline/references/*.md`'s `Delegates to:` lines.

| Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|
| *"replace [the driver's] `state strike <creator>` with wording that … says the stage skill records the strike"* | none | `skills/pipeline/SKILL.md:51` still reads ``below 80: creator fixes → critic re-scores; `state strike <creator>`; at 3 → escalate``. | **NEVER-LANDED** |
| *"For each delegating stage skill with no `state strike`, add one line"* | none | Strike lines exist in `write` (×2), `lit-position`, `strategize` (×2), `analyze`. **`discover`, `review`, `submit` and `talk` still have none** — those stages can never escalate. Both failure directions the plan identified are live. | **NEVER-LANDED** |
| *"Add one short paragraph to `rules/agents.md`'s escalation section: the stage skill owns `state strike`…"* | none | `per file:` `rules/agents.md:46` mentions `pipeline.py state strike` but states no ownership rule. | **NEVER-LANDED** |
| *"Create `tests/test_strike_ownership.py`"* (3 cases, verbatim) | none | `tested:` **absent**. | **NEVER-LANDED** |
| *(underlying defect the plan set out to fix)* | — | `tested:` `scripts/pipeline.py:558` is `n = stt["strikes"].get(cr, 0) + 1` — **still an unconditional increment with no round key.** Four delegating stages still double-count and escalate after two real rounds. | **NEVER-LANDED** |

#### Task 4 — `tools`: `render`, `lint`, three stepless subcommands

`per file:` `skills/tools/SKILL.md` read in full (current version, after today's
unrelated edits) and `hooks/lint-scripts.sh` line 19.

| Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|
| *"Fix `render`: `MS=$(python3 .claude/scripts/pipeline.py manuscript) && quarto render "$MS"`"* | none | `per file:` still `quarto render manuscript_<project>.qmd`. The hardcoded convention the pipeline deliberately stopped assuming is intact. | **NEVER-LANDED** |
| *"Change the `**Default:**` line to name `scripts/acquire/` only"* | none | `per file:` still *"**Default:** `/tools lint` (lints `scripts/acquire/` and `explorations/`)"*. `tested:` `hooks/lint-scripts.sh:19` is `TARGET="${1:-scripts/acquire}"` — one target, no `explorations/`. The doc still promises coverage the script does not provide. | **NEVER-LANDED** |
| *"`validate-bib`, `journal` and `context` … Each gets a command block, an output, and a pass condition"* | none | `per file:` all three are still two-sentence descriptions with no command block, no output path and no pass condition. | **NEVER-LANDED** |
| *"delete the `## Bundled Resources (Level 3)` table"* | none | `per file:` still present (plus a `## Principles` section). | **NEVER-LANDED** |
| *"Find the three contradictions between `gotchas.md` and `SKILL.md`"* | none | Not attempted. | **NEVER-LANDED** |
| *"Create `tests/test_tools_contracts.py`"* (4 cases, verbatim) | none | `tested:` **absent**. | **NEVER-LANDED** |
| *(`learn` — explicitly out of scope, fixed by the predecessor)* | `35f82d5` | `per file:` `/tools learn` correctly points at `.claude/rules/meta-governance.md` and `/promote`; the "auto-memory handles corrections automatically" claim is gone. | **LANDED-AND-WORKS** (predecessor's) |

#### Task 5 — `ztp-data-tag` atomicity, `lit-position` local-first

`per file:` `skills/ztp-data-tag/SKILL.md` Step 5 and `skills/lit-position/SKILL.md`
frontmatter + Step 1 read in full.

| Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|
| *"Rewrite `ztp-data-tag` Step 5 so the note is written **first** and the marker tag second"* | none | `per file:` Step 5 item **1 is Tags** (including the `data-tagged` marker), item **2 is Note**. Order unchanged. | **NEVER-LANDED** |
| *"`mcp__zotpilot__get_notes(item_key=…)` — does a "Data (auto-extracted)" note already exist?"* | none | `tested:` `get_notes` occurs **once** in the file — at line 158, in the **Undo** section. It is absent from Step 5. An item carrying a `/ztp-tutor` or `/ztp-research` note still gets the marker and no Data note, and Step 2 then skips it forever. The silent, permanent failure is intact. | **NEVER-LANDED** |
| *"Insert [the local sweep] **before** the `/ztp-research` invocation … `search_topic` → `advanced_search` → `search_papers`"* | none | `per file:` Step 1 is: (1) extract key terms, (2) *"Invoke `/ztp-research` for the topic"*, (3) citation chains, (4) scooping risks. **No local search anywhere.** The skill still quotes `rules/literature-search-order.md` immediately above and then does not perform it. | **NEVER-LANDED** |
| *"Add `Bash` to `allowed-tools`"* (lit-position) | none | `allowed-tools: Read,Write,Edit,Grep,Glob,WebSearch,WebFetch,Agent`. Step 7 still runs `pipeline.py`. | **NEVER-LANDED** |
| *"Create `tests/test_zotpilot_skills.py`"* (5 cases, verbatim) | none | `tested:` **absent**. | **NEVER-LANDED** |

#### Task 6 — Low sweep: `promote`, `state/`, `new-project-ztp`, `/write humanize`

| Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|
| *"Step 1: read the lock's `# installed via:` line, not the presence of `commit=`"* | none | `per file:` `skills/promote/SKILL.md:27` still tests *"if the lock names a commit but `$RC` is on `main`"*. `tested:` `apply.sh:262` writes `commit=$sha` unconditionally and `:264` writes `# installed via: $mode`. **The test is still always true.** | **NEVER-LANDED** |
| *"give the re-link as `./bootstrap-pipeline.sh --tip` … or `apply.sh --project-dir <path> --link`"* | none | `per file:` `skills/promote/SKILL.md:84` still offers bare `apply.sh --link`. `tested:` `apply.sh:93` → `Error: --project-dir is required; exit 1`. **The documented command still fails.** | **NEVER-LANDED** |
| *"narrow the 'no other project has a link to it' claim to **new top-level items**"* | none | `per file:` claim unchanged. | **NEVER-LANDED** |
| *"Remove the three `/obsidian-digest-sync` references from `state/obsidian-config.md.example`"* | none | `tested:` still referenced at lines 5 and 49 of that file. The skill was deleted 2026-09-09. | **NEVER-LANDED** |
| *"add `"state"` to `SHIP` and `".example"` to `TEXT_SUFFIX` in `scripts/check_refs.py`"* | none | `tested:` `SHIP` (line 16) = `["agents","skills","rules","references","hooks","templates","seeds","scripts"]` — no `state`. `TEXT_SUFFIX` (line 18) has no `".example"`. **The checker still structurally cannot see the file above.** | **NEVER-LANDED** |
| *"Replace the `## Current Project State` anchor"* | none | `per file:` `skills/new-project-ztp/SKILL.md:81` still says *"If not, append after `## Current Project State`"* — an anchor that ships in no template. | **NEVER-LANDED** |
| *"Replace the index estimate with the README's figure"* | none | `per file:` skill (lines 60–61) still says *"~15–20 min for 300 papers (Gemini free tier)"*; `README.md:408` says *"200 papers ≈ 10–20 minutes either way"*. | **NEVER-LANDED** |
| *"**Recommend (a)** — [rename `/write humanize` to `/write cleanup`]"* (D2) | none | D2 answer cell **empty**; no rename. See §5.3 — the conflict is live and now demonstrably resolves the wrong way. | **NEVER-LANDED** |
| *"Create `tests/test_low_severity_contracts.py`"* (6 cases, verbatim) | none | `tested:` **absent**. | **NEVER-LANDED** |

#### Task 7 — Close out

| Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|
| *"Append a dated entry to `docs/SESSION_REPORT.md` recording, per task: what was verified, what was fixed, the D2 and D3 answers…"* | none | `tested:` last entry is `## 2026-09-16 — Skill token optimization: Tasks 0–8 complete`. No closeout entry. | **NEVER-LANDED** |
| *"Step 2: Measure"* (re-run the Task 0 baseline) | none | Never run. I ran it for them in §3. | **NEVER-LANDED** |
| *"does that remaining list still belong to the handoff? … repoint **Start here** …"* | none | Not addressed. | **NEVER-LANDED** |
| *"**Found in passing … not fixed:** this repo's own `CLAUDE.md` says `templates/` holds files `apply.sh` installs directly into a project … Neither file is in `templates/`. Verify and correct or delete that sentence."* | none | `tested:` `templates/` holds `handoff.md`, `journal-profile-template.md`, `pipeline-state.json`. The plan's own carried-forward correction was never applied. | **NEVER-LANDED** |

**Two corrections to the closeout plan's own statements**, found by reading the files
it cites to EOF:

- The plan says `/obsidian-digest-sync` *"appears three times"* in
  `state/obsidian-config.md.example`. `per file:` reading that file in full (90 lines),
  it appears **twice** — line 5 (the header comment) and line 49 (the knowledge-base
  folder heading). The four-row table at lines 54–59 belongs to the deleted skill but
  does not name it. The defect is real; the count is off by one.
- `tested:` The plan's carried-forward *"found in passing"* item is confirmed:
  `CLAUDE.md:52-53` claims `templates/` holds `data_manifest.md` and `gitignore`;
  `ls templates/` returns `handoff.md`, `journal-profile-template.md`,
  `pipeline-state.json`. The sentence is still wrong.

### 4.2 Token-optimization plan (`2026-09-16-skill-token-optimization.md`) — 9 tasks

Included because it drove 32 of the window's 41 commits and because the closeout plan
inherits its constraints. Verified the same way: by reading the current files and
running the suite.

| Task | Promise (abridged, quoted) | Commit | Current state | Class |
|---|---|---|---|---|
| 0 | *"Record the Level-2 baseline"* | — (no commit) | `tested:` figures reproduce. | **LANDED-AND-WORKS** |
| 1 | *"block the force-push form people type, stop blocking safe `branch -d`"* | `c7a6d24` / `786379e` | `tested:` `tests/test_session_guard.py` present; 12 cases pass in the 175-test suite. Per-pattern compilation, refspec force-push, `find -delete` all in `hooks/session-guard.py`. | **LANDED-AND-WORKS** |
| 2A | *"put the R-133 coverage check in the final workflow, not just the principles"* | `1537f8e` / `fdf17a3` | `per file:` `skills/submit/SKILL.md:73-75` carries step 3.5 with `pipeline.py state show`; `tests/test_submit_gate.py` present and passing. | **LANDED-AND-WORKS** |
| 2B | *"Put decision D1 to the user"* | — | D1 answered **(b)** and recorded in the Open decisions table. | **LANDED-AND-WORKS** |
| 3 | *"review: 18,058 → ≤11,000; bind templates to steps"* | `35bcd61` / `745794f` | `tested:` 10,878. `causal-audit-4-phases.md` present; `referee-report-template.md` deleted; `disposition-pool.md` retained and bound (named at the `--peer` Phase 1 step). `tests/test_review_contracts.py` passes — all three pinned strings survived. | **LANDED-AND-WORKS** |
| 4 | *"strategize: 15,966 → ≤8,000"*; implement D1(b) | `7dfb98f` / `ea89319` | `tested:` 7,967. `per file:` line 99 carries `--scope section:pre-analysis-plan`; line 38 binds `design-checklists/<design>.md`; `pap-safety.md` and `pre-theory-report.md` present. | **LANDED-AND-WORKS** |
| 5 | *"write: 11,290 → ≤7,500; bind the cleanup pass as Step 4b"* | `6cdfb9c` / `4e765ce` | `tested:` 7,482. `per file:` `#### 4b. Cleanup pass` at line 59 naming `cleanup-patterns.md`. | **LANDED-AND-WORKS** |
| 6 | *"discover: 9,733 → ≤6,000; five orphans resolved"* | `97b91b8` / `4333ec2` | `tested:` 5,934. `lit-review-entry.md` and `pdf-processing.md` deleted; all five discover entries gone from `KNOWN_UNBOUND` and the binding test passes. | **LANDED-AND-WORKS** |
| 7 | *"checkpoint: 8,526 → ≤5,500; three templates bound; three dropped report lines restored"* | `a3bb0bf` / `52a3267` | `tested:` 5,495 (5,459 + 36 from Task 8). `references/obsidian.md` present; three checkpoint entries gone from `KNOWN_UNBOUND`. | **LANDED-AND-WORKS** |
| 8 | *"surface pipeline-skill corrections as promotion candidates"*; ratchet budgets | `fb457c9` / `35f82d5` | `per file:` `skills/checkpoint/SKILL.md:75` and `:123` carry the candidate lines; `/tools learn` repointed. `tested:` `BUDGET` caps are the measured sizes rounded to the next 500, annotated in the test at lines 34–36. | **LANDED-AND-WORKS** |
| 8 | *"Step 9: repoint this repo's `CLAUDE.md` **Start here** … if this work supersedes [the handoff]"* | `66ca1cb` | Deliberately **not** repointed; reason recorded in the Progress Log and cross-linked from the handoff. That reason was itself corrected two commits later (`6f0e820`). | **SUPERSEDED** (a recorded decision, not a miss) |
| 8 | *"Step 4: Re-link the projects … `./apply.sh --link`"* | `35f82d5` | The executor found the plan's command **wrong** (`apply.sh --link` needs `--project-dir`), established that skills are *directory* symlinks so membership propagates on save, verified in NAR_settlement, and recorded the correction instead of running a broken command. | **SUPERSEDED** (correct handling of a defective plan step) |
| — | *"P2 / P4 / P6-as-specified / P7"* | — | Explicitly out of scope, with reasons, in the plan header and its close-out. | **SUPERSEDED** (deliberate non-adoption) |

**Nine of nine tasks landed and work.** Two plan steps were found to be wrong during
execution and were corrected rather than followed — which is the behaviour the repo's
"read before asserting" rule asks for, and it is recorded in both the Progress Log and
`docs/SESSION_REPORT.md`.

---

## 5. Cross-check against today's findings

For each: **did this plan promise to fix it?**

### 5.1 Nine agents told to write reports with no `Write` tool — **NOT PROMISED**

`tested:` Reading the `tools:` frontmatter of all 18 files in `agents/`, nine declare
exactly `Read, Grep, Glob` (plus `editor.md`, which adds WebSearch/WebFetch): the seven
critics (`coder-critic`, `explorer-critic`, `lit-critic`, `storyteller-critic`,
`strategist-critic`, `theorist-critic`) plus `domain-referee`, `methods-referee` and
`editor`. None has `Write`. Several carry explicit report-writing instructions.

`tested:` **Neither plan touches agent `tools:` frontmatter, and neither does the source
audit.** `grep -c 'Write tool'` returns 0 in all three documents. The closeout plan's
three `tools:` hits are the `/tools` **skill** (Task 4). Both plans address
`allowed-tools` on **skills** only (`revise`, `lit-position`), and the token plan's
close-out lists the rest of that sweep as deliberately left open — but that sweep is
about *skills running `pipeline.py` without pre-approved Bash*, a different thing
entirely.

`per file:` There is an unremarked mitigation: `skills/review/SKILL.md`'s Comprehensive
section says *"Critics are read-only and return their reports as text; this session
writes them."* So in `/review` the orchestrator is the writer by design. That makes the
tool grant arguably correct there — and makes the agent files' own "Save report to…"
instructions misleading rather than broken. Neither plan noticed either side of this.

### 5.2 `ai-audit` installed but wired to nothing — **NOT PROMISED**

`tested:` `apply.sh:155-160` links `ai-audit/skills` and `ai-audit/agents` into every
project, and `scripts/check_install.sh:162-163` verifies those links. `tested:` Searching
`skills/`, `rules/` and `agents/` for `humanize` or `verify-claims`, the only hits are
`skills/write/SKILL.md` — which refers to its **own** `/write humanize` mode, not the
ai-audit skill. No `skills/pipeline/references/*.md` names either. So `/humanize` and
`/verify-claims` ship to six papers and are invoked by nothing in the pipeline.

`tested:` The closeout plan mentions `ai-audit` seven times. `per file:` reading each:
lines 1157, 1371 (*"git status --short zotpilot-skills/ ai-audit/"* — a tripwire that
nothing vendored moved), 1200 (*"read-only — vendored"*), 1241 (quoting humanize's own
text for D2), 1366 (*"do not edit `ai-audit/`"*), 1448 and 1517 (*"need upstream PRs to
… `EconGeo/ai-audit`"*). **Every mention is a prohibition on editing it or a note that
its P1 verbosity needs an upstream PR. None is about wiring it in.** Not promised, and
not identified as a gap by the source audit either.

### 5.3 `/write humanize` vs `/humanize` — **PROMISED, as decision D2. Never asked.**

This is the one cross-check the plan did name: **Task 6 Step 2**, decision **D2**, with
a recorded recommendation of **(a) rename the mode to `/write cleanup`**, and the
instruction *"put it to the user (see Open decisions) **before touching either file**"*.

`tested:` The D2 answer cell in the Progress Log's Open decisions table is **empty**.
Task 6 never ran. The conflict is entirely live, and reading both files confirms the
sharper form of it:

- `per file:` `ai-audit/skills/humanize/SKILL.md` frontmatter carries
  **`disable-model-invocation: true`** and describes itself as *"Read-only audit …
  Produces a report; does NOT rewrite."*
- `per file:` `skills/write/SKILL.md` frontmatter has **no such flag**, and line 102 is
  `### `/write humanize [file]` — Cleanup Pass Only`, which edits the file in place.

`tested:` So the mechanism the prompt describes is real and demonstrable from the two
frontmatters: **the detect-only skill is the one the model is forbidden to invoke, and
the in-place rewriter is the one it can reach.** Under model invocation the rewriter
always wins — the exact behaviour the vendored skill's own text calls out as degrading
prose on a cross-vendor finding.

Worth noting for whoever picks D2 up: the plan anticipated this and required the
overlap evidence (*"read `cleanup-patterns.md` and `agents/humanize-auditor.md` in full
and say … how much the 24 cleanup patterns actually overlap the auditor's 10
categories"*) **before** presenting the options, because a low overlap would change
which option is right. That evidence was never gathered. The plan's analysis of this
defect is good; only the execution is missing.

### 5.4 `data-engineer.md:92` recommending `kableExtra` while its own critic deducts — **NOT PROMISED**

`tested:` `grep -c kableExtra` returns **0** in all three documents — the closeout plan,
the token plan, and the 2026-09-15 audit. Never raised.

`per file:` The contradiction is real and is a *conditionality* failure, not a flat
disagreement. `agents/data-engineer.md` line 92 lists `Tables | gt, kableExtra,
modelsummary` in an unconditional package table. But `rules/quarto-word.md:49` says
*"`kableExtra` emits LaTeX and produces garbage in Word — use **flextable**"*, its
line 143 lists `kableExtra | Produces HTML/LaTeX, not Word tables`, and its **deduction
table at line 169 charges −5** for *"`kableExtra` loaded or used for Word tables"*.
Meanwhile `rules/quarto-pdf.md:39-67` makes `kableExtra` the **required** choice for PDF.
So the agent's recommendation is right for a PDF manuscript and a scored defect for a
Word one, and the agent file states no output-format condition at all. The audit's §3 P3
row for `analyze` catches two *other* agent-vs-reference drifts (`base_size`, `treated`)
and misses this one.

**Cross-check summary: one of the four was promised (5.3), and it was never asked.**

---

## 6. Answers

### 6.1 What proportion landed and works?

Counting the discrete ledger rows in §4:

| | Rows | LANDED-AND-WORKS | SUPERSEDED | NEVER-LANDED |
|---|---|---|---|---|
| Closeout plan | 46 | **3** (2 are Task 0; 1 is the predecessor's `learn` fix) | 0 | **43** |
| Token-optimization plan | 13 | **10** | 3 | 0 |
| **Both** | **59** | **13 (22%)** | **3 (5%)** | **43 (73%)** |

By task rather than by promise:

- **Closeout plan: 1 of 8 tasks — 12.5%.** And the one that landed is the baseline task,
  whose functional content was a diff that already existed in the working tree before
  the plan was written. **Of the seven defect-fixing tasks the plan exists for, zero
  landed.** Closeout-attributable promises delivered: **2 of 46 (4%)**.
- **Token-optimization plan: 9 of 9 tasks — 100%**, with every numeric claim reproducing
  exactly seven days later and mechanically defended by ratchet tests that are green today.

**The honest headline is that these are two different stories sharing one window.** The
41 commits are overwhelmingly the predecessor's: 32 of them, and they delivered. The
plan under audit contributed **3 commits** (`ed57b0f`, `b0a95af`, `3ad638e`) plus the
two that wrote and corrected the plan document itself (`86203f8`, `6f0e820`), and it
delivered its baseline and nothing else.

Notably, **no classification other than LANDED-AND-WORKS and NEVER-LANDED was needed for
the closeout plan.** There is no LANDED-BUT-UNWIRED, no LANDED-BUT-BROKEN, no
PARTIALLY-LANDED. Nothing was half-done, because nothing was started. That is a cleaner
failure than the alternative: the tree is not carrying half-applied fixes.

### 6.2 Top recurring failure shapes

Across the 43 unfixed defects, six shapes recur, in rough order of frequency:

1. **The documentation and the thing it documents have drifted, and the documentation is
   what the model reads first.** The largest class. `tools lint`'s default vs
   `lint-scripts.sh:19`; `promote`'s `apply.sh --link` vs `apply.sh:93`; `revise` Step 6's
   page references vs `response-letter.qmd`'s explicit ban on them; `new-project-ztp`'s
   `## Current Project State` anchor that ships in no template; `tools render`'s
   hardcoded `manuscript_<project>.qmd`; `data-engineer.md:92`'s unconditional
   `kableExtra`; and `CLAUDE.md:52`'s own `templates/` sentence. In every case the
   executable artifact is right and the prose is wrong — and the prose wins, because the
   model reads it first.
2. **A route is advertised and nothing implements it.** `/review --theory` (a weight-20
   component with a routing line, a caller in `adopt.md`, and no dispatch);
   `/review --variance` (fully specified in `agents/editor.md`, which delegates
   enforcement to a skill that never heard of it); `/tools validate-bib`, `journal`,
   `context`. The plan's own framing is the right one: *"A routing line with no mode
   section is worse than an undocumented flag: it tells the model the mode exists, and
   the model then invents the dispatch."*
3. **A rule is stated in one file and executed in none.** `rules/literature-search-order.md`
   is quoted verbatim by `lit-position` Step 1, which then does not perform it.
   `rules/revision.md:31` mandates `post writer`; `revise` never calls it. This is the
   same shape the predecessor plan fixed twice (R-133 in `submit`, `cleanup-patterns.md`
   in `write`) — evidence it is systemic, not incidental.
4. **A catalogue stands in for a binding.** `## Bundled Resources (Level 3)` tables in
   `revise` and `tools`, with `KNOWN_UNBOUND` still holding five entries. The
   predecessor built the mechanical fix for this (`test_skill_contracts.py`) and
   discharged it for five skills; the closeout plan was to discharge three more.
5. **Order of operations producing a silent, permanent failure.** `ztp-data-tag` writes
   the `data-tagged` marker before the Data note, so an item that already carries any
   ZotPilot note is marked done, gets no Data note, and is excluded from every future
   run with no report. The worst single unfixed defect, because it is undetectable from
   the outside.
6. **Two copies, opposite answers, nothing pinning them.** REWRITE in `revise` but not
   `rules/revision.md`; `/write humanize` vs `/humanize`; `kableExtra` in PDF vs Word.
   The predecessor's response — *"add a contract test for any pair that must agree"* —
   is the right one and was applied only where it refactored.

**A seventh shape, and the plan is an instance of it.** `tested:` The closeout plan's
verification block in **every** task (lines 422, 617, 799, 982, 1157, 1371, 1408) chains
`… && python3 scripts/check_paths.py` and/or `&& python3 scripts/check_refs.py`. Both
scripts **require `--root`**:

```
$ python3 scripts/check_paths.py
usage: check_paths.py [-h] --root ROOT [--list]
check_paths.py: error: the following arguments are required: --root
```

Run as written, each verification chain aborts at the gate step — and in Tasks 3, 6 and
7, `./tests/run_fixture.sh`, `check_refs.py` and `./scripts/check_install.sh --all` sit
*after* it and would never run at all. (`scripts/check_fork.sh` invokes both correctly,
via a helper that supplies `--root`; the token-optimization plan has **zero**
argument-less invocations.) **The plan prescribes a verification recipe that does not
execute** — the same shape as defect class 1, in the document written to fix defect
class 1. Nobody found out, because nobody ran it.

### 6.3 Did anything verify completion at the time?

**Split answer, and the split is the lesson.**

**The token-optimization plan verified itself thoroughly, and its verification still
holds today.** `per file:` every task followed write-the-failing-test → confirm red →
fix → confirm green → full suite → `check_fork`, and the Progress Log records the suite
count climbing 142 → 154 → 156 → 158 → 159 with the specific expected failures named at
each stage. More importantly it left behind **ratchets rather than assertions**:
`BUDGET` and `KNOWN_UNBOUND` in `tests/test_skill_contracts.py` are checked on every run
and both are green in today's **175 passed, 3 subtests**. `tested:` I reproduced all its
headline numbers to the character without reading its close-out first. That is
verification that survived the session that wrote it.

**The closeout plan verified Task 0 and had no mechanism to notice that Tasks 1–7 never
happened.** Task 0's own verification is genuinely good — `tested:` claims checked
against the *installed build* rather than the vendored text, two draft claims found
wrong and dropped, suite and `check_fork` recorded. But at the plan level:

- The only completion signal is a human editing a markdown table. `tested:` Nothing
  tests the plan. No CI, no hook, no gate reads `docs/plans/*.md`. A plan stuck at 1 of 8
  for seven days produces no signal anywhere.
- `tested:` The suite is **green** at 175 passed. The tree passes `check_fork`. Every
  one of the 43 unfixed defects is invisible to every gate in the repo — which is exactly
  why the plan specified six new test files, and exactly why their absence matters more
  than the absent fixes. **The tests were the durable part, and none of them exist.**
- The plan's own design contributed. Its execution model — *"Each task is one session …
  **clear the context window** … Do not read the other tasks"* — means there is no
  session that ever holds the whole plan, and therefore no session positioned to notice
  it stalled. It is a good model for executing a long plan and a poor one for detecting
  that execution stopped.

So: **something verified completion for the work that was done, and nothing verified
non-completion for the work that was not.** The one artifact that would have caught it —
Task 7's close-out, which re-measures the baseline and writes the `SESSION_REPORT.md`
entry — is itself a task inside the plan that stalled. A plan whose only completion
check is its own last step cannot report that it stopped.

### 6.4 What a reader should take from this

- `tested:` **The tree is in a known-good, self-consistent state.** Suite green,
  `check_fork` PASS, no half-applied changes, no uncommitted shipped edits. Nothing here
  is urgent in the sense of "broken right now".
- **The 43 unfixed defects are all still exactly as the 2026-09-15 audit and the plan
  described them**, and the plan's analysis of each was re-verified by me by reading the
  current files. The plan is a good plan. It can be picked up at Task 1 as written, with
  three amendments: fix the seven `check_paths.py` / `check_refs.py` invocations to pass
  `--root`; correct the `/obsidian-digest-sync` count in Task 6 from three to two; and
  note in Task 0's row that `tools` has since grown by 2,577 chars for unrelated reasons,
  so its 4,347 baseline no longer applies.
- **D2 and D3 are still unanswered and both are Step 2 of their tasks.** Neither task can
  start without them.
