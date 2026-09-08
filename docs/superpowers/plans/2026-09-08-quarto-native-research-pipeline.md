# Quarto-Native Research Pipeline — Implementation Plan

> **STATUS: COMPLETED 2026-09-08, then AMENDED the same day — read the amendment
> before trusting any verification claim below.** All 18 tasks executed; all six paper
> repos converted, merged and pushed. `scripts/check_fork.sh` exits 0. Outcome, defects
> found during execution, and the pre-existing manuscript findings are recorded in
> `~/Academic/research-claude/docs/SESSION_REPORT.md`. Checkboxes below are marked
> complete; the plan is retained as the historical record of what was decided and why.
>
> **AMENDMENT — a post-completion audit found four defects the plan's own
> verification could not have caught.** All four are fixed and pushed (`9c9ec0c`,
> `b12d6e2`, plus one commit per paper repo); the detail is in the
> `2026-09-08 (audit)` entry of `docs/SESSION_REPORT.md`. Summarised here because
> this plan is the cold-start document and three of its statements were wrong:
>
> 1. **"Verified three ways" (see Verification, below) was two ways.** Nothing
>    checked *membership* — that every upstream item is actually linked in each
>    project. POGM4 silently lacked `rules/session-handoff.md` for a day.
>    `scripts/check_install.sh` now checks this and five other properties; it is the
>    project-side gate the plan never specified.
> 2. **Step 5's `git rm --cached` snippet omits `hooks`** (the Task 18 runbook's
>    version includes it). Applied inconsistently, this left committed symlinks in
>    five of six repos — machine-specific targets that hand a coauthor a clone full
>    of dangling links, defeating D10. Only ESG was correct.
> 3. **C4 ("hooks are linked but never auto-wired") was not a safe default.** No
>    project seeded a `settings.json`, so twelve hooks were installed everywhere and
>    at most one fired. `session-guard.py` was wired in **zero** repos, so `/freeze`
>    and `/careful` shipped with their enforcement mechanism uninstalled while
>    reporting themselves active. `apply.sh` now seeds `templates/settings.json`.
> 4. **Three hooks were inert regardless of wiring** — wrong stdin/env contract or
>    wrong per-event blocking protocol. Two more had been fixed days earlier for the
>    same reason, which is the pattern: a hook that fails this way leaves no trace.
>
> **The generalisable lesson:** every one of these is a *silent* failure — no error,
> no log line, nothing happening. The plan's gates all tested that something was
> present, never that it was doing anything. Where a check can be red-tested by
> injecting the failure, red-test it: `check_install.sh`'s override check was
> vacuous on first write and passed on all six repos before the red test caught it.


> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fork `EconGeo/research-claude` off the dead `hugosantanna/clo-author` submodule into a standalone Quarto-native research pipeline, then symlink that one canonical tree into all six `~/Research` paper repos so a fix lands everywhere at once.

**Architecture:** `research-claude` becomes the single editable source of truth — its own `agents/`, `skills/`, `rules/`, `references/`, `hooks/`, `templates/` directories, seeded from clo-author and enriched with the improvements currently stranded in POGM4 and zoning2026. `apply.sh` stops copying the pipeline and instead creates one relative symlink **per skill directory / agent file / rule file** into the research-claude checkout. Editing a shared skill from any paper session edits the repo working copy directly; `git pull` in research-claude updates all six papers instantly. Coauthors, who cannot see the private paper repos' pipeline because it is gitignored, bootstrap it from the public research-claude at a pinned commit.

