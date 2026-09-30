# Rule consumer audit — which excluded rule does each step need? (2026-09-29)

Task 1 of `docs/plans/2026-09-29-rule-load-exclusions.md`. Every file below was **read in
full** before its row was written; the grep inventory in the plan was used only to locate
them. Rules read in full: all fifteen candidates for exclusion, plus `agents.md`.

## 1. The two findings that decide the shape of Task 3

**Subagents load project rules, and `claudeMdExcludes` removes them from subagents too.**
- per docs (`code.claude.com/docs/en/sub-agents`, fetched 2026-09-29): a non-fork
  subagent's initial context holds "every level of the CLAUDE.md hierarchy the main
  conversation loads, including `~/.claude/CLAUDE.md`, project rules …".
- tested (headless `claude -p` in `~/Research/NAR_settlement`, one `general-purpose`
  subagent, no tools, asked whether `logging.md`'s *Receipts* section, *Option Gates* and
  *Content Invariants* were in its context): at baseline all three were present in the
  subagent; with the Task 2 exclusion list only *Content Invariants* was. `InstructionsLoaded`
  fired only for the main session (21 events baseline, 7 with the list), never for the
  subagent.

So an agent that needed an excluded rule's content needs a read step exactly as a skill does.

**The worker logs are silent consumers.** `ai-disclosure.md` says "every worker agent
appends one entry to `ai_use_log.md`" and `logging.md` says an entry goes to
`research_journal.md` "whenever an agent completes work". Only `coder` and `writer` carry the
AI-log instruction in their own file; no agent carries the journal one. The paper repos show
both happening anyway — `affordable_housing_2026/ai_use_log.md` has entries from
`strategist`, `explorer` and `data-engineer`, and its journal has entries from
`strategist-critic`, `explorer`, `coder-critic` — which only the loaded rules can have caused.

## 2. Row-level audit

`needs content?` — does the step act correctly only with the rule's text in hand (yes), or is
the mention a citation, a rationale or a pointer (no). `already reads?` — does the file
already instruct a read of it.

### skills/

