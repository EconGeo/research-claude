# Rule load exclusions (`claudeMdExcludes`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) or superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: planned (2026-09-29). Not started.**

## Decisions (user, 2026-09-29)

1. **Option A is chosen:** exclude rules from startup loading with `claudeMdExcludes`, and leave every file where it is. Moving the rules to `references/` (option B) is **rejected**. It would edit ~143 path references in ~69 files plus `check_fork.sh`, `render_registry.py` and `pipeline.py` for the same token saving, and it would be the seventh restructure of this repo.
2. **Format rules are excluded as well**, not only the pipeline internals.
3. **Goal:** cut the tokens loaded every session **without losing any functionality**. The exclusion list (Task 2) and the read steps (Task 3) ship together. The exclusion does not go live until every consumer that needs an excluded rule has an explicit read step for it.

**Goal:** a session in a linked project loads 7 instruction files at startup instead of 21: the 3 CLAUDE.md files and the 4 always-on rules. The 15 excluded rules are read at the point a skill or agent needs them.

**Architecture:** one `claudeMdExcludes` list in the user settings (`~/.claude/settings.json`). It holds patterns matched against the link target (`**/research-claude/rules/<name>.md`), so it covers both the shared checkout and a pinned `.pipeline/research-claude` checkout. It never matches anything under `~/Courses`. Every file stays at `.claude/rules/<name>.md`, so every path, script, gate and test is unchanged. The functionality is kept by adding one explicit `Read` line at each point of need in `skills/` and `agents/`.

## Evidence this plan argues from (2026-09-29)

- **Per docs** (`code.claude.com/docs/en/memory`, fetched 2026-09-29):
  - Rules without `paths:` load at launch.
  - `claudeMdExcludes` works at any settings layer and matches either the symlink path or its target.
  - A rule symlinked from outside the working directory loads only if it has **no** `paths:`.
- **Tested** (headless `claude -p` in a linked project, with an `InstructionsLoaded` logging hook passed through `--settings`):
  1. Baseline: 21 files loaded at `session_start` (3 CLAUDE.md + 18 rules).
  2. A symlinked rule with `paths: ["**/*.qmd"]` (`content-standards.md`) did **not** load after the session read the `.qmd`. A real-file rule with the same `paths:` did load (`path_glob_match`). So `content-standards.md` has never loaded in any linked project, and `paths:` scoping is not available to symlinked rules.
  3. With `claudeMdExcludes: ["**/research-claude/rules/permissions.md", "**/research-claude/rules/quarto-word.md"]`, 19 files loaded, neither excluded file was in context, and a `Read` of `.claude/rules/permissions.md` still worked.
- **Locator only (grep, not yet read in full):** 61 mentions of the excluded rules in `skills/` and `agents/`. Only 2 have "read/load/open" wording nearby. The rest appear to assume the rule is already in context. Task 1 settles this by reading every one.
- **Size:** the excluded rules total about 82.8 KB (~20.7k tokens by the bytes/4 rule in `scripts/context_bill.py`). The rules that stay total about 24.1 KB (~6k tokens).

## The split

**Always loaded (4 rules):** `agents.md`, `content-invariants.md`, `systematic-debugging.md` and `literature-search-order.md`. These apply to every turn, not to one skill. `registry.yaml` is not Markdown and never loads, so it needs no change.

**Excluded (15 rules):**

| Rule | Kind | What a missing read step costs |
|---|---|---|
| `permissions.md` | rendered copy of `registry.yaml` | Nothing enforced. `pipeline.py` reads the YAML |
| `lifecycle.md` | explains `pipeline.py` | Nothing enforced. The script is the gate |
| `quality.md` | weights and thresholds | Nothing enforced. `pipeline.py score` computes them |
| `meta-governance.md` | promotion and corrections | `/promote` and `/checkpoint` behaviour |
| `shared-pipeline.md` | what a symlinked `.claude/` means | Editing a linked file without knowing it is shared |
| `option-gates.md` | ranked-choice wait contract | Gate format in 12 skills |
| `revision.md` | R&R routing | `/revise` routing table |
| `logging.md` | session report, research journal and dispatch-log formats | Entry formats written by skills and agents |
| `session-handoff.md` | checkpoint staleness sweep | `/checkpoint` Requirements 1–3 |
| `quarto-empirical.md` | single-document architecture | coder, data-engineer, writer and their critics |
| `quarto-pdf.md` | PDF block and kableExtra | writer, writer-critic, `/analyze` |
| `quarto-word.md` | docx block and flextable | writer, writer-critic, data-engineer |
| `data-manifest.md` | provenance table | data-engineer, coder-critic (INV-24) |
| `ai-disclosure.md` | AI use log format | every worker agent's log entry, `/submit` |
| `content-standards.md` | table and figure standards | Already never loads (see Evidence 2). Excluding it stops it silently starting to load if its `paths:` is ever removed |

## Global Constraints