**Tech Stack:** Bash (`apply.sh`, checkers), Markdown (agents/skills/rules), Quarto + R (the pipeline's output target), Python 3 (`prose_number_check.py`, path math), git submodules (`ai-audit`, `journal-digest` only).

**Spec:** `~/Academic/research-claude/docs/superpowers/specs/2026-09-08-quarto-native-research-pipeline-design.md`
**Companion checkpoint:** `~/Academic/research-claude/docs/checkpoints/2026-09-08_quarto-native-pipeline-fork.md`
**Related (not implemented here):** `~/Research/docs/writing-pipeline-consolidation.md` — its §6 Phase 3 symlink mechanics are superseded by Phase 5 below; its §8 open item is resolved by D8.

**Working branch:** `design/quarto-native-pipeline` (already exists, holds the spec + checkpoint).

---

## Global Constraints

Copied verbatim from the spec. Every task's requirements implicitly include this section.

- **No installed file may match:** `latexmk`, `\doublespacing`, `threeparttable`, `paper/main.tex`, `paper/sections`, `Emory` (spec criterion 6).
- **No installed file may match a project noun:** `POGM`, `JREPM`, `JRER`, `CoStar`, `SFPP`, `zoning`, `WRLURI`, `NAR`, or `manuscript_quarto_word` (criterion 7).
- **Manuscript filename is `manuscript_<project>.qmd`** — one file, single source of truth. Never `paper/main.tex`, never `manuscript_quarto_word.qmd`.
- **D5 is a standing rule, not a one-time step:** no journal name, dataset name, project noun, or non-standard manuscript filename ships in the template.
- **`zotpilot-skills/` is vendored verbatim from `EconGeo/ZotPilot` and is never edited in place.** Changes go into a bridge skill under `skills/`. It is exempt from the token scans above.
- **Word output uses flextable + PNG at `fig-dpi: 200`; PDF output uses kableExtra + vector.** Per `rules/quarto-word.md` / `rules/quarto-pdf.md`, which are already correct and are the authority.
- **`~/Courses` tooling never enters this pipeline** (user global CLAUDE.md domain separation). See Correction C1 — this rule has already been violated once.

---

## Context

`research-claude` scaffolds every paper project under `~/Research`. Today it does that by *copying* three sources into `PROJECT/.claude/`: the `clo-author` submodule, the `ai-audit` submodule, and its own `skills/` + `rules/`. Four things are wrong with that, all measured in the spec:

1. **`clo-author` is dead and one-way** — pinned at 2026-05-10, nothing pulled in four months.
2. **Value flows out of projects and never returns.** POGM4's `editor` is 366 lines against clo-author's 67. POGM4 and zoning2026 independently taught `coder-critic` Quarto and taught it *different halves* — POGM4 added Quarto/Rmd modes and INV-23/24 manifest coverage, zoning2026 added a Correctness Layer catching hardcoded prose numbers and count-outcome traps. Neither knows the other exists, and a new project scaffolds from the 58-line baseline and gets neither.
3. **Four shipped files give agents actively wrong instructions** — `table-standards.md` says export bare `tabular` (pipeline uses flextable), `figure-standards.md` says `ggsave('fig.pdf')` (Word needs PNG), `working-paper-format.md` applies a LaTeX deduction table to a `.qmd`, `meta-governance.md` says the project is a public template with Emory context. `rules/pipeline-precedence.md` names six files and covers none of these four. Translation-by-precedence is the wrong mechanism.
4. **Copying is the drift engine.** Six projects hold six full copies; two skills forked this session.

The critics are *not* the problem — measured LaTeX coupling across all 47 clo-author files is 0–6%, and ten agents measure exactly 0%. So this is a distribution and curation fix, not a rewrite.

**Intended outcome:** one tree, edited once, linked everywhere; new projects correct from day one; project-side improvements have a path home.

---

## Decisions taken this session

The spec left three open items and the companion consolidation doc left one. All four are now settled, plus two that follow from them.

| # | Decision | Rationale |
|---|---|---|
| **D6** | **Validate on a scratch copy of POGM4 before touching anything under `~/Research`.** | Spec criterion 4 assumes it. Cheap; a live project is a bad test subject. |
| **D7** | **The promotion path back is a real `/promote` skill, not a README checklist.** | The spec's own lesson: "a rule with no executable check is a suggestion." Under symlinks its job shrinks (see Task 15) but does not vanish. |
| **D8** | **Distribution is symlinks only. `research-claude` is the sole edit surface; `apply.sh` never copies the pipeline again.** Resolves the consolidation doc's §8 blocker without creating a new repo: the canonical tree *is* the `research-claude` working copy at `~/Academic/research-claude`, which is already a versioned public repo with a remote. | The user maintains one thing. Updates flow instantly — no re-import step, because there is no copy to re-import. §8's option 1 (a new `EconGeo/research-pipeline` repo) is unnecessary once the fork makes research-claude standalone. |
| **D9** | **`apply.sh --link` links per item, not per directory.** One symlink per skill dir, per agent file, per rule file. A real file already present at a link's destination is treated as a deliberate project override and left alone. | Preserves the spec's §7 escape hatch ("the tree is per-item, not all-or-nothing"). POGM4's `flextable-quarto-word-captions` stays a real local skill beside the links. Also makes re-running `apply.sh --link` meaningful: it adds links for new upstream items and prunes links whose target was deleted. |
| **D10** | **Coauthors bootstrap from the public repo at a pinned commit.** Each paper repo gitignores `.claude/{skills,agents,rules}` and commits `bootstrap-pipeline.sh` + `.claude/pipeline.lock`. | `EconGeo/research-claude` is **public**; all six paper repos are private. So a coauthor needs no access grant — just a clone. Gitignoring the linked dirs means a fresh clone has nothing to dangle. The lock doubles as replication provenance: *this manuscript was written with pipeline SHA abc123*. |
| **D11** | **Rollout: prove on scratch POGM4, then convert all six for real, one branch each, POGM4 first.** Order: POGM4 → NAR_settlement → zoning2026 → ESG → affordable_housing_2026 → BRI. Skip `NAR_settlement_legacy_archive` (frozen). | POGM4 goes first for real because its forked `review`/`submit` must be resolved into the canonical tree before it can link. NAR_settlement is at baseline on every agent, so it is the cleanest confirmation that the tree is complete. |

### D10 detail — the two bootstrap modes, and why they use different checkouts

`bootstrap-pipeline.sh --tip` (maintainer) links into the **shared** checkout at `$RESEARCH_CLAUDE_HOME` (default `~/Academic/research-claude`), kept on `main`. All six projects point there; a `git pull` updates all six.

`bootstrap-pipeline.sh` with no flag (coauthor, or archival reproduction) clones into a **project-local** `PROJECT/.pipeline/research-claude` and detaches at the locked SHA.

The two must not share a checkout. If pinned mode were allowed to detach the shared checkout, it would silently pin *every* project on the maintainer's machine to one paper's locked SHA. Separating them removes that hazard structurally rather than by warning.

---

## Corrections to the spec

Found while verifying the spec's claims against the files. Fix these in the spec as part of Task 1 so the two documents do not disagree.

**C1 — `verifier`: do not harvest from POGM4.** The spec's Work-Item-A row says POGM4 "correctly deleted the LaTeX checks but also dropped the two-mode structure." That is wrong. `~/Research/POGM4/.claude/agents/verifier.md` is not a research verifier at all — its own description reads *"Checks that slides compile, render, deploy, and display correctly"* and its body opens *"You are a verification agent for academic course materials,"* with sections for Beamer slides, TikZ freshness, and `docs/` deployment. It scores **12** hits on `latex|beamer|tikz|revealjs|Slides/` against clo-author's **6** — twice the coupling, not less.

This is a `~/Courses` agent that leaked into a `~/Research` project, the exact failure the user's global CLAUDE.md was written to prevent. **Resolution:** take clo-author's `verifier.md` (two modes, checks 1–10 intact) and rewrite check 1 from `latexmk` to `quarto render` — which is exactly what the B-list `audit-10-checks` port already specifies. Nothing is harvested from POGM4 here. Log the leak in the research journal.

A scan of the other eight POGM4 harvest candidates (`editor`, `methods-referee`, `domain-referee`, `writer-critic`, `writer`, `coder`, `coder-critic`, `strategist`, `theorist`) for `slide|beamer|lecture|course|tikz|revealjs|pedagog` returns **0 hits each** except `domain-referee` at 1 (a benign seminar reference). The leak is isolated to `verifier`. The rest of the harvest table stands.

**C2 — the B-list ports mostly need no porting.** Six of the eight already live inside clo-author *skill* directories that this plan vendors wholesale: `strategize/templates/design-checklists/{did,iv,rdd,event-study,structural,descriptive}.md`, `strategize/templates/{decision-record,robustness-plan}.md` + `pap-templates/{osf,egap,aea-rct}.md`, `submit/templates/audit-10-checks.md`, `talk/templates/narrative-arcs.md`, `write/references/notation-protocol.md`, `write/templates/drafting-gates.md`. Vendoring the skill brings its templates. Only two need real work: `audit-10-checks` check 1 (Task 8) and the FATAL/ADDRESSABLE/TASTE promotion into `/revise` (Task 9).

**C3 — design-checklists stay inside `skills/strategize/templates/`.** The spec's architecture sketch implies `templates/design-checklists/` at repo top level. Moving them there would either orphan `/strategize`'s references or duplicate the files, since `apply.sh` installs skills wholesale. Criterion 9 ("`templates/design-checklists/` ships in the template") is satisfied in place. Update the spec's wording.

**C4 — hooks are vendored and linked but not auto-wired.** The spec lists `hooks/ NEW # 7 session/compact/lint hooks`. Those exist in clo-author and are vendored. But `apply.sh` has never installed hooks, and hooks only fire if a project's `settings.json` references them — so auto-wiring six repos' settings would be a silent behavior change across every project at once. Ship the hooks and link them; leave `settings.json` wiring as a documented opt-in (Task 12).

---

## File structure

Post-fork `~/Academic/research-claude/`:

```
apply.sh                    REWRITE  link mode only for the pipeline; copy only scaffolding seeds
scripts/
  check_fork.sh             NEW      the executable gate — spec criteria 1,3,6,7,8 + D1 deletions
  sync-zotpilot-skills.sh   keep
agents/                     NEW      17 files (21 clo-author − 4 deleted), 7 harvested from POGM4/zoning2026
skills/                     GROWS    13 clo-author skills + 3 existing bridge skills + lit-position + promote
rules/                      GROWS    7 own + 6 kept from clo-author; 6 deleted, 3 rewritten
references/                 NEW      6 clo-author templates + discipline-cards, prompt-formatting-core
hooks/                      NEW      7 clo-author hooks (linked, not auto-wired — C4)
templates/                  GROWS    + gitignore, data_manifest, bootstrap-pipeline.sh, pipeline.lock
root-skills/                DELETE   `new-project` folded into skills/ or dropped (D1)
zotpilot-skills/            unchanged (vendored, exempt)
submodules/
  clo-author/               REMOVE
  ai-audit/                 keep
  journal-digest/           keep
```

Per paper repo under `~/Research/<project>/` after conversion:

```
.claude/
  skills/<name>       → symlink ../../../../Academic/research-claude/skills/<name>
  agents/<name>.md    → symlink …/agents/<name>.md
  rules/<name>.md     → symlink …/rules/<name>.md
  hooks/<name>        → symlink …/hooks/<name>
  references/*.md     → symlinks to ~/Research/.claude/references/  (unchanged, pre-existing)
  pipeline.lock       COMMITTED  repo URL + SHA + timestamp
  settings.json       COMMITTED  project-owned
bootstrap-pipeline.sh COMMITTED  one command for a coauthor
.gitignore            + .claude/{skills,agents,rules,hooks}/ and /.pipeline/
```

---

## Phase 0 — The executable gate

### Task 1: Build `check_fork.sh` and correct the spec

The spec's nine success criteria are the test suite. Make them runnable *first*, so every later task has a red/green cycle instead of a judgment call.

**Files:**
- Create: `~/Academic/research-claude/scripts/check_fork.sh`
- Modify: `~/Academic/research-claude/docs/superpowers/specs/2026-09-08-quarto-native-research-pipeline-design.md` (Work-Item-A `verifier` row; criterion 9 wording)
- Copy this plan to: `~/Academic/research-claude/docs/superpowers/plans/2026-09-08-quarto-native-research-pipeline.md`

**Interfaces:**
- Produces: `scripts/check_fork.sh`, exit 0 = all criteria pass. Every later task runs it.

- [x] **Step 1: Copy this plan into the repo it describes**

```bash
mkdir -p ~/Academic/research-claude/docs/superpowers/plans
cp ~/academic-claude/quality_reports/plans/write-up-the-plan-compiled-beacon.md \
   ~/Academic/research-claude/docs/superpowers/plans/2026-09-08-quarto-native-research-pipeline.md
```

- [x] **Step 2: Write the gate**

Create `scripts/check_fork.sh`:

```bash
#!/usr/bin/env bash
# check_fork.sh — executable gate for the Quarto-native fork.
# Implements the spec's success criteria 1, 3, 6, 7, 8 and the D1 deletions.
# Exit 0 = fork is complete and clean.
set -uo pipefail
RC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0

# Directories that ship into a project. zotpilot-skills/ is vendored verbatim and exempt (D5).
SHIP=(agents skills rules references hooks templates)

scan() {  # scan <label> <extended-regex>
  local label="$1" pat="$2" hits present=()
  local d; for d in "${SHIP[@]}"; do [[ -d "$RC/$d" ]] && present+=("$d"); done
  if [[ ${#present[@]} -eq 0 ]]; then echo "SKIP [$label] (no ship dirs yet)"; return; fi
  hits="$(cd "$RC" && grep -rInE "$pat" "${present[@]}" 2>/dev/null)"
  if [[ -n "$hits" ]]; then
    echo "FAIL [$label]"; printf '%s\n' "$hits" | sed 's/^/    /'; fail=1
  else
    echo "PASS [$label]"
  fi
}

absent() {  # absent <label> <path>
  if [[ -e "$RC/$2" ]]; then echo "FAIL [$1] $2 still present"; fail=1
  else echo "PASS [$1] $2 gone"; fi
}

contains() {  # contains <label> <file> <pattern>
  if [[ -f "$RC/$2" ]] && grep -q "$3" "$RC/$2"; then echo "PASS [$1]"
  else echo "FAIL [$1] $2 missing /$3/"; fail=1; fi
}

echo "── criterion 6: no LaTeX / multi-file pipeline residue ──"
scan latex-residue 'latexmk|\\doublespacing|threeparttable|paper/main\.tex|paper/sections|Emory'

echo "── criterion 7: no project nouns, no non-standard manuscript filename ──"
scan project-nouns 'POGM|JREPM|JRER|CoStar|SFPP|zoning|WRLURI|NAR|manuscript_quarto_word'

echo "── criteria 1-3: the fork is structural ──"
absent clo-author-submodule submodules/clo-author
absent pipeline-precedence  rules/pipeline-precedence.md
if grep -q 'clo-author' "$RC/.gitmodules" 2>/dev/null; then
  echo "FAIL [gitmodules] .gitmodules still names clo-author"; fail=1
else echo "PASS [gitmodules]"; fi
if grep -q 'CLO_SKIP_SKILLS' "$RC/apply.sh" 2>/dev/null; then
  echo "FAIL [apply.sh] still references CLO_SKIP_SKILLS"; fail=1
else echo "PASS [apply.sh]"; fi

echo "── criterion 8: the coder-critic merge kept both halves ──"
contains cc-zoning-half  agents/coder-critic.md 'Correctness Layer'
contains cc-pogm-half    agents/coder-critic.md 'INV-23'

echo "── D1: the orchestration graph is gone ──"
for gone in agents/orchestrator.md agents/guide-writer.md agents/librarian.md \
            agents/librarian-critic.md rules/permissions.md rules/lifecycle.md \
            rules/workflow.md rules/working-paper-format.md rules/meta-governance.md \
            root-skills; do
  absent d1-deletions "$gone"
done

echo "── C1: no ~/Courses domain leak ──"
scan course-leak 'academic course materials|Beamer slides|TikZ Freshness'

[[ $fail -eq 0 ]] && echo "✓ check_fork: PASS" || echo "✗ check_fork: FAIL"
exit $fail
```

- [x] **Step 3: Run it and confirm it fails**

```bash
chmod +x ~/Academic/research-claude/scripts/check_fork.sh
~/Academic/research-claude/scripts/check_fork.sh; echo "exit=$?"
```

Expected: `exit=1`, with FAIL on `clo-author-submodule`, `pipeline-precedence`, `gitmodules`, `apply.sh`, `cc-zoning-half`, `cc-pogm-half`, and `root-skills`. This is the red state the rest of the plan turns green.

- [x] **Step 4: Apply corrections C1 and C3 to the spec**

In `docs/superpowers/specs/2026-09-08-quarto-native-research-pipeline-design.md`:
- Work items §A, `verifier` row — replace the Source/De-project cells with: `clo-author | POGM4's verifier.md is a leaked ~/Courses slide agent (12 LaTeX hits vs clo-author's 6) — do not harvest. Take clo-author's two-mode structure; rewrite check 1 latexmk → quarto render.`
- Success criterion 9 — change `templates/design-checklists/ ships in the template` to `skills/strategize/templates/design-checklists/ ships in the template (in-skill; skills travel with their templates)`.

- [x] **Step 5: Commit**

```bash
cd ~/Academic/research-claude
git add scripts/check_fork.sh docs/superpowers/
git commit -m "test: add check_fork.sh gate; correct spec verifier row (POGM4 leak) and criterion 9

The spec's verifier harvest row was wrong: POGM4's verifier.md is the
~/Courses slide verifier, not a de-LaTeXed research agent.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Phase 1 — Agents: vendor and harvest

### Task 2: Vendor the 13 unchanged clo-author agents

**Files:**
- Create: `agents/{coder,data-engineer,explorer,explorer-critic,storyteller,storyteller-critic,strategist,strategist-critic,theorist,theorist-critic,verifier,writer,writer-critic}.md`
- Read from: `submodules/clo-author/.claude/agents/`

**Interfaces:**
- Produces: `agents/` directory. Tasks 3–5 add to it; Task 13 links it.

- [x] **Step 1: Copy the vendor-as-is set**

```bash
cd ~/Academic/research-claude && mkdir -p agents
CLO=submodules/clo-author/.claude/agents
for a in coder data-engineer explorer explorer-critic storyteller storyteller-critic \
         strategist strategist-critic theorist theorist-critic verifier writer writer-critic; do
  cp "$CLO/$a.md" "agents/$a.md"
done
ls agents | wc -l   # expect 13
```

- [x] **Step 2: De-LaTeX `storyteller` and `storyteller-critic`**

Per spec §A: Quarto-only. In both files remove every reference to `beamer-scaffold.tex` and Beamer output; keep `quarto-scaffold.qmd`. Also delete the scaffold itself in Task 7.

- [x] **Step 3: Rewrite `verifier` check 1 (correction C1 + B-list `audit-10-checks`)**

In `agents/verifier.md`, section `### 1. LaTeX Compilation` → rename to `### 1. Manuscript Render` and replace the `latexmk` command with:

```
Run: quarto render manuscript_<project>.qmd
Pass: exit code 0, and the rendered .docx/.pdf timestamp is newer than the .qmd
Fail: any non-zero exit, or a render that silently skips a chunk (check for
      "ERROR" or "WARNING" in the render log)
```

Leave the two-mode structure (Standard / Submission) and checks 2–10 unchanged — they are format-independent.

- [x] **Step 4: Run the gate**

```bash
scripts/check_fork.sh 2>&1 | grep -E 'latex-residue|project-nouns|course-leak'
```

Expected: `PASS [latex-residue]`, `PASS [project-nouns]`, `PASS [course-leak]`. If `latex-residue` fails, the storyteller de-LaTeXing or the verifier rewrite is incomplete — fix before committing.

- [x] **Step 5: Commit**

```bash
git add agents/ && git commit -m "feat(agents): vendor 13 format-agnostic clo-author agents

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

### Task 3: Harvest the six improved POGM4 agents

The whole point of the fork: 299 lines of `editor` improvements, plus four other agents that grew in a project and never came home.

**Files:**
- Create/overwrite: `agents/{editor,methods-referee,domain-referee,writer-critic,writer,coder}.md`
- Read from: `~/Research/POGM4/.claude/agents/`

- [x] **Step 1: Copy the harvest set**

```bash
cd ~/Academic/research-claude
P=~/Research/POGM4/.claude/agents
for a in editor methods-referee domain-referee writer-critic writer coder; do
  cp "$P/$a.md" "agents/$a.md"
done
wc -l agents/editor.md   # expect 366, not 67
```

Do **not** copy `verifier.md` — correction C1.

- [x] **Step 2: De-project (D5)**

```bash
grep -rInE 'POGM|JREPM|JRER|CoStar|SFPP|zoning|WRLURI|NAR|manuscript_quarto_word' agents/
```

The spec measured exactly one leaked token across the harvest candidates (`manuscript_quarto_word` in `coder-critic`, handled in Task 4). Anything this grep returns in these six files is new — replace project nouns with `<project>` and `manuscript_quarto_word` with `manuscript_<project>`.

- [x] **Step 3: Note what `editor` brings**

`editor.md` carries capability that has never run: a novelty check with an explicit anti-hallucination caveat (every "already done" claim must carry a URL or DOI, else report "unable to verify"), referee selection that refuses to draw the same disposition twice, and a `--variance N` mode running 3–5 referees to *estimate* review variance rather than enforce diversity. Confirm all three survive the copy; they are the reason this agent is worth 366 lines.

- [x] **Step 4: Run the gate, then commit**

```bash
scripts/check_fork.sh 2>&1 | grep -E 'project-nouns|latex-residue'
git add agents/ && git commit -m "feat(agents): harvest editor, referees, writer, writer-critic, coder from POGM4

editor grows 67 -> 366 lines: novelty check with anti-hallucination caveat,
non-repeating referee dispositions, --variance N mode.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

### Task 4: Merge `coder-critic` from two projects

The sharpest case in the spec. POGM4 and zoning2026 each taught this agent a different half of what it needs, and neither knows the other exists.

**Files:**
- Create: `agents/coder-critic.md`
- Read from: `~/Research/POGM4/.claude/agents/coder-critic.md` (99 lines), `~/Research/zoning2026/.claude/agents/coder-critic.md` (82 lines), `submodules/clo-author/.claude/agents/coder-critic.md` (58 lines)

- [x] **Step 1: See what each side has**

```bash
cd ~/Academic/research-claude
diff <(grep '^#' ~/Research/POGM4/.claude/agents/coder-critic.md) \
     <(grep '^#' ~/Research/zoning2026/.claude/agents/coder-critic.md)
```

Both share `Cold-Read Protocol`, `Your Task`, `Task-Specific Resources`, `Standalone Mode`, `Three Strikes Escalation`, `What You Do NOT Do`. POGM4 alone adds `## Quarto Empirical Mode` and `## Rmd Mode`. zoning2026 alone adds `## Correctness Layer (score correctness, not just hygiene)`.

- [x] **Step 2: Build the merge**

Start from POGM4's file (it is the longer superset of the shared sections). Insert zoning2026's `## Correctness Layer` block verbatim between `## Task-Specific Resources` and `## Standalone Mode`. The Correctness Layer covers: hardcoded prose numbers (INV-11), no derived CSVs written into `data/raw/`, cache discipline, and zero-inflation / extrapolation traps for count outcomes. Drop `## Rmd Mode` only if the pipeline is Quarto-only — **keep it**; `rules/quarto-format.md` still documents an Rmd path and dropping it would lose coverage for legacy projects.

- [x] **Step 3: De-project**

```bash
sed -i '' 's/manuscript_quarto_word/manuscript_<project>/g' agents/coder-critic.md
grep -nE 'POGM|zoning|NAR|manuscript_quarto_word' agents/coder-critic.md   # expect no output
```

- [x] **Step 4: Verify the merge kept both halves — this is spec criterion 8**

```bash
scripts/check_fork.sh 2>&1 | grep -E 'cc-zoning-half|cc-pogm-half'
```

Expected: `PASS [cc-zoning-half]` and `PASS [cc-pogm-half]`. Both must pass; either one failing means half the merge was lost.

- [x] **Step 5: Commit**

```bash
git add agents/coder-critic.md
git commit -m "feat(agents): merge coder-critic from POGM4 and zoning2026

POGM4 taught it Quarto/Rmd modes and INV-23/24 manifest coverage.
zoning2026 taught it a Correctness Layer (INV-11 hardcoded numbers, derived
CSVs in data/raw, cache discipline, count-outcome traps). Neither knew about
the other; a new project got neither.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

### Task 5: Delete the orchestration and librarian agents (D1, D3)

**Files:**
- Ensure absent: `agents/{orchestrator,guide-writer,librarian,librarian-critic}.md`

- [x] **Step 1: Confirm they were never vendored**

```bash
cd ~/Academic/research-claude
ls agents/ | grep -E 'orchestrator|guide-writer|librarian' || echo "none present — correct"
ls agents/ | wc -l   # expect 17 (clo-author's 21 minus these 4; the harvest overwrote, not added)
```

Expected final `agents/` contents (17 files): `coder, coder-critic, data-engineer, domain-referee, editor, explorer, explorer-critic, methods-referee, storyteller, storyteller-critic, strategist, strategist-critic, theorist, theorist-critic, verifier, writer, writer-critic`.

`humanize-auditor` and `claim-verifier` are **not** here — they stay in the live `ai-audit` submodule (spec §A).

- [x] **Step 2: Record why, so this is not undone later**

Create `docs/decisions/2026-09-08_cut-the-orchestration-graph.md`:

> **Decision:** delete `orchestrator`, `guide-writer`, `librarian`, `librarian-critic`.
> **orchestrator** was structurally unreachable — only `/new-project` dispatches it, and `apply.sh` refused to install `/new-project`. Its phase graph also serializes the coder↔writer looping the research journal shows actually happens. Worker→critic pairing and three-strikes escalation survive in `rules/agents.md`.
> **librarian** was WebSearch-first, contradicting `rules/literature-search-order.md` (local Zotero first). Its content survives in `skills/lit-position/` (Task 10).
> **What would invalidate this:** a project that genuinely needs multi-phase autonomous dispatch, or a literature workflow ZotPilot cannot serve.

- [x] **Step 3: Run the gate, then commit**

```bash
scripts/check_fork.sh 2>&1 | grep 'd1-deletions'
git add agents/ docs/decisions/
git commit -m "feat(agents): cut orchestrator, guide-writer, librarian pair (D1, D3)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Phase 2 — Skills

### Task 6: Vendor the clo-author skills and absorb `root-skills/`

**Files:**
- Create: `skills/{analyze,careful,checkpoint,dashboard,discover,freeze,review,revise,strategize,submit,talk,tools,write}/`
- Delete: `root-skills/`
- Keep untouched: `skills/{new-project-ztp,obsidian-digest-sync,ztp-data-tag}/`

- [x] **Step 1: Copy the 13 skills (all but `new-project`)**

```bash
cd ~/Academic/research-claude
CLO=submodules/clo-author/.claude/skills
for s in analyze careful checkpoint dashboard discover freeze review revise \
         strategize submit talk tools write; do
  cp -r "$CLO/$s" skills/
done
ls skills/   # expect 16 = 13 vendored + 3 existing bridge skills
```

Each skill brings its `templates/` and `references/` subtrees — that is C2, and it is why six of the eight B-list ports need no separate work.

- [x] **Step 2: Drop `root-skills/` and `new-project`**

```bash
git rm -r root-skills
```

`new-project` is superseded by `rules/quarto-empirical.md` (this is what `CLO_SKIP_SKILLS` existed to express) and by `skills/new-project-ztp/`, which stays.

- [x] **Step 3: Delete the Beamer scaffold (Quarto-only, spec §A)**

```bash
rm skills/talk/templates/beamer-scaffold.tex
grep -rn 'beamer-scaffold' skills/ || echo "no dangling references"
```

If that grep returns hits, remove the referencing lines from `skills/talk/SKILL.md`.

- [x] **Step 4: Delete the spec's C-list — dormant, and correctly so**

Vendoring a skill wholesale (C2) brings its templates, including three the spec explicitly drops. Remove them now, or they ship by accident:

```bash
rm skills/review/templates/causal-audit-4-phases.md        # no causal claims in a descriptive paper
rm skills/review/templates/literature-review-6-categories.md  # superseded by lit-position (D3)
rm skills/write/templates/claim-source-map.md              # superseded by inline `r` + prose_number_check.py
grep -rn 'causal-audit-4-phases\|literature-review-6-categories\|claim-source-map' skills/ rules/ agents/
```

Every hit from that grep must be removed from the referencing file. The rest of the C-list (`execution-trace`, `pipeline-state.json`, `requirements-spec`, `constitutional-governance`, `quality-report`) lives in `clo-author/templates/`, which this plan never vendors — nothing to do.

`literature-review-6-categories.md`'s six criteria are not lost: they become the self-check in `skills/lit-position/` (Task 10, Step 1, item 6). Read it before deleting.

- [x] **Step 5: Run the gate, then commit**

```bash
scripts/check_fork.sh
git add -A skills root-skills
git commit -m "feat(skills): vendor 13 clo-author skills; drop root-skills/ and new-project

Skills carry their own templates/ and references/, which lands six of the
eight B-list ports for free (design-checklists, decision-record,
robustness-plan, pap-templates, narrative-arcs, notation-protocol,
drafting-gates).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

### Task 7: Resolve POGM4's two forked skills

POGM4 forked `review` (c23707 → 1e7191) and `submit` (f8989f → ebcef4) this session. They must be resolved into the canonical tree before POGM4 can be linked to it.

**Files:**
- Modify: `skills/review/SKILL.md`, `skills/submit/SKILL.md`

- [x] **Step 1: See what diverged**

```bash
cd ~/Academic/research-claude
diff -u submodules/clo-author/.claude/skills/review/SKILL.md ~/Research/POGM4/.claude/skills/review/SKILL.md
diff -u submodules/clo-author/.claude/skills/submit/SKILL.md ~/Research/POGM4/.claude/skills/submit/SKILL.md
```

- [x] **Step 2: Upstream what is worth keeping; drop the rest**

Judgment call per hunk. Keep anything Quarto-aware, anything that reflects the corrected write gate, anything generalizable. Drop anything naming POGM4, its journal, or its dataset. Record the decision in one line per dropped hunk in the commit message so the choice is auditable.

- [x] **Step 3: Confirm nothing project-specific survived**

```bash
grep -nE 'POGM|JREPM|JRER|CoStar|SFPP|WRLURI' skills/review/SKILL.md skills/submit/SKILL.md
```

Expected: no output.

- [x] **Step 4: Commit**

```bash
git add skills/review skills/submit
git commit -m "fix(skills): resolve POGM4's review/submit forks into the canonical tree

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

### Task 8: Rewrite `audit-10-checks` check 1 (B-list port)

**Files:**
- Modify: `skills/submit/templates/audit-10-checks.md`

- [x] **Step 1: Replace check 1**

Change the LaTeX-compilation check to:

```
### 1. Manuscript renders
Run: quarto render manuscript_<project>.qmd
Pass: exit 0, output artifact newer than the source .qmd
```

Checks 5–10 (package inventory, dependency verification, data provenance, execution verification, output cross-reference, README completeness) port unchanged — they are format-independent.

- [x] **Step 2: Verify and commit**

```bash
grep -n 'latexmk' skills/submit/templates/audit-10-checks.md   # expect no output
scripts/check_fork.sh 2>&1 | grep latex-residue                 # expect PASS
git add skills/submit/templates/audit-10-checks.md
git commit -m "fix(submit): audit check 1 is quarto render, not latexmk

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

### Task 9: Promote FATAL / ADDRESSABLE / TASTE into `/revise` (B-list port)

Referee-comment classification currently lives buried in `skills/review/templates/disposition-pool.md` and has never produced an artifact. `rules/revision.md` classifies comments as NEW ANALYSIS / CLARIFICATION / DISAGREE / MINOR — a routing axis. FATAL/ADDRESSABLE/TASTE is a *severity* axis and is what decides whether a paper survives.

**Files:**
- Modify: `skills/revise/SKILL.md`
- Read: `skills/review/templates/disposition-pool.md`

- [x] **Step 1: Add a severity pass to `/revise`**

In `skills/revise/SKILL.md`, before the existing routing table, add:

```markdown
## Step 1: Classify severity, then route

Every referee comment gets both a severity and a route.

| Severity | Meaning | Consequence |
|---|---|---|
| **FATAL** | The finding, if correct, invalidates a headline claim | Stop. Re-estimate before drafting any response. Escalate to the user. |
| **ADDRESSABLE** | Real, fixable within the current design | Route normally (table below). |
| **TASTE** | The referee would have written a different paper | Draft a diplomatic disagreement; never silently comply. |

A TASTE comment answered with new analysis wastes a revision cycle. A FATAL
comment answered with prose is how papers get rejected on the second round.
```

Keep the existing NEW ANALYSIS / CLARIFICATION / DISAGREE / MINOR routing table as Step 2.

- [x] **Step 2: Commit**

```bash
git add skills/revise/SKILL.md
git commit -m "feat(revise): add FATAL/ADDRESSABLE/TASTE severity pass before routing

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

### Task 10: New bridge skill `skills/lit-position/` (D3)

`zotpilot-skills/` is vendored and must never be edited in place — editing it would recreate the one-way drift this fork exists to eliminate. Follow the existing bridge pattern (`new-project-ztp`, `ztp-data-tag`).

**Files:**
- Create: `skills/lit-position/SKILL.md`
- Read for content: `submodules/clo-author/.claude/agents/librarian.md`, `librarian-critic.md`, `skills/review/templates/literature-review-6-categories.md`

**Interfaces:**
- Produces: a skill that outputs `annotated_bibliography.md`, `frontier_map.md`, `positioning.md` into `quality_reports/literature/`.

- [x] **Step 1: Write the skill**

`skills/lit-position/SKILL.md` frontmatter:

```yaml
---
name: lit-position
description: Position a project against the literature using the local Zotero corpus. Calls ztp-research to find and ingest, ztp-review to synthesize, then produces the two artifacts ZotPilot does not — frontier_map.md and positioning.md. Use when starting a project, writing an introduction, or defending a contribution claim. Local-first per rules/literature-search-order.md.
---
```

Body, in order:
1. **Find + ingest** — invoke `ztp-research` for the topic. Local library first; external databases only for what the library lacks.
2. **Synthesize** — invoke `ztp-review` over the local corpus.
3. **Produce `annotated_bibliography.md`** — one entry per paper: claim, method, data, and *what it leaves open*.
4. **Produce `frontier_map.md`** — ZotPilot produces nothing like this. Cluster the corpus by what is settled, what is contested, and what is unexamined.
5. **Produce `positioning.md`** — one paragraph stating what this project adds, naming the two or three papers it sits between.
6. **Self-check** against the six `librarian-critic` categories: coverage, journal quality, scope calibration, recency, categorization quality, and whether the positioning claim is defensible against the closest paper.

Carry over `librarian.md`'s substantive guidance on frontier mapping and positioning; drop its WebSearch-first search order, which contradicts `rules/literature-search-order.md`.

- [x] **Step 2: Commit**

```bash
git add skills/lit-position/
git commit -m "feat(skills): add lit-position ZotPilot bridge, replacing the librarian agents (D3)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Phase 3 — Rules: delete, fold, rewrite

### Task 11: Delete six rules and fold pairing into `rules/agents.md`

**Files:**
- Create: `rules/agents.md`, `rules/{content-invariants,content-standards,html-dashboard,logging,quality,revision}.md` (from clo-author)
- Never create: `rules/{permissions,lifecycle,workflow,working-paper-format,meta-governance}.md`
- Delete: `rules/pipeline-precedence.md`

- [x] **Step 1: Vendor the six rules worth keeping**

```bash
cd ~/Academic/research-claude
CLO=submodules/clo-author/.claude/rules
for r in agents content-invariants content-standards html-dashboard logging quality revision; do
  cp "$CLO/$r.md" "rules/$r.md"
done
```

`permissions.md`, `lifecycle.md`, and `workflow.md` are the orchestration dependency graph — deleted with the orchestrator (D1). `working-paper-format.md` is a live LaTeX deduction table applied to `.qmd` files. `meta-governance.md` tells agents this is a public template with Emory context and biology-PhD forkers.

- [x] **Step 2: Fold the surviving orchestration content into `rules/agents.md`**

`rules/agents.md` already has the three sections that matter — `## 1. Adversarial Pairing`, `## 2. Separation of Powers`, `## 3. Three Strikes Escalation`. Add a fourth:

```markdown
## 4. No phase graph

Worker→critic pairing is the whole protocol. There is no orchestrator, no
dependency graph, and no phase gating. Any skill may invoke any agent when its
inputs exist. The coder↔writer loop in particular is expected to cycle —
serializing it was the orchestrator's mistake.
```

Then delete every reference to `permissions.md`, `lifecycle.md`, and `workflow.md` across `rules/` and `skills/`:

```bash
grep -rn 'permissions\.md\|lifecycle\.md\|workflow\.md\|pipeline-precedence' rules/ skills/ agents/
```

Every hit must be removed or rewritten. A dangling reference to a deleted rule is how agents end up guessing.

- [x] **Step 3: Delete `pipeline-precedence.md` (criterion 3)**

```bash
git rm rules/pipeline-precedence.md
```

Nothing is left to take precedence over — that is the entire point of rewriting rather than translating.

- [x] **Step 4: Run the gate, then commit**

```bash
scripts/check_fork.sh 2>&1 | grep -E 'd1-deletions|pipeline-precedence'
git add -A rules
git commit -m "feat(rules): keep 7, delete 5 orchestration/LaTeX rules, delete pipeline-precedence

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

### Task 12: Rewrite the three standards files that give wrong instructions (D-list)

These are the files that made this fork necessary — `pipeline-precedence.md` never covered them, so agents have been reading them as authoritative.

**Files:**
- Rewrite: `skills/analyze/references/table-standards.md` (321 lines)
- Rewrite: `skills/analyze/references/figure-standards.md` (206 lines)
- Rewrite: `rules/content-standards.md` (454 lines)
- Modify: `rules/content-invariants.md` (INV-12, INV-13, INV-22)

- [x] **Step 1: `table-standards.md` → flextable / kableExtra**

Delete every instruction to export bare `tabular`, wrap in `threeparttable`, or prefer `talltblr`. Replace with the two paths already documented correctly in `rules/quarto-word.md` and `rules/quarto-pdf.md`:

- **Word:** `modelsummary(..., output = "flextable")` with `set_flextable_defaults()` in the setup chunk and `fit_to_width(PAGE_WIDTH)`; notes as an italic paragraph or a `custom-style="Footnote Text"` div after the chunk.
- **PDF:** `modelsummary(..., booktabs = TRUE)` / `kbl(..., booktabs = TRUE)`; notes via the `notes` argument.
- **Both:** chunk label starts `tbl-`, `#| tbl-cap:` present, never `\hline`.

Do not duplicate `quarto-word.md` / `quarto-pdf.md` — reference them and keep this file to the table-design judgment they do not cover (what belongs in a table, column ordering, significance-star conventions, when a table should be a figure).

- [x] **Step 2: `figure-standards.md` → PNG for Word, vector for PDF**

Delete `ggsave('fig.pdf')` and every "output PDF for figures" instruction; Quarto cannot embed a PDF in Word. Replace with `fig-width: 6.5`, `dpi: 200` for Word and automatic vector for PDF. **Keep** the format-independent content — no in-figure titles (they go in `fig-cap`), colorblind-safe palettes, serif fonts — which is most of the file and is correct.

- [x] **Step 3: `content-standards.md` — keep the format-independent 91%**

The spec measured this file at 9% LaTeX-coupled. Strip those lines; keep everything else. Do not rewrite what is already right.

- [x] **Step 4: `content-invariants.md` — INV-12, INV-13, INV-22**

Rewrite INV-12 and INV-13 for chunk options and inline `` `r ` `` rather than LaTeX macros. **Retire INV-22** (claim-source map) — superseded by inline `r` plus `prose_number_check.py`, which enforce the same property mechanically. Mark it `RETIRED 2026-09-08` with the reason rather than deleting the number, so old references still resolve.

Then act on the spec's §5 lesson — *a rule with no executable check is a suggestion*: beside every invariant, name the command that enforces it, or mark it `reviewer-judgment` explicitly. `prose_number_check.py` enforces INV-11; `check_fork.sh` enforces the D5 naming rules; `quarto render` enforces nothing about literals, which is precisely the false assumption that started this.

- [x] **Step 5: Run the gate, then commit**

```bash
scripts/check_fork.sh
git add rules/ skills/analyze/references/
git commit -m "fix(rules): rewrite table/figure/content standards for Quarto; retire INV-22

These four files were giving agents concretely wrong instructions
(bare tabular, ggsave fig.pdf) and pipeline-precedence.md never named them.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

### Task 13: Vendor `references/` and `hooks/`

**Files:**
- Create: `references/*.md` (8), `hooks/*` (7)

- [x] **Step 1: Copy**

```bash
cd ~/Academic/research-claude && mkdir -p references hooks
cp submodules/clo-author/.claude/references/*.md references/
cp ~/Research/POGM4/.claude/references/{discipline-cards,prompt-formatting-core,coding-standards-rmd}.md references/ 2>/dev/null || true
cp submodules/clo-author/.claude/hooks/* hooks/
ls references hooks
```

`references/` holds *templates* — `domain-profile.md`, `journal-profiles.md`, `personal-style-guide.md` are filled in per user, and every `~/Research` project already symlinks those three to `~/Research/.claude/references/`. `apply.sh` must not overwrite an existing reference file (it already gets this right).

- [x] **Step 2: Ship hooks but do not auto-wire them (correction C4)**

Add `hooks/README.md`:

> These hooks are linked into every project but fire only if `.claude/settings.json`
> references them. Wiring is deliberately opt-in: enabling seven hooks across six
> repos at once is a silent behavior change. To enable, add the hook to the project's
> own `settings.json` — that file stays project-owned and is never linked.

- [x] **Step 3: Commit**

```bash
git add references/ hooks/
git commit -m "feat: vendor references/ templates and hooks/ (opt-in wiring, C4)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Phase 4 — `apply.sh`: link, don't copy

### Task 14: Rewrite `apply.sh` for link mode

The drift engine becomes the link engine. This is D8 and D9.

**Files:**
- Rewrite: `apply.sh` (339 lines → roughly 180; the submodule traversal, `CLO_SKIP_SKILLS`, and steps 1–7 collapse)
- Create: `templates/pipeline.lock.template`

**Interfaces:**
- Consumes: `agents/`, `skills/`, `rules/`, `hooks/`, `references/`, `templates/` from Tasks 2–13.
- Produces: `apply.sh --project-dir DIR --link [--tip]`, which creates per-item relative symlinks, prunes dead ones, copies scaffolding seeds, and writes `.claude/pipeline.lock`.

- [x] **Step 1: Delete the copy machinery**

Remove from `apply.sh`: `CLO_SKIP_SKILLS` (lines 70, 90, 180–186), the entire `── 1. clo-author` block (lines ~173–212), and the `git submodule update --remote` for clo-author. Keep the ai-audit block, the ZotPilot block, and steps 8–10 (data_manifest, .gitignore, --link-references) — those copy *scaffolding seeds*, which are project-owned and meant to be edited, so they must stay copies.

- [x] **Step 2: Add the linking core**

First extend the existing argument parser (around `apply.sh:60-95`, beside `UPDATE_MODE` and `WITH_DIGEST`) with the two new flags:

```bash
LINK_MODE=false
TIP_MODE=false
# ... in the arg loop, beside --update / --with-digest:
    --link) LINK_MODE=true; shift ;;
    --tip)  TIP_MODE=true;  shift ;;
```

`--link` is what makes this a link install; `--tip` is passed through by `bootstrap-pipeline.sh --tip` and only affects which checkout the caller already selected, so `apply.sh` records it in the lock comment and otherwise ignores it. Then add:

```bash
# ── relative path helper (macOS has no realpath --relative-to) ────────────────
relpath() { python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$1" "$2"; }

# ── link_items <src-dir> <dest-dir> ──────────────────────────────────────────
# One symlink per item. A real (non-symlink) entry at the destination is a
# deliberate project override (D9) and is left untouched.
link_items() {
  local src="$1" dest="$2" name target
  mkdir -p "$dest"
  for item in "$src"/*; do
    [[ -e "$item" ]] || continue
    name="$(basename "$item")"
    target="$dest/$name"
    if [[ -e "$target" && ! -L "$target" ]]; then
      echo "    ⤷ $name is a real file here — project override, left alone"
      continue
    fi
    ln -sfn "$(relpath "$item" "$dest")" "$target"
  done
}

# ── prune_dead_links <dest-dir> ──────────────────────────────────────────────
# A link whose target no longer exists means the item was deleted upstream.
prune_dead_links() {
  local dest="$1" dead
  [[ -d "$dest" ]] || return 0
  while IFS= read -r -d '' dead; do
    echo "    ⤷ removing stale link $(basename "$dead")"
    rm "$dead"
  done < <(find "$dest" -maxdepth 1 -type l ! -exec test -e {} \; -print0 2>/dev/null)
}

if [[ "$LINK_MODE" == true ]]; then
  echo "→ Linking pipeline from $SCRIPT_DIR"
  for d in skills agents rules hooks; do
    [[ -d "$SCRIPT_DIR/$d" ]] || continue
    echo "  $d/"
    prune_dead_links "$PROJECT_DIR/.claude/$d"
    link_items "$SCRIPT_DIR/$d" "$PROJECT_DIR/.claude/$d"
  done
  # ai-audit ships two skills and two agents from a live submodule — link those too
  AI="$SCRIPT_DIR/submodules/ai-audit"
  [[ -d "$AI/skills" ]] && link_items "$AI/skills" "$PROJECT_DIR/.claude/skills"
  [[ -d "$AI/agents" ]] && link_items "$AI/agents" "$PROJECT_DIR/.claude/agents"
  [[ -d "$AI/rules"  ]] && link_items "$AI/rules"  "$PROJECT_DIR/.claude/rules"
  # ZotPilot skills are vendored real files here, so linking them is correct too
  link_items "$SCRIPT_DIR/zotpilot-skills" "$PROJECT_DIR/.claude/skills"
fi
```

Note `zotpilot-skills/VENDORED.md` is a file, not a skill dir — `link_items` will link it into `.claude/skills/`. Guard the loop with `[[ -d "$item" ]] || continue` for that one call, matching the existing behavior at `apply.sh:246`.

- [x] **Step 3: Write the lock file**

```bash
write_lock() {
  local sha; sha="$(git -C "$SCRIPT_DIR" rev-parse HEAD)"
  cat > "$PROJECT_DIR/.claude/pipeline.lock" <<EOF
# Which research-claude produced this project's pipeline.
# Committed on purpose: it is replication provenance, and it is what
# ./bootstrap-pipeline.sh checks out for a coauthor.
repo=https://github.com/EconGeo/research-claude.git
commit=$sha
generated=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
}
```

- [x] **Step 4: Update the project `.gitignore` template (D10)**

Append to `templates/gitignore`:

```
# Pipeline: linked from research-claude, not project content.
# Run ./bootstrap-pipeline.sh to materialize.
.claude/skills/
.claude/agents/
.claude/rules/
.claude/hooks/
/.pipeline/
```

- [x] **Step 5: Test link mode on a throwaway directory**

```bash
cd ~/Academic/research-claude
rm -rf /tmp/linktest && mkdir -p /tmp/linktest
./apply.sh --project-dir /tmp/linktest --link
ls -l /tmp/linktest/.claude/skills/ | head -5      # every entry should be a symlink
readlink /tmp/linktest/.claude/agents/editor.md    # relative path
[[ -f /tmp/linktest/.claude/skills/write/SKILL.md ]] && echo "resolves ✓"
cat /tmp/linktest/.claude/pipeline.lock
```

Expected: symlinks with relative targets, all resolving; a lock file naming the current SHA.

- [x] **Step 6: Test the override and prune behavior (D9)**

```bash
rm /tmp/linktest/.claude/rules/quality.md
echo "# project override" > /tmp/linktest/.claude/rules/quality.md
./apply.sh --project-dir /tmp/linktest --link 2>&1 | grep quality.md
# expect: "⤷ quality.md is a real file here — project override, left alone"
cat /tmp/linktest/.claude/rules/quality.md   # still the override

ln -s /nonexistent /tmp/linktest/.claude/rules/ghost.md
./apply.sh --project-dir /tmp/linktest --link 2>&1 | grep ghost
# expect: "⤷ removing stale link ghost.md"
```

- [x] **Step 7: Run the gate, then commit**

```bash
scripts/check_fork.sh 2>&1 | grep 'apply.sh'   # expect PASS
git add apply.sh templates/
git commit -m "feat(apply): link mode replaces the copy path (D8, D9)

Per-item relative symlinks into this checkout. A real file at a link
destination is a project override and is preserved. Dead links are pruned.
Writes .claude/pipeline.lock for coauthor bootstrap and replication provenance.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

### Task 15: `bootstrap-pipeline.sh` and the `/promote` skill

**Files:**
- Create: `templates/bootstrap-pipeline.sh`
- Create: `skills/promote/SKILL.md`
- Create: `rules/shared-pipeline.md`

- [x] **Step 1: Write the bootstrap script**

`templates/bootstrap-pipeline.sh` — installed to each paper repo root and committed there:

```bash
#!/usr/bin/env bash
# bootstrap-pipeline.sh — materialize this project's Claude pipeline.
#
#   ./bootstrap-pipeline.sh          coauthor / archival: pinned commit, project-local checkout
#   ./bootstrap-pipeline.sh --tip    maintainer: shared checkout on main, edits flow everywhere
#
# The two modes deliberately use different checkouts. Pinning the SHARED
# checkout would silently pin every other project on this machine to this
# paper's locked commit.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK="$PROJECT_DIR/.claude/pipeline.lock"
[[ -f "$LOCK" ]] || { echo "missing $LOCK"; exit 1; }

repo="$(sed -n 's/^repo=//p'   "$LOCK")"
commit="$(sed -n 's/^commit=//p' "$LOCK")"
TIP=false; [[ "${1:-}" == "--tip" ]] && TIP=true

if [[ "$TIP" == true ]]; then
  RC="${RESEARCH_CLAUDE_HOME:-$HOME/Academic/research-claude}"
else
  RC="$PROJECT_DIR/.pipeline/research-claude"
fi

if [[ ! -d "$RC/.git" ]]; then
  echo "→ cloning $repo → $RC"
  git clone --recurse-submodules "$repo" "$RC"
fi
git -C "$RC" fetch --quiet origin

if [[ "$TIP" == true ]]; then
  if ! git -C "$RC" symbolic-ref -q HEAD >/dev/null; then
    echo "⚠️  $RC is in detached HEAD — returning it to main"
  fi
  git -C "$RC" checkout --quiet main
  git -C "$RC" pull --quiet --ff-only
  echo "→ pipeline: $RC @ main ($(git -C "$RC" rev-parse --short HEAD))"
else
  echo "→ pipeline: pinned $commit (project-local)"
  git -C "$RC" checkout --quiet "$commit"
fi
git -C "$RC" submodule update --init --recursive --quiet

exec "$RC/apply.sh" --project-dir "$PROJECT_DIR" --link
```

- [x] **Step 2: Test it end to end from a clean clone**

```bash
rm -rf /tmp/bstest && git clone --quiet https://github.com/EconGeo/POGM4.git /tmp/bstest 2>/dev/null || \
  { rm -rf /tmp/bstest && cp -R ~/Research/POGM4 /tmp/bstest; }
cd /tmp/bstest && ./bootstrap-pipeline.sh
ls -l .claude/skills | head -3          # symlinks into /tmp/bstest/.pipeline/research-claude
git -C .pipeline/research-claude rev-parse HEAD   # matches pipeline.lock
```

This step only becomes runnable after Task 17 commits the bootstrap script into POGM4; run it then and check the box.

- [x] **Step 3: Write `rules/shared-pipeline.md`**

The one behavioral hazard symlinks introduce: an agent editing `.claude/skills/write/SKILL.md` from a paper session is editing every paper at once, and the change lands as an uncommitted diff in a repo the session is not in.

```markdown
# Shared Pipeline — what a symlinked .claude/ means

`.claude/{skills,agents,rules,hooks}` are symlinks into a checkout of
`EconGeo/research-claude`. They are not this project's files.

**Editing one changes every paper immediately.** The edit lands as an
uncommitted change in the research-claude working copy, which no session is
"in". It will not appear in this project's `git status`.

- Improving the pipeline: edit through the link, then run `/promote` to review
  and commit it upstream. That is the intended path — it is how a fix stops
  being stranded in one paper.
- Needing something only this paper wants: `rm` the symlink and write a real
  file in its place. `apply.sh --link` treats a real file as a deliberate
  override and will never overwrite it.
- Never: copy the whole tree back into the project to "make it local". That is
  the drift this design exists to end.
```

- [x] **Step 4: Write the `/promote` skill (D7)**

Under symlinks, `/promote`'s job shrinks — there are no forks to reconcile, because there is nothing to fork. What remains is real: surfacing edits made through links so they get committed rather than sitting uncommitted, and finding project overrides that have outgrown being local.

`skills/promote/SKILL.md`:

```yaml
---
name: promote
description: Review pipeline changes made from a project session and land them upstream in research-claude. Use after improving a shared skill, agent, or rule from inside a paper project, or when a project override looks like it should be shared. Reports uncommitted edits to the linked tree and real files shadowing a canonical item.
---
```

Body:

1. **Resolve the checkout** — `readlink .claude/skills/write` → the research-claude path.
2. **Uncommitted upstream edits:** `git -C "$RC" status --porcelain -- agents skills rules references hooks templates`. Each entry is an improvement made from some paper session that has not been committed. Show the diff, ask whether to keep, and commit with a message naming the originating project.
3. **Project overrides:** every non-symlink in `.claude/{skills,agents,rules}` whose name also exists in the canonical tree. For each, diff against canonical and ask: genuinely local (leave it, note why), or generally useful (upstream it, then replace with a link)?
4. **De-projectification check before any upstream commit** — run the D5 grep from `check_fork.sh`; refuse to commit a file naming a project, journal, or dataset.
5. **Refresh the lock** — offer to re-run `apply.sh --link` so `.claude/pipeline.lock` records the new SHA.

- [x] **Step 5: Commit**

```bash
git add templates/bootstrap-pipeline.sh skills/promote/ rules/shared-pipeline.md
git commit -m "feat: bootstrap-pipeline.sh, /promote skill, shared-pipeline rule (D7, D10)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

### Task 16: Remove the clo-author submodule and update the README

**Files:**
- Delete: `submodules/clo-author/`
- Modify: `.gitmodules`, `README.md`, `CLAUDE.md`

- [x] **Step 1: Remove the submodule (criteria 1 and 2)**

Do this only after Tasks 2–13 have vendored everything out of it.

```bash
cd ~/Academic/research-claude
git submodule deinit -f submodules/clo-author
git rm -f submodules/clo-author
rm -rf .git/modules/submodules/clo-author
grep -A2 'clo-author' .gitmodules || echo ".gitmodules clean"
```

- [x] **Step 2: Rewrite the README's architecture section**

The 39 KB README describes a three-source composition that no longer exists. Replace with: research-claude is standalone and authoritative; `ai-audit` and `journal-digest` remain live submodules; `zotpilot-skills/` stays vendored; installation is `apply.sh --link`; new projects and coauthors use `bootstrap-pipeline.sh`. Add a short "How to change the pipeline" section pointing at `rules/shared-pipeline.md` and `/promote`. Credit clo-author for the origin of the vendored agents.

- [x] **Step 3: The gate must now pass completely**

```bash
scripts/check_fork.sh; echo "exit=$?"
```

Expected: `exit=0` and `✓ check_fork: PASS`. This is the first point at which the whole fork is green. If any line still fails, fix it here — do not proceed to Phase 5 with a red gate.

- [x] **Step 4: Commit and merge the branch**

```bash
git add -A
git commit -m "feat: remove the clo-author submodule; research-claude is standalone

Pinned at 2026-05-10 and one-way for four months. Everything worth keeping is
vendored into agents/, skills/, rules/, references/, hooks/.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
git checkout main && git merge --no-ff design/quarto-native-pipeline
git push origin main
```

---

## Phase 5 — Rollout (D6, D11)

### Task 17: Prove it on a scratch copy of POGM4 (D6)

Nothing under `~/Research` is touched until this passes.

- [x] **Step 1: Copy POGM4 to scratch and convert it**

```bash
rm -rf /tmp/pogm4-scratch && cp -R ~/Research/POGM4 /tmp/pogm4-scratch
cd /tmp/pogm4-scratch
rm -rf .claude/skills .claude/agents .claude/rules .claude/hooks
~/Academic/research-claude/apply.sh --project-dir /tmp/pogm4-scratch --link --tip
```

- [x] **Step 2: Restore POGM4's genuinely local skill**

`flextable-quarto-word-captions` is project-specific (spec §Phase 3) and must survive as a real file beside the links.

```bash
cp -R ~/Research/POGM4/.claude/skills/flextable-quarto-word-captions \
      /tmp/pogm4-scratch/.claude/skills/
ls -l /tmp/pogm4-scratch/.claude/skills/flextable-quarto-word-captions  # a directory, not a link
```

- [x] **Step 3: Spec criterion 4 — the manuscript still renders**

```bash
cd /tmp/pogm4-scratch && quarto render manuscript_quarto_word.qmd; echo "exit=$?"
```

Expected: `exit=0`. (The scratch copy keeps POGM4's current filename; the `manuscript_<project>.qmd` naming rule governs what the template *ships*, not what an existing paper is called.)

- [x] **Step 4: Spec criterion 5 — the prose-number gate still passes**

```bash
python3 ~/Research/scripts/prose_number_check.py /tmp/pogm4-scratch; echo "exit=$?"
```

Expected: `exit=0`.

- [x] **Step 5: Confirm the links actually load in a session**

Start a Claude Code session in `/tmp/pogm4-scratch` and confirm:
(a) a linked skill is invocable — `/write` resolves, not `Unknown skill`;
(b) the project's own `CLAUDE.md` still loads;
(c) `.claude/references/*.md` still resolve to `~/Research/.claude/references/`.

This is the one check no script can make. The consolidation doc's §1 established that a symlinked directory inside `PROJECT/.claude/skills/` *is* discovered as a project skill — this confirms it holds for per-item links too, which is the thing D9 changed.

- [x] **Step 6: Record the result**

Append to `~/Academic/research-claude/docs/SESSION_REPORT.md`: the four exit codes and the session-load result. If any failed, stop — the fork is not ready and no real project gets converted.

### Task 18: Convert the six paper repos, one branch each (D11)

Order: **POGM4 → NAR_settlement → zoning2026 → ESG → affordable_housing_2026 → BRI.** Skip `NAR_settlement_legacy_archive` (frozen).

POGM4 first because its `review`/`submit` forks were resolved upstream in Task 7 and it is the most-diverged. NAR_settlement second because it is at baseline on every agent, so a clean result there confirms the canonical tree is complete rather than accidentally POGM4-shaped.

Repeat for each project. **Do not start the next one until the current one is verified and merged.**

- [x] **Step 1: Branch and back up**

```bash
cd ~/Research/<project>
git checkout -b pipeline-symlink
cp -R .claude ".claude.bak.$(date +%Y%m%d)"     # the rollback; taken before anything is removed
echo ".claude.bak.*" >> .gitignore
```

- [x] **Step 2: Note the project's real-file overrides before removing anything**

```bash
diff -rq .claude/skills ~/Academic/research-claude/skills 2>/dev/null | grep 'Only in .claude'
diff -rq .claude/rules  ~/Academic/research-claude/rules  2>/dev/null | grep 'Only in .claude'
```

Anything listed is either (a) genuinely local — restore it as a real file in Step 4, or (b) an unharvested improvement — stop, upstream it via `/promote` first, then continue. Do not discard it.

- [x] **Step 3: Link**

```bash
rm -rf .claude/skills .claude/agents .claude/rules .claude/hooks
~/Academic/research-claude/apply.sh --project-dir "$PWD" --link --tip
cp ~/Academic/research-claude/templates/bootstrap-pipeline.sh . && chmod +x bootstrap-pipeline.sh
```

- [x] **Step 4: Restore genuinely local items as real files**

From the Step 2 list. For POGM4 that is `flextable-quarto-word-captions` and, if it is still wanted, `commit`. Confirm each is a directory or regular file, not a link.

- [x] **Step 5: Gitignore the linked dirs, commit the pointer (D10)**

```bash
cat >> .gitignore <<'EOF'

# Pipeline: linked from research-claude, not project content.
# Run ./bootstrap-pipeline.sh to materialize.
.claude/skills/
.claude/agents/
.claude/rules/
.claude/hooks/
/.pipeline/
EOF
git rm -r --cached .claude/skills .claude/agents .claude/rules 2>/dev/null || true
git add .gitignore bootstrap-pipeline.sh .claude/pipeline.lock
```

- [x] **Step 6: Verify before merging — all four must pass**

```bash
quarto render manuscript_*.qmd; echo "render=$?"
python3 ~/Research/scripts/prose_number_check.py "$PWD"; echo "prose=$?"
find .claude -maxdepth 2 -type l ! -exec test -e {} \; -print   # expect no output
```

Then start a session in the project and confirm a linked skill is invocable and `CLAUDE.md` loads.

- [x] **Step 7: Merge, or roll back**

```bash
git commit -m "chore: link pipeline from research-claude instead of copying

.claude/{skills,agents,rules,hooks} are now per-item symlinks into
EconGeo/research-claude. Project-specific overrides remain real files.
Coauthors: ./bootstrap-pipeline.sh

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
git checkout main && git merge --no-ff pipeline-symlink && git push
```

Rollback, if any check fails:

```bash
rm -rf .claude/skills .claude/agents .claude/rules .claude/hooks
cp -R .claude.bak.*/skills .claude.bak.*/agents .claude.bak.*/rules .claude/
git checkout main && git branch -D pipeline-symlink
```

- [x] **Step 8: After all six — delete the backups and record the outcome**

Keep the `.claude.bak.*` directories until every project has been converted and used in at least one real session. Then remove them and append a summary to `~/Academic/research-claude/docs/SESSION_REPORT.md`: which projects converted, what stayed local in each, and any improvement upstreamed during Step 2.

---

## Verification

**The gate, at every task:** `~/Academic/research-claude/scripts/check_fork.sh` — exit 0 means spec criteria 1, 3, 6, 7, 8 and the D1 deletions all hold. It fails on purpose at Task 1 and must be green by the end of Task 16.

**Spec criteria 4 and 5** are the scratch-POGM4 test in Task 17: `quarto render` exits 0 and `prose_number_check.py` exits 0 against a copy of a real paper.

**Criterion 9** (every B-list port has a landing place) is satisfied by C2 — six of eight ride along inside vendored skill directories; confirm with:

```bash
cd ~/Academic/research-claude
ls skills/strategize/templates/design-checklists/     # 6 files
ls skills/strategize/templates/pap-templates/         # 3 files
ls skills/{submit/templates/audit-10-checks.md,talk/templates/narrative-arcs.md}
ls skills/write/{references/notation-protocol.md,templates/drafting-gates.md}
ls skills/strategize/templates/{decision-record.md,robustness-plan.md}
```

**The link mechanism** is verified three ways, because a script cannot check the third:
1. Links resolve — `find .claude -type l ! -exec test -e {} \; -print` returns nothing.
2. Overrides survive and dead links are pruned — Task 14 Step 6.
3. Claude Code actually discovers a per-item symlinked skill — Task 17 Step 5, by hand, in a session.

> **AMENDED.** These three check that the links present are *good*. None checks that
> the links that should exist *are* present — a link cannot point at a file that did
> not exist when it was made, so an item added upstream reaches nobody until the
> linker re-runs. Membership is check 4, and it is scriptable after all:
> `scripts/check_install.sh` (also: no committed symlinks, no foreign checkout, no
> override a clone would miss, lock-vs-HEAD drift). Run it after any change that adds
> or removes a file under `agents/`, `skills/`, `rules/` or `hooks/`.

**End-to-end, after rollout:** edit a shared rule from within one paper, confirm the change is visible from a second paper without any re-apply, confirm `git -C ~/Academic/research-claude status` shows it as an uncommitted change, and confirm `/promote` surfaces it. That single test exercises the whole point of the design.

---

## What could go wrong

| Risk | Handling |
|---|---|
| An unharvested improvement is deleted during conversion | Task 18 Step 2 diffs before removing anything, and the `.claude.bak.*` copy is taken first. Backups survive until every project has run a real session. |
| Editing a linked file silently changes six papers | That is the design, but it needs to be visible: `rules/shared-pipeline.md` states it, and `/promote` surfaces the uncommitted diff. |
| A coauthor clones and gets a broken session | The linked dirs are gitignored, so there is nothing to dangle. `./bootstrap-pipeline.sh` is one command against a public repo, no access grant needed. |
| Pinned bootstrap detaches the shared checkout and freezes every project | Structurally prevented: pinned mode uses a project-local checkout, `--tip` uses the shared one. They never share. |
| Vendoring loses something clo-author had | The submodule is not removed until Task 16, after everything is vendored. Until then it is still on disk to diff against, and it stays in git history afterward. |
| The rewritten standards files introduce new wrong instructions | `rules/quarto-word.md` and `rules/quarto-pdf.md` are already correct and are the authority; Task 12 references them rather than restating them. |
| Hooks fire unexpectedly across six repos | C4 — hooks are linked but never auto-wired; `settings.json` stays project-owned and unlinked. |
