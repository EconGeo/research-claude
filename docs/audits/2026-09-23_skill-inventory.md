# Skill inventory audit — duplication, conflicts, clo-author parity

**Date:** 2026-09-23
**Scope:** all 26 shipped skills (18 `skills/`, 2 `ai-audit/skills/`, 6 `zotpilot-skills/`), 18 agents,
18 rule files, `README.md`, `CLAUDE.md`.
**Status:** read-only. Nothing was edited.

**Method.** Read in full to EOF: every `skills/*/SKILL.md`, `ai-audit/skills/*/SKILL.md`,
`zotpilot-skills/seed-papers/SKILL.md`, `rules/registry.yaml`, `rules/shared-pipeline.md`,
`rules/meta-governance.md`, `rules/agents.md`, `rules/quality.md`, `rules/lifecycle.md`,
`rules/literature-search-order.md`, `README.md`, `CLAUDE.md`, `agents/verifier.md`,
`agents/writer-critic.md`, `agents/lit-critic.md`,
`docs/superpowers/specs/2026-09-08-quarto-native-research-pipeline-design.md`,
`docs/checkpoints/2026-09-08_quarto-native-pipeline-fork.md`,
`docs/audits/2026-09-15_skill-best-practices-audit.md`,
`skills/submit/templates/audit-10-checks.md`, `skills/talk/templates/format-constraints.md`.
Targeted full-section reads elsewhere are cited inline. Greps were used only to locate.

---

## 0. Two corrections to the audit request, made before anything downstream