- **Branch first.** Edits to `skills/` and `agents/` are live in all six paper repos the moment they are saved. Work in a worktree on branch `rule-load-exclusions`.
- **No file moves and no renames under `rules/`.** The whole point of option A is that paths do not change.
- **Read steps are additive.** Each is a single line naming the file by its `.claude/rules/` path at the step that needs it, e.g. `Read .claude/rules/option-gates.md before presenting the gate.` Existing prose is not rewritten.
- `./scripts/check_fork.sh` must exit 0 before every commit that touches `skills/` or `agents/`. `tests/test_skill_contracts.py` sets SKILL.md size budgets, so raise a budget only when a read line pushes a skill over it, and say so in the commit.
- **Never put a time limit on a live eval** (`CLAUDE.md`, user ruling 2026-09-25).
- Quiet output: long logs go to the scratchpad, and only the exit status and failure lines are printed.
- End every commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Out of scope (deliberately)

- **Trimming rule content** (e.g. `permissions.md` duplicating `registry.yaml`). Once excluded it costs nothing at startup, so trimming saves only on-demand reads. Separate decision.
- **Shipping the exclusion in `seeds/settings.json`.** Seeds are copied once into each project and never overwritten, so the list would drift in six places. User settings is one place. Coauthors don't get the setting, so their sessions keep loading everything, which costs them tokens but no functionality.
- **Making `paths:` work for symlinked rules** (real-file copies from `apply.sh`). Rejected because copies drift.

---

### Task 0: Worktree and baseline

- [ ] **Step 1:** Create the worktree with `superpowers:using-git-worktrees`, branch `rule-load-exclusions` off `main`.
- [ ] **Step 2:** Run `python3 -m pytest tests/ -q` to a scratch log and record the pass count. Run `./scripts/check_fork.sh` and record exit 0.
- [ ] **Step 3:** Record the baseline load with the `InstructionsLoaded` harness (Task 4, Step 1) in `~/Research/NAR_settlement`. Expected: 21 `session_start` events.

### Task 1: Consumer audit (read in full, no edits)

The grep inventory below is a **locator**. For each file, read the whole file and record, per mention: (a) does the step need the rule's *content* to act correctly, or is the mention only a citation or rationale; (b) is there already an instruction to read it.

- [ ] **Step 1:** Read every file in the inventory in full and fill in the audit table at `docs/audits/2026-09-29_rule-consumer-audit.md` with columns `file | step | rule | needs content? | already reads? | action`.
- [ ] **Step 2: Find the silent consumers.** These are behaviours that need an excluded rule but never mention it, and grep cannot find them. Check at least:
  - every worker agent (`coder`, `data-engineer`, `writer`, `theorist`, `strategist`, `explorer`, `storyteller`) for the `ai_use_log.md` entry (`ai-disclosure.md`) and the research-journal entry (`logging.md`);
  - `data-engineer` and `coder-critic` for `data-manifest.md`;
  - `writer` for `quarto-pdf.md` and `quarto-word.md`;
  - `coder` for `quarto-empirical.md`.
  Where the agent's own file already carries the format it needs, record "self-contained" and take no action.
- [ ] **Step 3: Check whether subagents load project rules at all** (docs: `code.claude.com/docs/en/sub-agents`, "what loads at startup", then test with the Task 4 harness, dispatching one agent). If subagents never received `.claude/rules/` at startup, agent-side consumers are unchanged by this plan and only skill-side (main-session) consumers need read steps. Record the result, labelled `per docs:` or `tested:`.
- [ ] **Step 4:** Also list the mentions outside this repo, which Task 3 does not edit: `~/.claude/CLAUDE.md` (the quarto rules carve-out) and the project `CLAUDE.md` files of NAR_settlement, ESG and POGM4. Mark each "needs content" or "citation only". Anything that needs content goes into the Task 5 report for the user.

**Inventory (grep, 2026-09-29; mention counts in parentheses):**

- `agents/coder-critic.md`: `quarto-empirical` (3)
- `agents/data-engineer.md`: `quarto-word` (1)
- `agents/writer-critic.md`: `quarto-pdf` (1), `quarto-word` (1)
- `skills/analyze/SKILL.md`: `option-gates` (1), `quarto-empirical` (1)
- `skills/analyze/references/figure-standards.md`: `quarto-pdf` (1), `quarto-word` (1)
- `skills/analyze/references/table-standards.md`: `quarto-pdf` (1), `quarto-word` (1)
- `skills/analyze/templates/chunk-structure.md`: `quarto-empirical` (1)
- `skills/checkpoint/SKILL.md`: `ai-disclosure` (1), `logging` (3), `meta-governance` (1), `session-handoff` (3)
- `skills/discover/SKILL.md`: `option-gates` (4)
- `skills/lit-position/SKILL.md`: `option-gates` (3)
- `skills/pipeline/SKILL.md`: `meta-governance` (1), `option-gates` (1)
- `skills/pipeline/references/{adopt,analyze,recovery,write}.md`: `lifecycle` (1, 1, 2, 1)
- `skills/pipeline/references/{analyze,data,literature,recovery,strategy,submit,theory,write}.md`: `quality` (1 each)
- `skills/promote/SKILL.md`: `meta-governance` (1), `shared-pipeline` (1)
- `skills/review/SKILL.md`: `option-gates` (1)
- `skills/review/config/scoring-rubrics.md`: `quarto-empirical` (1)
- `skills/review/gotchas.md`: `quarto-pdf` (1)
- `skills/review/templates/manuscript-review-8-categories.md`: `quarto-empirical` (1), `quarto-pdf` (2), `quarto-word` (2)
- `skills/revise/SKILL.md`: `option-gates` (1), `revision` (1)
- `skills/strategize/SKILL.md`: `option-gates` (1)
- `skills/submit/SKILL.md`: `ai-disclosure` (1), `option-gates` (1)
- `skills/talk/SKILL.md`: `option-gates` (1)
- `skills/tools/SKILL.md`: `logging` (1), `meta-governance` (1), `quarto-empirical` (1)
- `skills/write/SKILL.md`: `option-gates` (1)
- `skills/ztp-data-tag/SKILL.md`: `option-gates` (1)
- **No mention in any skill or agent:** `permissions`, `data-manifest`, `content-standards`. Step 2 decides whether they have silent consumers.