| file | step | rule | needs content? | already reads? | action |
|---|---|---|---|---|---|
| `analyze/SKILL.md` | Step 1 Pre-Code Report gate | option-gates | yes (5–8 table, wait, `--yes`, rejected options recorded) | no | add read in the gate line |
| `analyze/SKILL.md` | Step 4 "What coder-critic checks" | quarto-empirical | no — tells the session what the critic applies; coder-critic reads it (below) | — | none |
| `analyze/references/figure-standards.md` | header | quarto-pdf, quarto-word | no — "mechanics live in the format rules" pointer | — | none (coder/data-engineer read them, below) |
| `analyze/references/table-standards.md` | Authority column | quarto-pdf, quarto-word | no — pointer | — | none (as above) |
| `analyze/templates/chunk-structure.md` | intro, table chunk comment | quarto-empirical, quarto-word | no — citation of where deductions live | — | none |
| `checkpoint/SKILL.md` | §intro item 2, 4b | logging | no — 4b's entry format is `templates/session-report-entry.md` | self-contained | none |
| `checkpoint/SKILL.md` | 4c | logging | no — `templates/research-journal-entry.md` | self-contained | none |
| `checkpoint/SKILL.md` | 4a | meta-governance | no — the ledger command is given in the step | self-contained | none |
| `checkpoint/SKILL.md` | Step 1, 4f, Step 5 | session-handoff | **yes** — R1's five-item checklist and R3's reference dry-run script exist only in the rule | no | add read at Step 5 |
| `checkpoint/SKILL.md` | Step 5 `ai_use_log.md` | ai-disclosure | no — the check is stated in the step | self-contained | none |
| `discover/SKILL.md` | interview framings gate; target-journal gate; data shortlist gate; ideation gate (4) | option-gates | yes | no | add read in the first gate line of each mode (interview, data, ideate: 3) |
| `lit-position/SKILL.md` | Steps 4, 5, 7 gates (3) | option-gates | yes | no | add read in the Step 4 gate line (Steps 5 and 7 follow in the same run) |
| `pipeline/SKILL.md` | `run` escalation gate | option-gates | yes | no | add read in the gate line |
| `pipeline/SKILL.md` | "Suggested Learnings … per meta-governance.md" | meta-governance | **yes** — the PATTERN / FRICTION / HIGH-PERF table and the 3-project bar are only in the rule | no | add read at that line |
| `pipeline/references/{adopt,analyze,recovery,write}.md` | limitation / section-score notes | lifecycle | no — rationale; `pipeline.py` prints its own refusal | — | none |
| `pipeline/references/{analyze,data,literature,recovery,strategy,submit,theory,write}.md` | "weight and threshold" | quality | no — `pipeline.py score` computes it | — | none |
| `promote/SKILL.md` | Step 2.6 | meta-governance | no — the step carries the ledger commands | self-contained | none |
| `promote/SKILL.md` | Step 5 | shared-pipeline | no — both re-link commands are given | self-contained | none |
| `review/SKILL.md` | Phase 1 journal gate; desk-reject venue gate (2) | option-gates | yes | no | add read in the Phase 1 gate line (desk-reject gate is in the same phase) |
| `review/config/scoring-rubrics.md` | Coder-Critic | quarto-empirical | yes, for coder-critic | — | covered by the coder-critic read (below) |
| `review/gotchas.md` | writer-critic format line | quarto-pdf, quarto-word, quarto-empirical | no — which critic owns which deduction | — | none |
| `review/templates/manuscript-review-8-categories.md` | Prerequisite Checks | quarto-pdf, quarto-word | yes, for writer-critic | **yes** — "Read `.claude/rules/quarto-pdf.md` and `.claude/rules/quarto-word.md`" | none |
| `review/templates/manuscript-review-8-categories.md` | §5 architecture note | quarto-empirical | no — "belongs to coder-critic" | — | none |
| `revise/SKILL.md` | Step 1.3 | revision | yes | **yes** — "Read the revision protocol (`.claude/rules/revision.md`)" | none |
| `revise/SKILL.md` | FATAL gate; DISAGREE gate (2) | option-gates | yes | no | add read in the FATAL gate line (DISAGREE is later in the same run) |
| `strategize/SKILL.md` | Step 2 design gate | option-gates | yes | no | add read in the gate line |
| `submit/SKILL.md` | `target` gate | option-gates | yes | no | add read in the gate line |
| `submit/SKILL.md` | final Step 2.5 | ai-disclosure | **yes** — "populate from `ai_use_log.md` using the Wiley/COPE-aligned template": the template text is only in the rule | no | add read at Step 2.5 |
| `submit/gotchas.md` | journal overrides | quarto-pdf, quarto-word | no | — | none |
| `talk/SKILL.md` | Step 1b gate | option-gates | yes | no | add read in the gate line |
| `tools/SKILL.md` | `journal` | logging | no — entry format is the checkpoint template | self-contained | none |
| `tools/SKILL.md` | `learn` | meta-governance | no — the step restates the user-corrections path | self-contained | none |
| `tools/SKILL.md` | `render` | quarto-empirical | no — write-gate item 4 is restated in the step | self-contained | none |
| `write/SKILL.md` | GATE 1 gate (and `abstract`, "same option gate") | option-gates | yes | no | add read in the gate line |
| `ztp-data-tag/SKILL.md` | Step 1 gate | option-gates | yes | no | add read in the gate line |

### agents/

| file | step | rule | needs content? | already reads? | action |
|---|---|---|---|---|---|
| `coder-critic.md` | Correctness Layer; "The one mode" | quarto-empirical | **yes** — "apply the deduction table in quarto-empirical.md"; the table is only there (scoring-rubrics defers to it) | no | add read in "The one mode" |
| `coder-critic.md` | INV-23/INV-24 | data-manifest | no — the check and deduction are stated in the file | self-contained | none |
| `coder.md` | AI Use Log | ai-disclosure | no — format carried in the file | self-contained | none |
| `coder.md` | Stage 3 tbl-/fig- chunks (silent) | quarto-pdf, quarto-word | **yes** when the YAML declares `docx:` — flextable defaults, `fit_to_width`, `output = "flextable"` are only in quarto-word; chunk-structure covers the PDF path only | no | add read at Stage 3 |
| `coder.md` | stages 0–3 (silent) | quarto-empirical | no — cache.extra/dependson/setup/inline-number rules and the 4-item write gate are carried by the file plus `chunk-structure.md`, which it reads first | self-contained | none |
| `data-engineer.md` | Preferred R Packages (Tables) | quarto-word | yes — same as coder | no | add read at Chunk Standards |
| `data-engineer.md` | Chunk Standards (silent) | quarto-empirical | **yes** — `cache.extra` syntax (`file.mtime`, `!expr list`) and the setup-chunk rules are not in the file and it is not told to read `chunk-structure.md` | no | add read at Chunk Standards |
| `data-engineer.md` | Saving (silent) | data-manifest | **yes** — the 8 columns, the six trigger events, "manual needs Notes" | no | add read at Chunk Standards |
| `data-engineer.md` | end of work (silent) | ai-disclosure | yes | no | add read (AI Use Log line) |
| `strategist.md`, `explorer.md`, `theorist.md`, `storyteller.md` | end of work (silent) | ai-disclosure | yes — entries from these agents exist in paper repos | no | add read (AI Use Log line) |
| `writer.md` | AI Use Log | ai-disclosure | no | self-contained | none |
| `writer.md` | voice paragraph (priority order) | quarto-pdf, quarto-word | no — the prose-level constraints (pandoc citations, no inline LaTeX, `@ref`s) are in `quarto-authoring.md`, which the writer reads before any `.qmd` edit | self-contained | none |
| `writer-critic.md` | Resources: Format | quarto-pdf, quarto-word | yes | **yes**, via the 8-categories template's Prerequisite Checks | none |
| every creator/critic dispatch | research-journal entry (silent) | logging | see decision D2 | no | see D2 |