**0.1 — The "folded into the canonical multi-skills" quotation is real, but it is not from
`/tools learn` and not from this repo.** It is from **POGM4 commit `5f11c52`** ("Align agents and
skills to research-claude canonical set"), verified this session:

> Skills: 58 -> 18 (research-claude canonical + commit + flextable-quarto-word-captions …).
> Removed course/teaching skills and standalone duplicates **now folded into the canonical
> multi-skills (tools, discover, review)**.

So the claim is a **project's** assertion about the pipeline, made in a paper repo's git history —
exactly the kind of claim worth testing against the successor skills, which §2.2 does. Two things
follow that the attribution obscured.

First, `skills/tools/SKILL.md` makes no such claim. Read in full, its `learn` subcommand says only:

> ### `/tools learn` — Extract Learnings
> Extract a reusable multi-step workflow from the current session and propose it as a skill.
>
> A **correction** to a pipeline skill, agent or rule is not handled here and is never applied
> silently. It follows `.claude/rules/meta-governance.md` …

The folding claims that *do* exist **in this repo** are the seven `Replaces the old …` clauses in
the multi-skills' `description:` frontmatter. Those are what §2.2 verifies.

Second — and this is a finding, not a technicality — **`5f11c52`'s own closing line admits the
consumer-side cleanup was deferred and it was never done:**

> CLAUDE.md skill table still references removed skills and will be reconciled in the CLAUDE.md
> refresh during the data-chain upgrade.

POGM4's `CLAUDE.md` "Skills Quick Reference" today still lists `/review-paper`,
`/respond-to-referees`, `/review-r`, `/data-analysis`, `/audit-reproducibility`, `/validate-bib`,
`/lit-review`, `/research-ideation`, `/interview-me`, `/seven-pass-review`, `/proofread`,
`/permission-check`, `/commit` and `/context-status` — most of them the very standalone skills
that commit deleted, promised for reconciliation in June 2026. The fold was done correctly in the
pipeline (§2.2); **the project-side table documenting it was not**, and a reader of POGM4's
`CLAUDE.md` is still told to invoke skills that have not existed for three months. This is
project-level residue rather than pipeline residue, so it is not in the prioritized list, but it
is the same defect class and worth a single reconciliation pass.

**0.2 — There is no clo-author checkout to read.** The request pointed at
`submodules/`, `docs/`, or a sibling checkout. `CLAUDE.md` (read in full) states:

> **There is no `submodules/` directory and no `.gitmodules`.** The git submodule mechanism was
> removed entirely on 2026-09-09 … `clo-author` was de-submoduled on 2026-09-08 (its agents are
> vendored into `agents/` and maintained here)

`find` over the filesystem confirms no `clo-author` directory anywhere, and `git remote -v` shows
one remote (`EconGeo/research-claude`). **The parity table in §3 is therefore built against the
contemporaneous inventory recorded in
`docs/superpowers/specs/2026-09-08-quarto-native-research-pipeline-design.md` (read in full)**,
which measured all 47 clo-author agent/rule/skill files and enumerates them in Work items A, B, C
and D. That spec is a record *of* clo-author, not clo-author itself, and §3 stays labelled
accordingly.

**Superseded in part, after the scope extension.** clo-author is a public repo. It was cloned from
`https://github.com/hugosantanna/clo-author.git` and checked out at **`d36c408`** — the exact
commit this repo's submodule was pinned to, recovered via
`git ls-tree bda2d1b submodules/clo-author`. clo-author's own rules, skill headers and settings
were then read directly. **That reading is the basis of the divergence register**
(`docs/decisions/clo-author-divergences.md`), and it confirmed the spec's inventory on every point
§3 relies on while adding intent the spec did not record. §3 is unchanged; nothing it claimed
turned out to be wrong.

---

## 1. Duplication and conflict

### 1.1 REAL CONFLICT — `/write humanize` vs `/humanize`: contradictory instructions, same task

Two skills own "strip AI voice", and they give opposite orders about whether to edit the file.

`skills/write/SKILL.md:102-108`:

> ### `/write humanize [file]` — Cleanup Pass Only
> Strip AI writing patterns from existing text without rewriting content.
>
> **Agent:** Writer (cleanup mode)
> **Output:** Edited file with AI patterns removed

`ai-audit/skills/humanize/SKILL.md` (frontmatter and "What this skill is NOT"):

> Produces a report; does **NOT** rewrite.
>
> - **Not a rewriter.** No `--rewrite` mode. Auto-rewriting AI tells degrades prose quality
>   (cross-vendor research finding); the author preserves voice by editing manually.

and its closing "Anti-pattern" section:

> We deliberately do not ship `/humanize --rewrite`. Cross-vendor research … finds that
> auto-rewriting prose to strip AI tells degrades quality more often than it improves it — the
> rewriter introduces its *own* AI tells.

This is not adjacency. `/humanize`'s refusal to rewrite is stated as a **design principle with a
cited rationale**, and `/write humanize` does exactly the thing the principle forbids, on the same
file types, under a name one word apart.

The detection sets overlap heavily too. `skills/write/templates/cleanup-patterns.md` lists 24
patterns in 4 categories; `ai-audit/skills/humanize/SKILL.md` lists 10 categories. Both cover AI
vocabulary (`delve`, `tapestry`, `leverage`, `nuanced`), em-dash overuse, rule-of-three / tricolon
abuse, stacked hedging, "not only X but also Y", filler phrases ("It is important to note that"),
and promotional/sycophantic framing. `cleanup-patterns.md:13` — "**Em dash overuse** -- more than
2 em dashes per page signals AI drafting" — versus `humanize` category 3 — "more than 3 em-dashes
per paragraph is a tell" — are two different thresholds for the same defect.

A **third** copy exists: `agents/writer-critic.md` describes itself as "the copy editor who checks
Quarto format, notation and **AI writing tells**", and `manuscript-review-8-categories.md:189`
scores `## Writing Quality: [CLEAN/AI PATTERNS FOUND/NEEDS REWRITE]`.

Noted as "Low" in the 2026-09-15 audit §4 ("`/write humanize` rewrites in place while `/humanize`
is detect-only by design"). It is still open, and I rate it higher: it is the only place in the
tree where two shipped skills instruct opposite actions on the same input.

### 1.2 ADJOIN, correctly bounded — `/review` vs `/verify-claims`

No conflict. `/verify-claims` declares its own boundary in frontmatter:

> NOT for style/grammar review or substance review — use the host pipeline's own reviews for those
> (in research-claude, `/review --proofread` and `/review`).

and the two check different things. `agents/verifier.md` check 3 is *key resolution* —

> **References resolve.** No `?@fig-`, `?@tbl-`, `?@sec-`, `?@eq-` in the output; every `@key`
> exists in `references.bib`

— i.e. the BibTeX key is present. `/verify-claims` Phase 4 checks *existence in the world*:

> **HIGH-WARN** — fabricated reference (the cited paper doesn't exist at the named venue/year) …

These are complementary. **But see §2.4: nothing in the pipeline ever calls `/verify-claims`.**

### 1.3 ADJOIN — `/analyze` vs `/strategize`

Clean separation, declared on both sides. `/strategize` produces `strategy_memo.md` +
`pseudo_code.md` ("Pseudo-code: implementation sketch"); `/analyze` Step 1 consumes it ("strategy
memo path, paper type, naming map") and writes chunks. `registry.yaml` enforces the ordering —
`coder.requires` is `score: strategy, min: 80`. `rules/agents.md` §2 keeps the strategist out of
code ("A critic that writes code … has failed its role"; `strategist` tools are `Read, Write,
Grep, Glob` only — no Edit/Bash). No overlap in trigger either: `/strategize` is design,
`/analyze` is execution.

### 1.4 ADJOIN, but with one broken cross-reference — `/tools` vs standalone equivalents

There are **no** standalone `commit`, `render`, `validate-bib`, `lint`, `journal`, `context` or
`learn` skills in the tree, and a grep for bare-slash references to them across
`agents skills rules references hooks templates seeds README.md CLAUDE.md` returns nothing but
`hooks/post-edit-lint.sh:39` calling `lint-scripts.sh` directly (a script, not a skill). The fold
is real.

Two frictions rather than conflicts:
- `/tools lint` and `/review --code` Step 1 both run `.claude/hooks/lint-scripts.sh`. That is
  deliberate and documented (`/review`: "Include the lint report in the coder-critic's input").
- `/tools render` hardcodes the filename — `quarto render manuscript_<project>.qmd` — where every
  other skill resolves it (`python3 .claude/scripts/pipeline.py manuscript`). Flagged 2026-09-15;
  still open. A project whose `CLAUDE.md` declares a different `manuscript:` gets the wrong command.

### 1.5 ADJOIN, with a stale description — `/discover` vs `/lit-position` vs `/seed-papers`

The three are sequenced, not competing, and the sequence is stated in three places consistently:
`new-project-ztp` Step 5 ("Optionally run `/seed-papers [topic]` first"), `seed-papers` Step 8
("Run the literature review next (`/lit-position [topic]` …)"), `lit-position` Step 0 ("If
`quality_reports/literature/<project>/zotero_seed.md` exists, `/seed-papers` was run"). Neither
duplicates the other's output: `seed-papers` writes the *confirmed anchor set*, `lit-position`
writes `frontier_map.md` and `positioning.md`, which its own preamble says "ZotPilot produces
nothing like this."

The conflict is in `/discover`'s frontmatter versus its body. Frontmatter:

> description: Discovery phase combining research interviews, **a pointer to /lit-position for
> literature**, data discovery, and ideation. … **Replaces the old interview-me, lit-review,
> find-data and research-ideation commands.**

Body:

> ### `/discover lit` — superseded
> Literature search and positioning are `/lit-position` (optionally after `/seed-papers`). Run that
> instead; **this skill no longer has a `lit` mode.**

The description simultaneously claims to *replace* `lit-review` and to *be a pointer*, while the
body says the mode does not exist. `argument-hint` still advertises it: `"[mode: interview | lit |
data | ideate] …"`. A user typing `/discover lit` gets a redirect, not a failure — so this is
stale copy, not a trap — but the description is the string the model selects on (see §5.2).

### 1.6 ADJOIN — the three ZotPilot layers

`ztp-research` (find + ingest) → `ztp-review` (synthesize) → `lit-position` (frontier +
positioning). `lit-position` states the boundary explicitly:

> **The vendored ZotPilot skills … are never edited.** This skill calls those skills; it does not
> modify them.

and `## What this skill does NOT do` disclaims writing the lit-review section (→ `/write`) and
proposing a strategy (→ `/strategize`). Well-bounded.

### 1.7 REAL CONFLICT — `agents/data-engineer.md` tells the agent to use a package its own critic deducts for

`agents/data-engineer.md:92`, in "Preferred R Packages", unqualified by output format:

> | Tables | `gt`, `kableExtra`, `modelsummary` |

`flextable` is absent from the list. `rules/quarto-word.md:49` and `:169`:

> `kableExtra` emits LaTeX and produces garbage in Word — use **flextable** for the …
>
> - `kableExtra` loaded or used for Word tables (-5)

The data-engineer writes the `tbl-summary` chunk (`/analyze` Step 2: "`build-*` chunks with
`cache.extra`, manifest rows, `tbl-summary` chunk"), so this is a live instruction, not dead prose.
`skills/analyze/templates/chunk-structure.md:71` gets it right — `output = "kableExtra", # PDF;
Word uses output = "flextable" (quarto-word.md)` — which makes the agent file the outlier.

### 1.8 REAL CONFLICT — two `/analyze` bundled resources contradict each other

Both are named in `/analyze`'s own resources table, so both reach the same agent.

`skills/analyze/templates/paper-to-code-map.md:36`:

> 4. **Match is exact.** If the paper calls it $D_{it}$, the code variable is `treatment` (or
>    `treat` — pick one and stick with it). **Never `treated`**, `Treatment`, `is_treated` …

`skills/analyze/templates/chunk-structure.md:19, 54-55`:

> `#   D_it     -> treated        (constructed in build-panel)`
> `m_main <- feols(log_permits ~ treated | unit + year, data = panel, cluster = ~unit)`
> `beta_hat <- coef(m_main)[["treated"]]; se_hat <- se(m_main)[["treated"]]`

The naming template forbids exactly the name the chunk template demonstrates three times.

Same skill, second instance: `agents/data-engineer.md:40` — "**Font:** Sentence-case labels,
`base_size >= 14` for readability" — against `skills/analyze/references/figure-standards.md:41` —
`theme_paper <- theme_minimal(base_family = "serif", base_size = 11)`. `/analyze` Step 2 dispatches
data-engineer and points it at `figure-standards.md`; the two numbers cannot both hold.

Both were reported 2026-09-15 (§3, P3 table, `analyze` row) and both are unfixed.

### 1.9 REAL CONFLICT — `/talk` SKILL.md vs `format-constraints.md`: every row disagrees

`skills/talk/SKILL.md` "Format Constraints":

| Format | Slides | Duration |
|---|---|---|
| job-market | 40-50 | 45-60 min |
| seminar | 25-35 | 30-45 min |
| short | 10-15 | 15 min |
| lightning | 3-5 | 5 min |

`skills/talk/templates/format-constraints.md`:

| Format | Duration | Slides |
|---|---|---|
| Job Market | 45-50 min | 35-45 |
| Seminar | 60-75 min | 40-55 |
| Short | 15-20 min | 12-18 |
| Lightning | 5-7 min | 5-8 |

Not one row matches. A lightning talk is 3-5 slides in the skill and 5-8 in the template; a seminar
is 30-45 minutes in one and 60-75 in the other. `/talk` says the Storyteller reads the template
("The Storyteller agent reads these resources before building slides … the format constraints
determine scope") while the skill's own Step 3 scores "Scope for format" against the inline table.

Two further drifts in the same file: the skill lists **5** critic categories where
`skills/review/templates/talk-review-6-categories.md` has 6; and the skill's visual check says
"font readability (>= 10pt)" where `skills/talk/references/slide-design-principles.md:15-17` says
"Title: >=24pt / Body: >=18pt / Footnotes/sources: >=12pt" — the skill's floor is below the
reference's floor for every element.

Reported 2026-09-15; unfixed.

### 1.10 REAL CONFLICT — `editor.md` delegates enforcement to a `/review` flag that `/review` does not have

`agents/editor.md:124`:

> `--variance` cannot combine with `--stress` … or `--r2`/`--r3` … **The `/review --peer` skill
> enforces this** — if you receive a Phase 1b call with both flags set, halt and report the
> conflict.

`skills/review/SKILL.md` was read in full. Its flag list is `--peer`, `--peer --r2`, `--stress`,
`--methods`, `--theory`, `--proofread`, `--code`, `--replicate`, `--all`. **`--variance` does not
appear anywhere in it.** The editor names an enforcement point that does not exist; the mode is
reachable only by a user who has read `editor.md`.

---

## 2. Retired-skill residue

### 2.1 Dangling reference — `/review-paper` in the README

`README.md:563`, in the "Using the research pipeline" table:

> | `/review-paper` | Manuscript review (single-pass, adversarial, or simulated peer review) |

No `review-paper` skill exists in `skills/`, `ai-audit/skills/` or `zotpilot-skills/`. It is one of
the five names `/review`'s own description says it replaced. This is the only dangling **skill**
reference in the tree — the retirement sweep was otherwise thorough (see 2.5).

The same README table also omits `/review`, `/revise`, `/talk`, `/submit`, `/discover`,
`/checkpoint`, `/tools`, `/promote`, `/careful`, `/freeze`, `/ztp-profile`, `/ztp-tutor`,
`/ztp-ollama` and `/new-project-ztp` — 14 of the 26 shipped skills are absent from the table a new
user reads.

### 2.2 The `Replaces the old …` claims, verified one by one

| Skill | Claim | Verdict |
|---|---|---|
| `/review` | paper-excellence, proofread, econometrics-check, review-r, review-paper | **Present** — `--all`, `--proofread`, `--methods`, `--code`, default/`--peer`. All five have routing entries and mode sections except `--all`, which is in routing only. |
| `/discover` | interview-me, lit-review, find-data, research-ideation | **Partial** — `interview`, `data`, `ideate` present. `lit` **removed, not folded**: "this skill no longer has a `lit` mode." Function lives in `/lit-position`. Description is stale (§1.5). |
| `/strategize` | identify, pre-analysis-plan | **Present** — `strategy` and `pap` (+ `pap interactive`), each with its own critic dispatch and `record-score`. |
| `/write` | draft-paper, humanizer | **Present but conflicting** — `humanize` mode exists and does the opposite of the surviving `/humanize` skill (§1.1). |
| `/revise` | respond-to-referee | **Present** — 8-step workflow with the FATAL/ADDRESSABLE/TASTE classification the spec's B-list asked for. |
| `/submit` | target-journal, audit-replication, **data-deposit** | **Partial — `data-deposit` is missing.** `target`, `package` and `audit` are present. Nothing in `skills/submit/`, `agents/verifier.md`, `submission-checklist.md` or `replication-readme.md` mentions openICPSR, Dataverse, Zenodo or any deposit step; a grep for `deposit` across `agents skills rules references README.md` returns only journal-policy prose in `references/discipline-cards.md` and `journal-profiles.md` (e.g. "AJPS Replication Policy requires deposit before acceptance"). `/submit package` **assembles** a package under `replication/`; nothing **deposits** it. The pipeline knows the requirement exists and has no step that satisfies it. |
| `/tools` | "individual utility skills" | **Present** — no standalone equivalents survive (§1.4). |

### 2.3 Orphans — skills nothing references

- **`/ztp-profile`** and **`/ztp-tutor`** — installed into every project (`apply.sh --link`
  creates the symlinks; confirmed present in `~/Research/POGM4/.claude/skills/`) and referenced
  from **nowhere** in `agents/`, `skills/`, `rules/`, `references/`, `hooks/`, `README.md` or
  `CLAUDE.md`. `/ztp-tutor` is the largest SKILL.md in the repo at 431 lines.
- **`/ztp-ollama`** — 141 lines, referenced exactly once, and only as an example of the
  bridge-skill pattern (`CLAUDE.md:75`: "Changes go into a bridge skill under `skills/` (see
  `lit-position`, `new-project-ztp`, `ztp-data-tag`, `ztp-ollama`)"). Never named in the README's
  ZotPilot setup section, which is the one place a user configuring Ollama would look — that
  section instead gives raw `zotpilot config set` commands.
- **`/careful`** and **`/freeze`** — referenced only by each other, their own gotchas, and
  `hooks/session-guard.py`. Not in the README skills table. Acceptable for session utilities.

### 2.4 Structural orphan — `ai-audit` is installed but never invoked

`/humanize` and `/verify-claims` are referenced **only** in `README.md` (lines 28, 160, 189, 194,
542, 564, 565, 752). Zero references from `agents/`, `skills/`, `rules/`, `hooks/`, `templates/`,
`zotpilot-skills/`. `rules/registry.yaml` was read in full and contains no entry for
`claim-verifier` or `humanize-auditor`, no component they score, and no weight.

Consequences, in order of severity:

1. **`/submit final` can pass at ≥ 95 with no hallucination check ever run.** Its workflow is
   review → replication audit → AI-disclosure audit → score gate → coverage check. Citation
   *existence in the world* is checked by nothing in that chain (`verifier` check 3 only confirms
   the key is in `references.bib` — §1.2).
2. `/pipeline`'s stage list (`setup → literature → data → strategy → theory → analyze → write →
   review → submit`, `talk` parallel) has no slot for either.
3. `skills/promote/SKILL.md` Step 2's pathspec is
   `-- agents skills rules references hooks templates seeds scripts` — it does **not** include
   `ai-audit` or `zotpilot-skills`, and the sync scripts `rm -rf` those trees. An improvement made
   to `/humanize` through a project symlink is silently destroyed on the next sync. `/promote` says
   so for one tree only: "Does not edit anything under `zotpilot-skills/`, which is vendored
   verbatim" — `ai-audit/` gets no equivalent warning anywhere in the skill.

### 2.5 Retirements that are clean — no action

Verified by reading every hit in full context: `orchestrator`, `guide-writer`, `librarian`,
`librarian-critic`, `root-skills/`, `new-project`, `pipeline-precedence.md`,
`working-paper-format.md`, `obsidian-digest-sync`, `journal-digest`. Every surviving mention is an
explicit historical note in `CLAUDE.md`, `README.md` or `rules/ai-disclosure.md`, several carrying
an intentional `<!-- residue:historical -->` marker for `check_fork.sh`. No skill, agent or rule
dispatches or reads any of them.

`rules/registry-verification-gate.md` (deleted today, `83205d7`) leaves **zero** dangling
references — grep across `agents skills rules references hooks README.md CLAUDE.md scripts tests`
returns nothing. Clean deletion.

### 2.6 Stale counts in the README's opening sentence

> A Quarto-native, multi-agent research pipeline for empirical academic work — **17 agents, 17
> skills and 19 rules** …

Actual: **18** agents (`ls agents/*.md`), **26** skills (18 + 2 + 6), **18** rule files (17 `.md` +
`registry.yaml`). All three numbers are wrong; the skills figure is off by nine.

---

## 3. clo-author parity

Built against the inventory in the 2026-09-08 design spec (see §0.2 — this is a record of
clo-author, not clo-author itself). Slides/presentations noted, not faulted.

### 3.1 Agents (spec Work item A)

| clo-author capability | research-claude equivalent | Status |
|---|---|---|
| `editor` | `agents/editor.md` (369 lines, harvested from POGM4's 366) | **Present** — and the three capabilities the spec called dormant all landed: novelty check with the anti-hallucination caveat (`:45` "Any 'already done' claim must include the URL or DOI … rather than asserting prior work"), no-duplicate dispositions (`:113` "**Do not draw the same disposition twice**"), and `--variance N` (`:117`, `:212`). **But `/review` cannot reach `--variance` — §1.10.** |
| `coder-critic` (merge POGM4 + zoning2026) | `agents/coder-critic.md` | **Present** — success criterion 8 met. Carries POGM4's manifest half (`:74` INV-23, `:75` INV-24) *and* zoning2026's half (`:42` "## Correctness Layer", `:51` no derived CSVs, `:59` zero-inflation/extrapolation traps). |
| `methods-referee`, `domain-referee` | both present (212 / 137 lines) | **Present** |
| `writer`, `writer-critic`, `coder` | all present | **Present** |
| `verifier` (clo-author two-mode, `latexmk` → `quarto render`) | `agents/verifier.md` | **Present** — two modes intact (1–4c standard, 5–10 submission), check 1 is `quarto render`. The POGM4 slide-agent leak was correctly not harvested. |
| `theorist`, `theorist-critic`, `strategist`, `strategist-critic`, `explorer`, `explorer-critic`, `data-engineer` | all present | **Present** |
| `storyteller`, `storyteller-critic` (drop `beamer-scaffold.tex`, keep `quarto-scaffold.qmd`) | both present; `skills/talk/templates/quarto-scaffold.qmd` present, no Beamer scaffold | **Deliberately dropped (Beamer)** — the RevealJS path survives and works. |
| `orchestrator`, `guide-writer` | deleted (D1) | **Deliberately dropped** — replaced by `registry.yaml` + `/pipeline` + `rules/agents.md` §4. |
| `librarian`, `librarian-critic` | `skills/lit-position/` + `agents/lit-critic.md` | **Present, improved** — the spec (E) proposed a *self-check* against librarian-critic's 6 categories; what shipped is a real paired critic agent with its own rubric (`scoring-rubrics.md:207-220`) and an independent `literature` component weight in the registry. Stronger than specified. |
| `humanize-auditor`, `claim-verifier` | `ai-audit/agents/` | **Present as files, unwired** — see §2.4. |

### 3.2 Dormant capabilities to port (spec Work item B — eight rows)

| clo-author port | research-claude equivalent | Status |
|---|---|---|
| 6 design checklists (DiD, IV, RDD, event-study, structural, descriptive) | `skills/strategize/templates/design-checklists/{did,iv,rdd,event-study,structural,descriptive}.md` — all six | **Present**, and bound to a step: "Pass the strategist **only the chosen design's** checklist … Naming all seven is what makes an agent read all seven." |
| `decision-record.md` | `skills/strategize/templates/decision-record.md`, written to `quality_reports/decisions/` by `/strategize` (Step 8), `/strategize theory` (Step 7) and `/discover interview` (Output 3) | **Present** |
| `robustness-plan.md` + 3 PAP registry templates | `skills/strategize/templates/robustness-plan.md`; `pap-templates/{aea-rct,osf,egap}.md` | **Present** |
| `audit-10-checks` (check 1 → `quarto render`; 5–10 unchanged) | `skills/submit/templates/audit-10-checks.md` | **Present**, check 1 is `quarto render`. Two residual drifts against `verifier.md`: its check 3 is "File Integrity" where the verifier's check 3 is "References resolve", and it hardcodes `manuscript_<project>.qmd`. The 4c invariant list, which had drifted, has been correctly collapsed to a pointer. |
| `narrative-arcs.md` — "Descriptive arc extracted as a paper-structure aid, **independent of `/talk`**" | `skills/talk/templates/narrative-arcs.md` only | **Partial** — the file shipped, but only inside `/talk`. `skills/write/` has no reference to it and `skills/write/templates/section-templates.md` is not it. The independence the spec asked for was not delivered. |
| FATAL / ADDRESSABLE / TASTE promoted into `/revise` | `skills/revise/SKILL.md` Step 2 severity table | **Present** |
| `notation-protocol.md`, de-LaTeXed, enforcing INV-7 | `skills/write/references/notation-protocol.md` | **Present** |
| `drafting-gates.md` | `skills/write/templates/drafting-gates.md`, bound at `/write` Step 6 | **Present** |

### 3.3 Deliberate drops (spec Work item C) — two reversals worth recording

| Spec said drop | Actual state |
|---|---|
| `causal-audit-4-phases` | **Reinstated** — `skills/review/templates/causal-audit-4-phases.md` exists and is the backbone of `/review --methods` and `/strategize` Step 4. Correct: the spec's rationale was "no causal claims in a descriptive paper", which was true of the one paper in view, not of the pipeline. |
| `pipeline-state.json` (dropped with D1) | **Reinstated** — `templates/pipeline-state.json`, and it is now the single source of truth for `/pipeline` (`rules/lifecycle.md`: "The state file is the truth; the research journal is written from it"). |
| `claim-source-map` / INV-22 | **Stays retired** — superseded by inline `` `r ` `` + `prose_number_check.py`. Consistent everywhere. |
| `literature-review-6-categories` | **Superseded, not lost** — became `lit-critic`'s six categories. |
| `execution-trace`, `requirements-spec`, `constitutional-governance`, `quality-report` | Not present, no residue. |

### 3.4 Rewrites (spec Work item D)

| File | Spec | Actual |
|---|---|---|
| `table-standards.md` (321 ln) | rewrite → flextable (Word) + kableExtra (PDF) | **Done** — `skills/analyze/references/table-standards.md:145` "`kableExtra` in Word output \| Produces LaTeX/HTML, not a Word table — use flextable". |
| `figure-standards.md` (206 ln) | rewrite → PNG `fig-dpi: 200` Word, vector PDF | **Done**, but see §1.8 (`base_size` conflicts with `data-engineer.md`). |
| `working-paper-format.md` (273 ln) | delete | **Deleted** |
| `content-standards.md` (454 ln) | rewrite | **Done** — now 125 lines, delegating format to `quarto-word.md`/`quarto-pdf.md`. |
| `meta-governance.md` (251 ln, Emory context) | delete | **Rewritten instead** — 30 lines, generic, no Emory. Better than deletion; the promotion protocol it now carries is load-bearing for `/promote`. |
| `permissions.md`, `lifecycle.md` | delete (D1) | **Rewritten instead** — `permissions.md` is now *generated* from `registry.yaml` by `render_registry.py`; `lifecycle.md` (125 ln) is now the `pipeline.py` predicate contract. Both read in full; no retired-pattern content. |
| `pipeline-precedence.md` | delete | **Deleted**; README states "there is nothing left to take precedence over." |

### 3.4b Divergence register

Parity as present/partial/missing answers *what* moved. It does not answer whether each divergence
was **litigated and recorded** or merely drifted. That second question is now tracked separately
and durably in **`docs/decisions/clo-author-divergences.md`**, written against clo-author's own
files at `d36c408` (§0.2). It classifies 19 divergences as INHERITED / DELIBERATE DIVERGENCE /
GAP / OBSOLETE, states for each whether the problem still exists under Quarto, and records whether
the reason is on disk anywhere.

Two results from it bear on this report:

- **Seven of nineteen divergences had no recorded reason** before that file existed: D-2, D-3,
  D-8, D-16, D-17, D-18, D-19.
- **Five of the six GAPs share one shape** — a mechanism was correctly retired, introduced or
  vendored, and its *purpose* was never assigned a new owner. The known-good instance is the
  results registry (D-4): retired correctly, but its purpose — no stale or invented number reaches
  prose — went unowned until `prose_number_check.py`, and in the interval a manuscript scored
  100/100 while carrying four provably wrong numbers and a sentence contradicting its own table.
  D-2, D-3, D-17, D-18 and D-19 are the same shape and still open.

### 3.5 Net parity verdict

**Nothing needed was lost in the port, with two exceptions and one caveat.**

- **Missing:** a data-deposit step (§2.2). `/submit` advertises it in its description and has no
  mode for it.
- **Partial:** `narrative-arcs.md` as a `/write`-side paper-structure aid (§3.2).
- **Caveat:** `/humanize` + `/verify-claims` survive the port as *files* but not as *pipeline
  capability* (§2.4) — they were never in clo-author, so this is not a parity loss, but it is the
  largest functional hole the audit found.

Everything the spec's A, B and D lists called for is otherwise present, and three items (lit-critic,
meta-governance, lifecycle) are stronger than specified.

---

## 4. Quarto-only coherence

**The retired multi-file/LaTeX pattern is essentially gone.** A full-tree scan for `scripts/R/`,
`00_master.R`, results registry, `source()`, `.Rmd`, `latexmk`, `paper/main.tex`,
`paper/sections`, `threeparttable` and `\doublespacing` across `agents skills rules references
hooks templates seeds ai-audit zotpilot-skills` returns 40 hits. **Every hit in the pipeline's own
tree was read in context and is a prohibition, not an assumption** — e.g.
`rules/quarto-empirical.md:37-38` "There is no `scripts/R/` analysis directory, no `00_master.R`,
and no `results_ground_truth.csv`", `agents/coder-critic.md:53` "`source()` inside any chunk:
−10". Several carry explicit `<!-- residue:prohibition -->` markers for `check_fork.sh`. No agent,
skill or rule *assumes* the retired pattern.

`rules/registry-verification-gate.md` is confirmed absent (`83205d7`) and is not reported.

Four residual items:

**4.1 `agents/data-engineer.md:92` recommends `kableExtra` with no format qualifier** — the one
place in the tree where an agent is pointed at a package its own paired critic deducts for. See
§1.7. This is the only substantive Quarto-coherence defect found.

**4.2 `ai-audit/` ships LaTeX-first examples.** `ai-audit/README.md:59-60, 81-83`:

> `/humanize paper/main.tex`
> `/verify-claims paper/main.tex --source papers/smith2024.pdf`

`paper/main.tex` is exactly the retired multi-file LaTeX layout the fork removed. It is
**vendored verbatim** and must not be edited in place (`CLAUDE.md`: "`ai-audit/` is **vendored
verbatim** … and is never edited in place"), so the fix is an upstream PR to `EconGeo/ai-audit`,
not a local edit. `ai-audit/VENDORED.md:27-28` already records having reconciled a *different*
LaTeX-era drift in that tree, so the precedent for an upstream fix exists.

**4.3 `skills/talk/SKILL.md` audits for `overfull hbox` warnings** — in the "Visual quality"
critic category. `\hbox` is a TeX concept; a Quarto RevealJS deck renders to HTML and never
produces one. LaTeX residue in a Quarto-only skill, flagged 2026-09-15, still present.

**4.4 `skills/submit/templates/submission-checklist.md`** carries `- [ ] No \hline -- booktabs
only (INV-3)`. Legitimate on the PDF path (`quarto-pdf.md` governs LaTeX table output), so not a
defect — noted only so it is not re-flagged by the next scan.

---

## 5. Naming and trigger collisions

**5.1 `/humanize` vs `/write humanize` — the sharpest collision in the tree.** Same verb, same
input file types (`.qmd`, `.tex`, `.md`), and `/humanize`'s description enumerates the exact
phrasings a user would use for either: "humanize", "does this sound like AI?", "check for AI
tells", "de-AI this draft", "remove AI voice". "Remove AI voice" and "de-AI this draft" are
*imperatives to edit* — they describe what `/write humanize` does, sitting in the description of
the skill that refuses to do it.

One mitigation exists and is partial: `ai-audit/skills/humanize/SKILL.md` sets
`disable-model-invocation: true`, so the model cannot auto-select it. The practical effect is the
**wrong** resolution — a user who types "de-AI this draft" gets routed to `/write humanize`, which
edits the file, when `/humanize`'s stated design principle is that the file must not be edited.
Typing `/humanize` explicitly is the only way to reach the read-only auditor.

**5.2 `/discover` vs `/lit-position` vs `/seed-papers` — description overlap, resolved by body
text only.** `/discover`'s description still contains the token `lit` and the claim to replace
`lit-review`; `/lit-position`'s description is "Position a project against the literature …";
`/seed-papers`' trigger list includes "check what I already have on X". A user asking "help me
review the literature for this project" matches `/discover`'s description as well as
`/lit-position`'s. The redirect in `/discover`'s body recovers it, but selection happens on the
description. Fixing §1.5 fixes this.

**5.3 `/review` vs `/verify-claims` — cleanly disambiguated.** `/verify-claims`'s description
carries an explicit negative ("NOT for style/grammar review or substance review — use … `/review
--proofread` and `/review`") and its own "When to pick this skill" section. This is the pattern
the other collisions should copy.

**5.4 `/analyze` vs `data:analyze` (plugin) — name collision across namespaces.** The session's
skill list carries both a pipeline `analyze` ("End-to-end analysis inside the declared
manuscript") and a plugin `data:analyze` ("Answer data questions — from quick lookups to full
analyses"). A user typing "analyze this data" matches the plugin's description more closely than
the pipeline's. Outside research-claude's control; noted because the pipeline's description
mentions the manuscript only, which is the right disambiguator and should not be shortened.

**5.5 `/tools` — a name that collides with a Claude Code built-in.** `README.md:539` instructs the
user to "type `/tools`" to inspect the MCP tool list, one line before `README.md:563`'s skills
table lists `/tools` as the pipeline's utility skill. Two meanings, six lines apart, in the
document a new user reads first.

**5.6 Not a collision:** `/careful` and `/freeze` have disjoint verbs and disjoint targets (Bash
vs Edit/Write). `/promote` and `/checkpoint` are disjoint. `/pipeline` and the stage skills are
explicitly a driver/driven pair (`rules/agents.md` §4).

---

## 6. Prioritized findings

### Tier 1 — Real conflicts (contradictory instructions for the same task)

| # | Finding | Files | §ent |
|---|---|---|---|
| 1 | **`/write humanize` edits the file; `/humanize` refuses to, on principle.** Two shipped skills, opposite actions, same input, near-identical names. Also the only case where a user's plain-English phrasing routes to the skill whose design principle forbids the action. | `skills/write/SKILL.md:102-108` vs `ai-audit/skills/humanize/SKILL.md` | §1.1, §5.1 |
| 2 | **`data-engineer` is told to prefer `kableExtra` with no format qualifier**, and its own paired critic deducts −5 for using it in Word. | `agents/data-engineer.md:92` vs `rules/quarto-word.md:49,169` | §1.7, §4.1 |
| 3 | **`/talk`'s inline format table disagrees with `format-constraints.md` on every row**, plus 5-vs-6 critic categories and a 10pt-vs-18pt font floor. | `skills/talk/SKILL.md` vs `templates/format-constraints.md`, `review/templates/talk-review-6-categories.md`, `references/slide-design-principles.md:15-17` | §1.9 |
| 4 | **`paper-to-code-map.md` forbids the variable name `chunk-structure.md` demonstrates**; `data-engineer` says `base_size >= 14` where `figure-standards.md` sets 11. Both pairs are bundled resources of the same skill. | `skills/analyze/templates/*`, `references/figure-standards.md:41`, `agents/data-engineer.md:40` | §1.8 |
| 5 | **`editor.md` delegates `--variance` conflict enforcement to `/review --peer`, which has no `--variance` flag.** | `agents/editor.md:124` vs `skills/review/SKILL.md` | §1.10 |

### Tier 1b — Safeguards that exist but never run (added by the divergence audit)

Both are `GAP`s in `docs/decisions/clo-author-divergences.md`. Neither is inherited from
clo-author; both are failure modes this pipeline's own architecture created.

| # | Finding | Register |
|---|---|---|
| 1b-i | **`check_install.sh` is wired to no automatic trigger.** It detects all four symlink failure modes — item never linked, link dangling, link pointing at another checkout, and **a real file shadowing a canonical one**. It is named only in `README.md:207` and `CLAUDE.md:103` (instructions to a human), `/promote` Step 5, and two test files. `seeds/settings.json` carries eight hook entries and **none invokes it**; its only `SessionStart` hook matches `compact\|resume` and runs `post-compact-restore.py`. `/promote` is the sole in-session caller — a skill run only when someone is *already* reconciling the tree. This is the mechanism behind a project-local skill shadowing a shared rule for three months and waiving a real defect through two critic rounds: **the detector existed the whole time and nothing called it.** clo-author needed no such check (its `.claude/` was 138 real tracked files, 0 symlinks, no installer), so this is not a lost safeguard — it is an unguarded new hazard. | D-2 |
| 1b-ii | **`protect-files.sh` ships dead.** clo-author wired it as the first `PreToolUse` hook on `Edit\|Write`, blocking edits to `settings.json`, `strategy-memo-*.md`, `referee-report-*.md` and `quality-score-*.json`. research-claude ships the script and documents it in `hooks/README.md:35` as *"PreToolUse \| Blocks edits to protected paths"* — but `grep -c protect-files seeds/settings.json` returns **0**, and that file's own `$comment` states hooks *"fire only because they are named here."* It never fires. The protected class matters more now, not less: `/review` already had to add a `git status --porcelain` check because *"a project gate restamped two committed reports."* | D-3 |

### Tier 2 — Residue and gaps (something claimed that is not delivered)

| # | Finding | §ent |
|---|---|---|
| 6 | **`ai-audit` is installed but wired to nothing.** No registry entry, no `/pipeline` stage, no `/review` route. `/submit final` can pass at ≥95 with no hallucination check. Compounded by `/promote`'s pathspec excluding `ai-audit/` while `sync-ai-audit.sh` `rm -rf`s it — edits made through a project link are silently destroyed. | §2.4 |
| 7 | **`/submit`'s description claims to replace `data-deposit`; no deposit step exists.** `package` assembles; nothing deposits. Journal profiles reference the requirement ("AJPS Replication Policy requires deposit before acceptance") with no pipeline step behind it. | §2.2 |
| 8 | **`/discover`'s frontmatter contradicts its body** — claims to replace `lit-review` and offers `lit` in `argument-hint`; the body says the mode no longer exists. Selection happens on the description. | §1.5, §5.2 |
| 9 | **`README.md:563` lists `/review-paper`**, which does not exist. The only dangling skill reference in the tree. | §2.1 |
| 10 | **`/ztp-profile` and `/ztp-tutor` are installed into every project and referenced nowhere**; `/ztp-ollama` is referenced once, as a pattern example, and is absent from the README's Ollama setup section where a user would look. | §2.3 |
| 11 | **`/tools render` hardcodes `manuscript_<project>.qmd`** where every other skill runs `pipeline.py manuscript`. Wrong command for any project declaring a different `manuscript:`. | §1.4 |
| 12 | **`narrative-arcs.md` shipped inside `/talk` only.** The spec asked for it "independent of `/talk`" as a paper-structure aid; `/write` has no reference to it. | §3.2 |
| 13 | **`ai-audit/README.md` ships `paper/main.tex` examples** — the retired multi-file LaTeX layout. Vendored verbatim, so this is an upstream PR to `EconGeo/ai-audit`, not a local edit. | §4.2 |
| 14 | **`skills/talk/SKILL.md` audits for `overfull hbox`** — a TeX concept in a RevealJS-only skill. | §4.3 |

### Tier 3 — Cosmetic

| # | Finding | §ent |
|---|---|---|
| 15 | README's opening counts are all wrong: "17 agents, 17 skills and 19 rules" vs actual 18 / 26 / 18. | §2.6 |
| 16 | README's skills table omits 14 of 26 shipped skills, including `/review`, `/submit`, `/revise`, `/talk`, `/checkpoint`, `/tools` and `/promote`. | §2.1 |
| 17 | `audit-10-checks.md` check 3 ("File Integrity") still does not match `verifier.md` check 3 ("References resolve"), and hardcodes the manuscript filename. The 4c drift that mattered has been correctly collapsed to a pointer. | §3.2 |
| 18 | `/review`'s `--theory` and `--all` appear in the routing list with no Mode Details section and no `record-score` line, unlike every other flag. | §2.2 |
| 19 | `README.md:539` tells the user to type `/tools` to inspect MCP tools, six lines above listing `/tools` as a pipeline skill. | §5.5 |
| 20 | `skills/.DS_Store` and `skills/checkpoint/.DS_Store` are tracked in a public template repo. | — |

### Explicitly NOT findings

- `rules/registry-verification-gate.md` — deleted today, zero dangling references. Confirmed clean.
- The `ztp-*` version gap against upstream / PyPI — **expected, not a defect.** `CLAUDE.md` and
  `zotpilot-skills/VENDORED.md` carry the test that settles it; acting on it was tried and reverted
  on 2026-09-15 (`c1bc220`). Do not re-vendor from `xunhe730/ZotPilot`.
- `disposition-pool.md` vs `editor.md` on the zero-FATAL decision rule — **fixed since 2026-09-15.**
  The duplicates were removed and the resolution is documented in the file itself
  (`disposition-pool.md:9-13`: "`editor.md` is right … so the duplicates are gone rather than
  corrected").
- `/freeze` and `/careful` "session-scoped" claims — **fixed.** Both gotchas now open "**Not
  session-scoped.** The guard file persists on disk."
- `/strategize pap` score scope, `/submit` R-133 coverage check, `/write` cleanup Step 4b —
  **all fixed** since 2026-09-15.
- Beamer / slide rendering — **deliberately dropped** per spec Work item A. `quarto-scaffold.qmd`
  survives, `beamer-scaffold.tex` does not. Not faulted.
- `kableExtra` in `rules/quarto-pdf.md`, `chunk-structure.md:71`, `coding-standards-r.md` — all
  correctly format-qualified to the PDF path. Only `data-engineer.md:92` is unqualified.