- [ ] **Step 5: Checkpoint with the user.** Present the audit's action column: how many read steps, which rules (if any) turn out to need always-on loading after all (these move out of the exclusion list), and the subagent finding. **Do not start Task 2 without approval.**

### Task 2: The exclusion list (written, not yet live)

- [ ] **Step 1:** Write the final list to `docs/audits/2026-09-29_rule-consumer-audit.md` as the JSON fragment to be merged into user settings. It is the 15 rules minus anything Task 1 kept always-on:

```json
"claudeMdExcludes": [
  "**/research-claude/rules/permissions.md",
  "**/research-claude/rules/lifecycle.md",
  "**/research-claude/rules/quality.md",
  "**/research-claude/rules/meta-governance.md",
  "**/research-claude/rules/shared-pipeline.md",
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

  Do **not** edit `~/.claude/settings.json` yet. It goes live in Task 5, after the read steps are merged.

### Task 3: Read steps

- [ ] **Step 1:** For each audit row with action "add read", add one line at that step: `Read .claude/rules/<name>.md` plus a few words saying why. Group edits by file, one commit per skill or agent family (`skills/pipeline/**`, `skills/review/**`, `skills/analyze/**`, `agents/*-critic.md`, and so on).
- [ ] **Step 2:** For skills with an **Option gate** (12 skills), put the read step inside the gate's declaration line so `tests/test_option_gates.py` still finds the marker, the rule name and the minimum on that line. Run that test after each edit.
- [ ] **Step 3:** After each commit, run `python3 -m pytest tests/ -q` (scratch log) and `./scripts/check_fork.sh`. Both must stay green. A size-budget failure in `test_skill_contracts.py` means raising the budget in the same commit, with the reason.

### Task 4: Verification harness and evidence

- [ ] **Step 1: Harness.** Write a scratch settings file with an `InstructionsLoaded` hook that appends its stdin JSON to a log, plus the Task 2 `claudeMdExcludes` list. Put the prompt **before** `--allowedTools=Read`: the flag takes a variable number of arguments and swallows a trailing prompt.
- [ ] **Step 2: Startup count.** Run `claude -p` in `~/Research/NAR_settlement` with the harness. Expected: 7 `session_start` events (3 CLAUDE.md + 4 rules) and no excluded file.
- [ ] **Step 3: Point-of-need load.** For one skill per rule family (`/checkpoint` for logging and session-handoff, `/review` for quarto-pdf and quarto-word, a skill with an option gate for option-gates), run it headless on `tests/fixture-project/` and confirm in the transcript (`--output-format stream-json`) that the `Read` of the excluded rule happens before the step that uses it. No timeout (Global Constraints).
- [ ] **Step 4: Regression.** Run `tests/run_fixture.sh --live` against the worktree with the harness settings. It must be green. Compare against the Task 0 baseline.
- [ ] **Step 5:** Record the before and after numbers (files and estimated tokens at startup) and the Step 3 transcript excerpts in the audit file.

### Task 5: Go live

- [ ] **Step 1:** Merge `rule-load-exclusions` to `main` (read steps only; nothing under `rules/` changed).
- [ ] **Step 2:** Merge the Task 2 `claudeMdExcludes` list into `~/.claude/settings.json`, keeping the existing `hooks` block. It currently has no `claudeMdExcludes` key.
- [ ] **Step 3:** Open a fresh interactive session in one paper repo and run `/context`. **Memory files** must list 3 CLAUDE.md files and 4 rules.
- [ ] **Step 4:** Update `CLAUDE.md` (Start-here pointer) and append to `docs/SESSION_REPORT.md`. Report to the user: startup tokens before and after, the out-of-repo mentions from Task 1 Step 4, and `content-standards.md`'s history (it never loaded).

## Rollback

Delete the `claudeMdExcludes` key from `~/.claude/settings.json`. Every rule loads at startup again at once. The read steps are harmless when the rule is already loaded and can stay.