### Rules that load at startup (not edited here)

- `rules/agents.md` §4: "Read `permissions.md` before relying on a pairing" — **already reads**,
  so `permissions.md` needs nothing. Its `option-gates.md` mention is a pointer; the gated
  skills carry the reads.
- `rules/content-invariants.md`: no mention of an excluded rule.

### Outside `skills/` and `agents/` (read, no edit)

| file | rule | verdict |
|---|---|---|
| `hooks/log-reminder.py`, `hooks/pre-compact.py` | logging, session-handoff | citation in docstrings and a reminder string; the reminder itself carries the header format |
| `references/quarto-authoring.md` | quarto-empirical/-pdf/-word | citation (Scope and precedence table) |
| `references/journal-profiles.md` | ai-disclosure | citation (JRER's policy "differs from the Wiley/COPE template") |
| `references/domain-profile.md` | quality | template comment, citation |
| `ai-audit/README.md`, `ai-audit/VENDORED.md` | ai-disclosure | citation; vendored, never edited |

## 3. Mentions outside this repo (Task 1 Step 4)

| file | rule | verdict |
|---|---|---|
| `~/.claude/CLAUDE.md` (carve-out 2) | quarto-empirical/-pdf/-word | citation — names them as owning document architecture. **But see D3**: it is the only instruction a session gets before an ad-hoc `.qmd` edit, and it points at `quarto-authoring.md` only |
| `~/Research/NAR_settlement/CLAUDE.md` | quarto-empirical (×3), data-manifest | citation — the project restates the parts it relies on |
| `~/Research/ESG/CLAUDE.md` | quarto-empirical | citation |
| `~/Research/POGM4/CLAUDE.md` | quarto-empirical (×2), ai-disclosure | citation; the ai-disclosure line is a project override (T&F placement), which holds with or without the rule |
| `~/Research/affordable_housing_2026/CLAUDE.md` | quarto-empirical | citation (documented exception) — not in the plan's list; found by the same grep |
| `~/Research/zoning2026/CLAUDE.md` | quarto-empirical | citation — not in the plan's list |

## 4. Decisions for the user (Task 1 Step 5)

**D1. Two rules have a trigger that is not a skill step — any turn can fire it.**
- `meta-governance.md`, *User corrections*: "ask once, at the moment of the correction —
  Make this permanent in `<target file>`?" The trigger is the user correcting a shared
  skill's output, in any session. No skill step can carry that read.
- `shared-pipeline.md`: "editing one changes every paper immediately … nothing will warn you."
  The trigger is any edit through a `.claude/` link.

Recommendation: **keep both always on** (≈3.4 KB + 3.0 KB, ≈1.6k tokens). They fit the
plan's own criterion for the always-on four ("apply to every turn, not to one skill").

**D2. The research journal loses its per-dispatch entries.** Today the session appends an
entry after each creator or critic completion because `logging.md` is in context. Excluded,
nothing says to. What survives: `/checkpoint` 4c writes the session's agent work to the
journal from its own template, and `/tools journal` back-fills every recorded score from
`pipeline_state.json`. Nothing gates on the journal (`/pipeline` reads state, critics
cold-read without it). Options: (a) accept checkpoint-time entries; (b) keep `logging.md`
always on (≈4.7 KB, ≈1.2k tokens); (c) a read step in each dispatching skill (≈9 skills).
Recommendation: **(a)** — the journal is written *from* the state file by design, and (c)
spreads one bookkeeping line across nine files.

**D3. Ad-hoc manuscript edits outside `/analyze` and `/write`.** A main session editing the
`.qmd` by hand currently has `quarto-empirical.md` (and the two format rules) in context.
Excluded, it gets them only through a skill or agent read step. The one instruction every
research session already obeys before a `.qmd` edit is `~/.claude/CLAUDE.md` carve-out 2
("read `quarto-authoring.md` before authoring any `.qmd`"). Recommendation: extend that line
to "…and, in a research project, `.claude/rules/quarto-empirical.md` plus the format rule for
each declared format". That file is outside this repo, so it is your edit to approve.
`data-manifest.md`'s "any new file in `data/raw/`" trigger has the same shape; the
data-engineer read covers the pipeline path, and the project `CLAUDE.md` files already carry
the manifest requirement.

**Count.** 23 read lines if D1 is accepted: 13 option-gate lines across 11 skills (one per
mode — later gates in the same run reuse the read), `checkpoint`, `submit` Step 2.5,
`coder-critic`, `coder`, `data-engineer` (2), `strategist`, `explorer`, `theorist`,
`storyteller`. 24 if `meta-governance.md` stays excluded (adds the `/pipeline` read).

## 5. Exclusion list (Task 2 — written, not live)

**User rulings, 2026-09-29:** D1 — keep `meta-governance.md` and `shared-pipeline.md` always
on; D2 — accept checkpoint-time journal entries (`logging.md` excluded); D3 — add the read line
to `~/.claude/CLAUDE.md` carve-out 2 (done). Final list, 13 excluded:

```json
"claudeMdExcludes": [
  "**/research-claude/rules/permissions.md",
  "**/research-claude/rules/lifecycle.md",
  "**/research-claude/rules/quality.md",
  "**/research-claude/rules/option-gates.md",
  "**/research-claude/rules/revision.md",
  "**/research-claude/rules/logging.md",
  "**/research-claude/rules/session-handoff.md",
  "**/research-claude/rules/quarto-empirical.md",
  "**/research-claude/rules/quarto-pdf.md",
  "**/research-claude/rules/quarto-word.md",
  "**/research-claude/rules/data-manifest.md",
  "**/research-claude/rules/ai-disclosure.md",
  "**/research-claude/rules/content-standards.md"
]
```

## 6. Verification (Task 4, 2026-09-29)

Harness: a scratch settings file with an `InstructionsLoaded` hook appending each event to a
log, plus the §5 list, passed with `--settings` (a `claude` shim on `PATH` added it for
`run_fixture.sh`). No timeouts on any run.

**Startup load, `~/Research/NAR_settlement` (tested):**

| | files at `session_start` | rule bytes | ≈ tokens (bytes/4) |
|---|---|---|---|
| before | 21 (3 CLAUDE.md + 18 rules) | 106,932 | ≈ 26.7k |
| after | 9 (3 CLAUDE.md + `agents`, `content-invariants`, `systematic-debugging`, `literature-search-order`, `meta-governance`, `shared-pipeline`) | 30,572 | ≈ 7.6k |

Saving ≈ 76.4 KB, ≈ 19.1k tokens per session start, main session and every subagent.

**Point-of-need reads (tested, `--output-format stream-json` transcripts):**
- `/checkpoint` on a fixture copy: read `.claude/rules/session-handoff.md` (Step 1 batch)
  before reporting the staleness sweep and dry-run lines.
- `/review --proofread`: the writer-critic subagent read `content-invariants.md` and
  `quarto-pdf.md` before scoring (the fixture declares only `pdf:`).
- `run_fixture.sh --live` (`/pipeline run --until strategy --yes`): the session read
  `option-gates.md` before `/discover data`'s gate; the explorer subagent read
  `ai-disclosure.md` and created `ai_use_log.md` in that format; the strategist appended its
  entry in the same format. Critic scores recorded (data 100, strategy 86).

**Regression:** `tests/run_fixture.sh --live` → `✓ run_fixture: PASS` (all mechanical and live
checks). `python3 -m pytest tests/ -q` → 583 passed. `check_fork.sh` → PASS.

**Finding, pre-existing and not caused by this change:** in fixture copies under `/private/tmp`
and `/var/folders` *no* rule loads at session start, with or without the exclusion list (tested:
a baseline run with no `claudeMdExcludes` in `fx_ck` logged only the two CLAUDE.md files). In
`~/Research/NAR_settlement` all 18 load. Cause unverified. Consequence: the live fixture tier
and the evals have never exercised startup-loaded rules, so a green eval never showed a skill
working *with* rules in context — which, after this change, is the state that matches
production more closely than before.
