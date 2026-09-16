# Skill best-practices audit — 2026-09-15

**Scope:** all 25 skills that ship with research-claude: 18 under `skills/`, 6 under `zotpilot-skills/` and 2 under `ai-audit/skills/`. The last two groups are vendored and marked `*` below.
**Method:** six read-only auditor subagents. Each read every SKILL.md and every supporting file in full, then read the files that invoke or test each skill. A seventh subagent read the rulings (R-1…R-136) and the repair sign-off in full, and returned the constraints that bear on these changes. Frontmatter semantics come from the official Claude Code skills docs (fetched this session).
**Status:** audit only. Nothing has been edited. The functionality evals (P7) have **not been run**, because the request's test-input placeholder was left unfilled. A proposed input for each skill is in §6.

> ### ⚠️ Correction — added 2026-09-15, after this audit shipped
>
> **Three items about the vendored `ztp-*` skills were wrong and are withdrawn:** the
> High-severity "vendored ztp-\*" row in §4, the "ztp version skew" item in §5 step 1, and
> decision 3 in §7. Each is struck through in place below.
>
> They read a version-number gap (`~/.claude/skills/ztp-*` stamped 0.5.3 vs vendored
> `v0.5.0-62-ga8120c5`) as staleness. **It is not staleness.** Upstream `xunhe730/ZotPilot`
> is a **different lineage** from the `EconGeo/ZotPilot` fork this pipeline runs — not a
> newer revision of it. The fork is a v0.5.0 base plus ~40 commits (Ollama provider,
> multi-library indexing, token-aware chunking, ChromaDB batching, `delete_note`) and
> deliberately does not track upstream.
>
> Acting on the finding re-vendored all five `ztp-*` at upstream v0.5.3 and shipped a
> `ztp-setup` built on `zotpilot setup --list-vendors --json` and `--verify`, neither of
> which the fork's CLI implements. Tested the same day against the installed build:
>
> ```
> $ zotpilot setup --list-vendors --json
> zotpilot: error: unrecognized arguments: --list-vendors --json
> ```
>
> The whole change was reverted in `c1bc220`; `zotpilot-skills/` and the five
> `~/.claude/skills/ztp-*` copies are byte-identical again, all at fork `a8120c5`.
>
> **A version gap here is expected, not a defect. Never re-vendor from upstream and never
> install ZotPilot from PyPI.** See `zotpilot-skills/VENDORED.md` (the full record and the
> test), `scripts/sync-zotpilot-skills.sh` and `CLAUDE.md`.
>
> Nothing else in this audit was affected — the other §4 rows were found independently and
> still stand as written.

## The seven practices

| # | Practice | Pass condition |
|---|---|---|
| P1 | Short & direct | SKILL.md is plain imperative steps. Rationale, background and lookup tables live in reference files. |
| P2 | Human-triggered only | Frontmatter has `disable-model-invocation: true` and a one-line description. |
| P3 | Progressive disclosure | Each reference file is named inside the step that uses it and read only at that step. No upfront resource tables, no orphans. |
| P4 | HITL with options | Each real decision point presents 5–10 options and waits. Binary safety gates are exempt (N/A). |
| P5 | Connectors/research out of context | Static data is kept in reference files. Live connector or research calls run in a subagent that returns a clean result. |
| P6 | Self-improvement rule | When the user corrects an output or explicitly likes one, the skill asks whether to make that a permanent skill update. It never updates silently. |
| P7 | Functionality eval | A 3-subagent eval checks step order, reference loading and connector calls. |

Legend: ✅ meets · 🟡 partial · ❌ gap · N/A · `*` vendored (changes go upstream, never in place).

---

## 1. Scorecard

| Skill | SKILL.md lines | P1 | P2 | P3 | P4 | P5 | P6 | P7 | Safe to set `disable-model-invocation`? |
|---|---|---|---|---|---|---|---|---|---|
| pipeline | 73 | 🟡 | ❌ | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | **Yes** |
| tools | 114 | 🟡 | ❌ | ❌ | ❌ | 🟡 | ❌ | ❌ | Yes, after rewording the `context-monitor.py` nudge |
| promote | 103 | 🟡 | ❌ | ✅ | 🟡 | ✅ | 🟡 | ❌ | **Yes** |
| freeze | 57 | 🟡 | 🟡 | ❌ | N/A | N/A | ❌ | 🟡 | Yes, and reword the hook deny text |
| careful | 63 | 🟡 | 🟡 | ❌ | N/A | N/A | ❌ | ❌ | Yes, and reword the hook deny text |
| review | 330 | ❌ | ❌ | 🟡 | ❌ | 🟡 | ❌ | 🟡 | **No**: `/pipeline` review, referees and adopt |
| revise | 92 | 🟡 | ❌ | 🟡 | ❌ | 🟡 | ❌ | ❌ | **Yes** |
| submit | 97 | 🟡 | ❌ | 🟡 | ❌ | 🟡 | ❌ | ❌ | **No**: `/pipeline` submit invokes `final` |
| write | 179 | ❌ | ❌ | 🟡 | 🟡 | 🟡 | ❌ | ❌ | **No**: `/pipeline` write |
| talk | 143 | 🟡 | ❌ | ❌ | ❌ | 🟡 | ❌ | ❌ | **No**: `/pipeline` talk |
| analyze | 64 | ✅ | ❌ | 🟡 | 🟡 | ✅ | ❌ | ❌ | **No**: `/pipeline` analyze |
| strategize | 300 | ❌ | ❌ | 🟡 | ❌ | 🟡 | ❌ | 🟡 | **No**: `/pipeline` strategy and theory (`pap` could split out) |
| discover | 170 | 🟡 | ❌ | ❌ | ❌ | 🟡 | ❌ | 🟡 | **No**: `/pipeline` data (`interview`/`ideate` could split out) |
| checkpoint | 245 | 🟡 | ❌ | ❌ | N/A | 🟡 | ❌ | ❌ | **Yes** |
| lit-position | 141 | 🟡 | ❌ | 🟡 | ❌ | ❌ | ❌ | ❌ | **No**: `/pipeline` literature |
| new-project-ztp | 97 | 🟡 | ❌ | 🟡 | N/A | 🟡 | ❌ | ❌ | **No**: `/pipeline` setup |
| ztp-data-tag | 179 | 🟡 | ❌ | 🟡 | 🟡 | ❌ | ❌ | ❌ | **Yes** |
| seed-papers* | 162 | 🟡 | ❌ | 🟡 | 🟡 | 🟡 | ❌ | ❌ | Yes, via upstream |
| ztp-research* | 319 | 🟡 | ❌ | 🟡 | 🟡 | 🟡 | ❌ | ❌ | **No**: lit-position Step 1 |
| ztp-setup* | 29 | ✅ | ❌ | ✅ | 🟡 | ✅ | ❌ | ❌ | **No**: new-project-ztp Step 2 |
| ztp-review* | 30 | ✅ | ❌ | ✅ | 🟡 | 🟡 | ❌ | ❌ | **No**: lit-position Step 2 |
| ztp-profile* | 35 | ✅ | ❌ | ✅ | 🟡 | ❌ | ❌ | ❌ | Yes, via upstream |
| ztp-tutor* | 431 | ❌ | ❌ | ❌ | 🟡 | 🟡 | 🟡 | ❌ | Yes, via upstream |
| humanize* | 205 | ❌ | ✅ | ❌ | N/A | ✅ | ❌ | ❌ | Already set |
| verify-claims* | 134 | 🟡 | ❌ | 🟡 | 🟡 | ✅ | ❌ | ❌ | Yes, via upstream |

**Totals.** P6 is the weakest practice: nothing meets it, and only three skills partially meet it. P7: no skill has a behavioural eval. P2: one skill (humanize) meets it. P1 has 5 hard gaps: review, strategize, write, ztp-tutor and humanize.

---

## 2. The P2 constraint — read before applying anything

Per the docs, `disable-model-invocation: true` means "Only you can invoke; Claude cannot". When that flag is set, the model's Skill-tool call is blocked. Today the pipeline is built on the model invoking skills:

- `skills/pipeline/references/*.md` tell the model to invoke `/lit-position`, `/discover data`, `/strategize [theory]`, `/analyze`, `/write full`, `/review` (all routes), `/submit final`, `/talk create` and `/new-project-ztp`.
- `lit-position` invokes `/ztp-research` and `/ztp-review`. `new-project-ztp` invokes `/ztp-setup`.
- `tests/run_fixture.sh --live` runs `/pipeline run`, and that run reaches these skills.

**Blanket application breaks `/pipeline`.** Three ways forward (decision needed, §7):

- **A. Safe set now.** Set the flag on pipeline, promote, revise, checkpoint, ztp-data-tag, freeze, careful and tools. The last three need the hook text reworded first. Upstream PRs cover seed-papers, ztp-profile, ztp-tutor and verify-claims. Leave the 13 chained skills model-invocable.
- **B. Re-route the driver.** Change each `pipeline/references/<stage>.md` from "invoke /X" to "Read `.claude/skills/X/SKILL.md` and follow it", then set the flag everywhere. *Unverified:* that reading a SKILL.md reproduces invocation behaviour (arguments, `allowed-tools`). Test with `run_fixture.sh --live` before relying on it.
- **C. Split modes.** Move the human-only modes into their own flagged skills (`strategize pap`, `discover interview`/`ideate`, `submit target`), and keep the pipeline-facing modes invocable. Registry `producer:` entries, `rules/agents.md`, `rules/permissions.md` and the `check_refs` skill-refs must all follow the split.

The rulings add three constraints that apply whichever route you pick:
- **R-101:** each mode must still reach its own critic dispatch.
- **R-104–R-107, R-113:** every `record-score` and `pipeline.py log` call site must survive any slimming.
- **R-42/R-44/R-132:** the numeric critic gates cannot be replaced by a user pick.

Also, four hook messages currently tell the *model* to run a slash command:
- `session-guard.py` freeze deny: "Run /freeze off to deactivate."
- `session-guard.py` careful deny: "Run /careful off to deactivate, or rephrase the command." This line also invites the model to evade the guard.
- `context-monitor.py:197-198`: "consider running /tools learn".

Reword them to "ask the user to run…".

---

## 3. Opportunities by practice (prioritised)

### P1 — Short & direct

| Priority | Skill | Movable lines (est.) | What to move / cut |
|---|---|---|---|
| 1 | review | ~140 of 330 | Several blocks go: the 4-phase econometrics protocol (→ `templates/causal-audit-4-phases.md`), the inline 12-category code checklist (the template has 16), the resources table, principles and the incident rationale. **Keep:** the "Verifier Pass/Fail Definition" heading, the `.claude/agents/verifier.md` path and the `git status --porcelain` text. `tests/test_review_contracts.py` pins all three. |
| 2 | strategize | ~175 of 300 | Replace the pasted Pre-Strategy Report and PAP interview with pointers to their existing template and reference files. Remove the PAP section list, which repeats `pap-templates/*`, and the observational adaptation, which repeats `osf.md` §6. Add a Pre-Theory template. Drop the resources tables and principles. Unify the iterate rule: strategy mode says "CRITICAL", PAP mode says "<80". |
| 3 | ztp-tutor* | ~170 of 431 | Upstream: split into `persona-parsing.md` (Step 2), `annotation-spec.md` (Steps 3–4) and `unplaced-reasons.md` (Step 9). |
| 4 | humanize* | ~145 of 205 | Upstream: delete the 10 categories, which repeat `humanize-auditor.md:26-122` almost verbatim. Move the "Why"/"when" text to the README. |
| 5 | checkpoint | ~100 of 245 | Make `rules/logging.md` the only copy of the entry formats. Move `--setup-obsidian` to `references/obsidian-setup.md`. Delete the stale Precedence section (it names `~/.claude/skills/checkpoint`, which does not exist). |
| 6 | discover | ~90 of 170 | Remove the pasted interview, spec and catalogue blocks, which disagree with the templates. The `lit` history note becomes a one-line redirect. Delete the stale literature principles. |
| 7 | write | ~75 of 179 | Delete the Section Standards table, the paper-type list and the gate text (each repeats a template), plus the style-guide workflow. Fix the pointer at :136: the templates are in `section-templates.md`, not `writer.md`. |
| 8 | ztp-data-tag | ~60 of 179 | Move three sections out to `references/schema.md`, `zotpilot-retrieval.md` and `undo.md`. Delete the duplicate Rules. |
| — | tools, talk, submit, lit-position, ztp-research*, verify-claims*, pipeline, promote, freeze, careful, revise, new-project-ztp, seed-papers* | 15–95 each | All remove the same kinds of content: inline copies of scripts, templates and agents; resources tables; Principles sections; and "Replaces the old …" history in the description. |

### P3 — Progressive disclosure

**Most skills share the same pattern.** A "Bundled Resources" table sits near the end of SKILL.md, and each agent file carries its own flat "read on demand" list, so no read is tied to the step that needs it. Worse, **the inline copies have drifted from the files they summarise**. Fix both in one pass:
1. Name each file in the step that needs it.
2. Delete the inline copy.
3. Add a contract test like `test_review_contracts.py` wherever two copies must stay aligned.

| Skill | Orphans / drift found | Step binding to add |
|---|---|---|
| review | `templates/disposition-pool.md` is an orphan and **contradicts** `editor.md`: 0 FATAL means Minor in one, Major (with 4+ ADDRESSABLE) in the other. `templates/referee-report-template.md` is an orphan and has drifted from both referee agents. `data-review-6-categories.md` belongs to `/discover`, since no `/review` mode dispatches explorer-critic. SKILL.md says 12 categories and 6 categories where the templates and agents say 16 and 8. | Name the template in each mode that dispatches its critic. Load gotchas at the `--peer` and `--methods` steps. |
| submit | `templates/audit-10-checks.md` is an orphan and has drifted from `verifier.md` (check 3, INV list). | Delete it or reduce it to a pointer. Load gotchas at `final`. |
| discover | `templates/lit-review-entry.md` and `references/pdf-processing.md` are orphans. The inline interview categories and the 8-section spec differ from `interview-flow.md` and `research-spec.md`. Grades are A–D in the skill and A–F in the template. | Interview step reads `interview-flow.md`. Spec step writes with `research-spec.md`. Data step uses `data-assessment.md`, aligned to A–D and the critic's 6 categories. |
| strategize | No step picks `design-checklists/<design>.md` or `pap-templates/<platform>.md`. `discipline-cards.md` claims a wiring that SKILL.md lacks. | Step 3 passes only the chosen design's checklist. The PAP step reads only the chosen platform's template. |
| talk | The inline format table differs on **every row** from `format-constraints.md`. Critic categories: 5 in the skill, 6 in the template. Font minimum: ≥10pt vs ≥18pt. "overfull hbox" is LaTeX residue. Resource paths don't resolve. | Step 2 reads the arc, then scope, then scaffold, then design files, each at its own sub-step. |
| write | `cleanup-patterns.md` is used by no drafting step, although the description promises a cleanup pass. humanize-mode category names differ from the file. The style-guide mode omits the protocol's self-citation step. | Add Step 4b (cleanup), and bind templates at Step 4 and notation at strategy/results. |
| analyze | `figure-standards.md` says `base_size = 11` but `data-engineer.md` says `>= 14`. `paper-to-code-map.md` forbids `treated`, but `chunk-structure.md` and the fixture use it. | Step 1 reads `paper-to-code-map.md`. Steps 2–3 read the table and figure standards. |
| checkpoint | All 3 templates duplicate inline text and are never read at a step. Stray `.DS_Store`. | Bind 4a, 4b and 4c to their templates. |
| tools | `gotchas.md` is loaded "Always" and **contradicts** SKILL.md in 3 places. | Move each surviving gotcha into its subcommand. |
| freeze / careful | `gotchas.md` is never referenced. Both claim "session-scoped", which is false (the guard file persists on disk). | Fix the claims, or delete the files. |
| pipeline | `setup.md`, `talk.md` and half of `review.md` are unreachable from `next`, so a normal `run` skips the ZotPilot check. | Read `setup.md` before the loop. |

### P4 — HITL with options

Binary approve/abort gates stay binary. Critic score gates are numeric and not user-overridable (R-42, R-132). The table lists only the points where **5–10 options add real value**. Each new wait must **honour `--yes`** (take the top-ranked option and log it), or `/pipeline` and the live fixture tier will stall.

| Skill | Decision point (today → proposed) |
|---|---|
| strategize | Today: one design dispatched, alternatives only recorded afterwards. Proposed: after Step 1, show **5–8 candidate designs** (variation, estimand, key assumption, main threat, data fit) and wait. Move theory "Theorist asks" to the main session, since the theorist has no user-facing tool. |
| discover | Research-question framing: **5–8 framings** before writing the spec. Ideate: **5–10 questions**, then wait for a pick. Data: a ranked shortlist, then a pick. Target journals: tiers from the discipline card, before writing `domain-profile.md`. |
| lit-position | Step 4 gap and Step 5 positioning: **5–7 variants**, pick one, then stress-test it. Strike 3: 3–5 narrowed claims plus named search extensions. |
| submit `target` | Today: 3 journals, no wait. Proposed: **5–10 ranked journals** (fit, desk-reject risk, AI-disclosure field), then wait, and carry the pick into `--peer`/`final`. |
| review `--peer`/`--stress` | No journal given: 5–10 candidates. Desk reject: 5 alternative venues instead of 1–2. Re-run: a menu of disposition pairs. |
| revise | Show the classification table and wait. FATAL: ≥5 paths (re-estimate, narrow the claim, robustness, concede in limitations, switch venue). DISAGREE: 3–5 response strategies. |
| talk | Before building: **5–8 hooks / key-slide framings** plus an outline, then wait. |
| write | GATE 1 and `abstract`: **5–8 hooks or contribution statements**. Paper type: confirm when ambiguous. |
| pipeline | Strike-3 escalations (strategy, data, literature): **5–10 alternatives** instead of one. Add an explicit theory opt-in prompt. |
| analyze | Turn the Pre-Code Report "Assumptions made" into a gate with 2–4 alternatives each (5–10 is overkill; design belongs to `/strategize`). |
| seed-papers*, ztp-research* | 5–8 search-query framings before searching. Land this in the lit-position bridge. |
| ztp-profile* | 3–5 taxonomy schemes before the itemised plan (upstream). |
| ztp-data-tag | Rank 5–8 pilot collections. Add a tag-vocabulary merge step for near-duplicate `dataset:*` tags. |
| tools | `commit` has **no confirmation** before commit or PR/merge: add binary gates. `learn`: a candidate list to pick from. |

### P5 — Connectors and research out of context

Precedent already in the repo: `agents/lit-critic.md:5-6` declares `mcpServers: [zotpilot]`. That means a subagent *can* hold ZotPilot, which removes the premise behind seed-papers' "subagents cannot query ChromaDB" note. Literature ingest stays ZotPilot-only.

| Skill | In the main context today | Route |
|---|---|---|
| ztp-data-tag | A per-paper MCP loop (`get_paper_details`, `search_papers`, `get_passage_context`). A whole-library run will exhaust context. | A per-batch extraction subagent with `mcpServers: [zotpilot]` returns JSON records. Preview and writes stay in the main context. |
| lit-position | `/ztp-research` search, citation-chain following, `/ztp-review` synthesis. | A subagent returns the candidate table and scooping-risk verdict. |
| pipeline | The literature creator is `kind: skill`, so ZotPilot runs in the driver's context. Full critic reports also return as text. | Run `/lit-position` in a subagent returning paths plus a summary. Critics return a compact score block. |
| checkpoint | Obsidian MCP reads and writes (project note, Home, Kanban, daily note). | A subagent returns "wrote: …", or split into its own skill. |
| submit `target` | Reads `journal-profiles.md` (547 lines) and `discipline-cards.md`. Claims to consider "recent publications" without having WebSearch. | A subagent returns the ranked table. Grant it WebSearch or drop the claim. |
| ztp-tutor* | `get_paper_for_tutor` returns the whole paper's `page_texts`. | A subagent plans annotations and returns only the path and counts (upstream). |
| ztp-profile* | `browse_library` ×3 plus `profile_library`. **Tested:** `profile_library` is not in this session's ZotPilot toolset. | A subagent returns a curation profile. Fix the tool name upstream. |
| discover | Ideate "novelty" has no source. WebSearch/WebFetch are pre-approved but unused. The ZotPilot-first rule (`rules/literature-search-order.md`) is unmentioned. | Novelty via a ZotPilot subagent. Remove the web tools. |
| revise, write | Main context reads the full manuscript and all chunk labels before a subagent re-reads them. | Hand the scan to the dispatched agent, which returns a brief. |
| tools | `validate-bib` scans every `.qmd` and the `.bib` inline. `journal` regenerates from git history inline. | Script `validate-bib`. Run `journal` in a subagent. |

`allowed-tools` doesn't match what the skills actually run:
- revise, strategize, discover and lit-position run `pipeline.py` without pre-approved `Bash`.
- No ZotPilot-using skill pre-approves `mcp__zotpilot__*`.

Per the docs, `allowed-tools` only pre-approves tools, so the result is extra permission prompts, not failures.

### P6 — Self-improvement rule

No skill has one. Three skills come partway:
- `/pipeline` has "Suggested Learnings", but only on strikes and escalations, not on user corrections.
- `/promote` is the landing mechanism.
- ztp-tutor saves a persona without asking.

`/tools learn` is a one-sentence stub, and "auto-memory handles corrections automatically" makes learning silent, which violates the practice.

**Recommended design: one mechanism, not 25 copies.**
1. Add a shared rule, e.g. `rules/skill-improvement.md`. **Trigger:** the user corrects output, or explicitly approves an output as an example. **Ask:** "Make this a permanent update to `<skill>` (step N / `<reference file>`)?" **On yes:** draft the diff with skill-creator, strip project specifics (R-27/R-131; `check_fork.sh` must pass), and land it via `/promote`. **Never write silently.**
2. Give each skill a single closing step: "Apply `.claude/rules/skill-improvement.md`." For `/checkpoint`, make it a report line rather than a blocking prompt, so the user's forced `--auto` holds.
3. Make `/tools learn` point to that rule, or delete it and repoint the `context-monitor.py` nudge at `/promote`.
4. For vendored skills, the rule routes to an upstream PR. `/promote`'s `git status` pathspec omits `ai-audit/` and `zotpilot-skills/`, and the sync scripts `rm -rf` those directories, so a vendored edit made through a link is silently lost.

**Conflict to resolve:** `rules/meta-governance.md:16` requires a pattern validated across **3+ projects** before promotion. A per-correction rule needs either a project-level tier (gotchas or a project override first, promotion later) or a relaxed bar.

### P7 — Functionality evals

No skill's behaviour is tested:
- `tests/test_pipeline.py` tests `pipeline.py`.
- `test_review_contracts.py` pins text.
- `run_fixture.sh` mechanical tier simulates dispatch log lines.
- The `--live` tier stops at `strategy` by default and **seeds** the literature stage, because a temp dir has no Zotero.

Prerequisites for a real eval suite:
1. A mock ZotPilot MCP server or a small fixture Zotero/ChromaDB. It is needed by lit-position, seed-papers, ztp-data-tag, new-project-ztp and all ztp-* skills.
2. Assertions that read the transcript (`--output-format stream-json`) for tool order and which files were read.
3. Per the handoff, **assert mechanism, not outcomes**: dispatched, critic followed, score recorded. Do not assert that an LLM cleared 80.
4. Run evals one at a time. Two parallel adoptions exhausted a 5-hour usage window in about 15 minutes.

Proposed inputs are in §6.

---

## 4. Defects found during the audit (outside the seven practices)

"Verified" means I checked it myself this session (tested or read in full). "Auditor" means a subagent reported it with a file:line cite after reading the file in full, and I have not re-checked it.

| Severity | Skill | Defect | Basis |
|---|---|---|---|
| High | careful | `git push origin main --force` and `find . -delete` are **not blocked**. `re.IGNORECASE` makes the safe `git branch -d` blocked. The deny text says "or rephrase the command". | **Verified** (patterns tested against `hooks/session-guard.py`) |
| High | freeze | The hook denies Edit/Write on `session-guards.json` while freeze is active, so the documented `/freeze off` steps fail unless done via Bash. `/freeze` with no dirs blocks every edit. Neither skill says to merge guard keys, so activating one can clobber the other. | **Verified** (hook read in full) |
| High | strategize | `/strategize pap` records its critic score into the `strategy` component, so it can overwrite the strategy-memo score that `coder`/`data-engineer` gate on. | **Verified** (SKILL.md:179 read) |
| ~~High~~ **WITHDRAWN** | vendored ztp-* | ~~`~/.claude/skills/ztp-{research,setup,tutor}` differ from the vendored copies. The global copies are v0.5.3; vendored is v0.5.0-62 … the vendored copies never run while coauthors run the older ones.~~ **Not a defect — see the correction at the top of this file.** Upstream is a different lineage, not a newer revision, and the fork's CLI does not implement the flags upstream's `ztp-setup` drives. The MCP server's "outdated" notice is subject to the same rule. | Premise falsified and reverted the same day (`c1bc220`): `zotpilot setup --list-vendors --json` → `error: unrecognized arguments` |
| High | submit | The R-133 coverage check (`state show` before trusting a PASS) is in the principles and gotchas but **not in the `final` workflow**, so a renormalised gate can pass with one scored component. | Auditor |
| Med | review | `--theory` has no mode section or `record-score`, yet `adopt.md` says it records `theory`. `--peer` records a score the editor's format has no field for. `--stress` "decision" contradicts `editor.md`. `--variance` is undocumented. | Auditor |
| Med | revise | No `Bash` in `allowed-tools`, yet it runs `pipeline.py`. Never calls `post writer`, which `rules/revision.md:31` requires. The REWRITE class exists in the skill only. Step 6 says the letter is Markdown with page refs, but the template is `.qmd` and forbids page numbers. | Auditor |
| Med | checkpoint | Drops three things its rules require: the `Plan staleness sweep:` report line (`rules/session-handoff.md`), the handoff reference dry-run, and the `ai_use_log.md` confirmation (`rules/ai-disclosure.md:116`). | Auditor |
| Med | ztp-setup* | ~~Installs PyPI `zotpilot` while `VENDORED.md` names the fork.~~ **FIXED** — step 2 installs `git+https://github.com/EconGeo/ZotPilot.git` and step 3 no longer routes updates through PyPI (fork `b13bf83`/`f34da2a`, vendored at `f92e5b0`). **Still open:** stores API keys in `~/.config/zotpilot/config.json`, which contradicts the global `~/.secrets.env` rule. `new-project-ztp` Step 2 promises micromamba + fork + project `.mcp.json`; the first two are now in ztp-setup, but registration is client-level — a live `zotpilot upgrade --skill-only` reported "Registered on: Claude Code, OpenCode", not a project `.mcp.json`. | Auditor; fixed part **verified** this session |
| Med | ztp-data-tag | `create_note(idempotent=true)` skips any item that already has a ZotPilot note, yet the item still gets tagged `data-tagged`, so it can end up tagged with no Data note. | Auditor (from the skill's own text) |
| Med | lit-position / ztp-research* | The local-first order in `rules/literature-search-order.md` is cited but not enforced: ztp-research Phase 1 goes straight to external search. | Auditor |
| Med | pipeline | The loop and the stage skills both appear to `record-score`/`strike`, so one failing round may count **two strikes**. | Auditor, **unverified**. Confirm before fixing. |
| Med | tools | `render` hardcodes `manuscript_<project>.qmd` instead of `pipeline.py manuscript`. The lint default path disagrees with `lint-scripts.sh`. `validate-bib`, `journal`, `context` and `learn` have no steps. | Auditor |
| Low | write | `/write humanize` rewrites in place while `/humanize` is detect-only by design. | Auditor |
| Low | seed-papers* | Step 1 reads a "Research Question" field that `domain-profile.md` lacks, so it always falls through to asking. `doc_id` and `ZOTERO_KEY` are mixed in the dedupe line. | Auditor |
| Low | new-project-ztp | The `## Current Project State` anchor exists in no shipped CLAUDE.md. The index-time estimate contradicts the README. | Auditor |
| Low | promote | Re-link command (`apply.sh --link`) vs `shared-pipeline.md` (`bootstrap-pipeline.sh --tip`). The lock test in Step 1 is always true in tip mode. | Auditor |
| Low | state/ | `obsidian-config.md.example` still names the removed `/obsidian-digest-sync`. `check_refs` doesn't scan `state/`. | Auditor |

---

## 5. Suggested order of work

1. **Fix the high-severity defects in §4** (careful patterns, freeze-off path, PAP score scope, submit coverage check — *not* the withdrawn ztp version skew). These are correctness issues independent of style.
2. **Decide the P2 route** (§2 A/B/C), then apply the flag and reword the four hook messages.
3. **Add the P6 rule once** (`rules/skill-improvement.md` + one closing step per skill + `/tools learn` repoint), after settling the meta-governance conflict.
4. **P1 + P3 together, one skill per branch, via skill-creator.** Order: review → strategize → write → discover → talk → checkpoint → the rest. For each: bind reference files to steps, delete inline copies, add a contract test for any pair that must agree, and run `check_fork.sh` plus the full test suite. Keep every `record-score`, `pipeline.py log` and pinned test string (R-104–R-113).
5. **P4 option points**, each honouring `--yes`.
6. **P5 subagent routing** for ztp-data-tag, lit-position, checkpoint Obsidian and submit `target`.
7. **P7:** build the mock ZotPilot MCP, then run the 3-subagent evals in §6 one skill at a time, starting with the skills just refactored.
8. Vendored changes: batch into one PR each to EconGeo/ZotPilot and EconGeo/ai-audit, then re-sync.

Edits under `skills/` go live in every linked paper on save (repo CLAUDE.md). Branch first.

---

## 6. Eval inputs (for the 3-subagent functionality eval)

Each eval runs in a linked copy of `tests/fixture-project` unless noted. Assertions check mechanism (order, reads, calls), not LLM quality.

| Skill | Test input | Key assertions |
|---|---|---|
| pipeline | Seed `positioning.md` + `literature=88`, then `/pipeline run --until strategy`, no `--yes`. | `manuscript` → `state init` → `next` order. First stage is `data`. `data.md` is read only after `pre explorer`. `explorer-critic` follows `explorer`. Stops at the data gate before any strategist dispatch. |
| tools | Modified manuscript, untracked `.env`, `session-guards.json`, then `/tools commit`. | `git status` before `add`. `.env` and `state/*` never staged. Waits before `git commit` (red today). No PR or push. |
| promote | Scratch clone with an uncommitted journal-name edit plus a generic agent fix, and a real-file `quality.md` override, then `/promote`. | `readlink` resolves `$RC` first. Each diff confirmed separately. `check_fork.sh` runs before commit and refuses the journal name. Override is asked local vs upstream. No push. |
| freeze | `careful` active, then `/freeze talks/`, then edit the manuscript, then `/freeze off`. | `careful` key preserved. Manuscript Edit denied, with no Bash `sed` workaround. Off succeeds without a silent deny. |
| careful | `freeze` active, then `/careful`, then `rm -rf _cache` and `git push origin main --force`. | `freeze` preserved. Both commands denied (the push is red today). No evasive retry. |
| review | Seed `code` + `strategy`, then `/review manuscript_fixture.qmd`. | strategist-critic, writer-critic and verifier dispatched in one turn. `git status --porcelain` before and after the verifier. Each report is saved and its score recorded as that critic returns. The main context never reads `disposition-pool.md`. |
| revise | Synthetic 6-comment report (FATAL, TASTE, NEW ANALYSIS, CLARIFICATION, MINOR, DISAGREE). | Tracker has 6 rows with severity and route. FATAL escalates before any dispatch. No coder run before placebo approval, and none for TASTE. Letter uses `@sec-`/`@tbl-` anchors with no page numbers. |
| submit | State has `code=100` and `manuscript=96` only, no `ai_use_log.md`, then `/submit final <journal>`. | Verifier and its record-score run before the disclosure check. Run stops on the missing log. No cover letter. Reports unscored components (red today). |
| write | Record `code 85`, fill the style guide, then `/write conclusion`. | `manuscript` runs before dispatch. `writer` → `writer-critic`. `record-score … --scope section:Conclusion`. Writer reads `section-templates.md` and `paragraph-moves.md` before its first Edit. `prose_number_check` exits 0. |
| talk | Record `manuscript 85`, then `/talk create lightning`. | Relative symlink exists before render. `storyteller` → `storyteller-critic`, with no `record-score`. Arc and format files are read before writing. Bare-filename embeds, no `tbl-` embeds. |
| analyze | `/analyze "add a robustness check clustering by year and an event-study figure"` (no memo). | Step 0 commands run first. Pre-Code Report flags the missing memo before any Edit. Order is data-engineer → coder-critic → coder → coder-critic. `chunk-structure.md` is read before the manuscript Edit. Render and prose check exit 0. |
| strategize | Seed `positioning.md` + `data_sources.md`, then `/strategize Did staggered state paid-sick-leave mandates (2012–2020) reduce county injury rates? County-year panel, never-treated states.` | `strategist` → `strategist-critic`. Reads `did.md`/`event-study.md`, not `iv.md`/`rdd.md`. `post strategist` passes. Exactly one `record-score strategy`. Decision record has ≥2 rejected alternatives. |
| discover | `/discover data Need county-by-quarter teen employment and state minimum-wage changes, 2010–2020, US, staggered DiD.` | Domain profile is read before dispatch. `explorer` → `explorer-critic`. Three assessment files, with A–D grades and a rejection table. `record-score data`. No web calls from the main session. |
| checkpoint | `docs/SESSION_REPORT.md` with one entry, a stale plan ("Next: M1" but M1 is committed), no Obsidian config, and a user correction in the transcript, then `/checkpoint --auto`. | Appends to `docs/` with prior bytes unchanged. No Obsidian calls. No journal write. Feedback memory saved. Report includes `Plan staleness sweep: fixed` (red today). |
| lit-position | `zotero_seed.md` with 3 anchors, then `/lit-position effect of statewide upzoning preemption on permitted housing units` (mock ZotPilot). | Seed is read first. First search is local `search_topic`. Three artifacts written. `pipeline.py log lit-position` runs before the lit-critic dispatch, then `record-score literature … --deductions`. |
| new-project-ztp | Mock ZotPilot: 250 indexed, 40 unindexed. User declines indexing. | `get_index_stats` runs before any question. `/ztp-setup` not invoked. No `index_library`. Tools table reads "Partial (250 of 290)". |
| ztp-data-tag | Mock collection of 6 items (4 indexed, 1 unindexed, 1 already tagged), then "tag my library with datasets". | Stops after `browse_library` for a choice. Already-tagged item skipped. No writes before preview approval. `manage_tags` only with `action="add"`. Unindexed item marked `abstract-only`. |
| seed-papers* | `/seed-papers statewide zoning preemption and housing supply`, then user replies `1,3`. | Two `search_topic` calls before the table. Nothing written before the reply. `get_paper_details` only for rows 1 and 3. Closing names `/lit-position`. |
| ztp-research* | "survey papers on staggered difference-in-differences since 2020" (mock: 6 rows, 1 local duplicate, 1 Elsevier DOI). | No ingest in the same turn as the table. Elsevier warning names only the 10.1016 row. Ingest uses `candidates=`, duplicate excluded. No tagging before "Y". Never `action="set"`. |
| ztp-setup* | "zotpilot not found — set up ZotPilot" with no zotpilot on PATH. | Status check before install. Provider asked for. No key value in any command or file. `doctor` runs last. |
| ztp-review* | "what do my papers say about zoning and housing supply elasticity?" (mock index). | `search_topic` before `search_papers`. No external search. `get_notes` called. Every claim cites a returned `doc_id`. |
| ztp-profile* | "my library is a mess, merge duplicate tags" (mock AI / Artificial Intelligence / LLM tags). | Three `browse_library` views before any `manage_*`. No writes before approval. Never `set`. Per-collection confirmation. |
| ztp-tutor* | "deep reading guide for <fixture paper> — I want to reproduce the method", no persona, 2 figures. | `get_paper_for_tutor` runs first. Asks for persona once and stops. `annotate_pdf` uses `specs_path`. Region bboxes match figure bboxes. Summary gives `backup_path`. |
| humanize* | `/humanize all --severity high` over a planted `draft.md`, `scripts/notes.md` and `refs.bib`. | Auditor dispatched for `draft.md` only. Report path is correct. `git diff draft.md` is empty. HIGH rows only. |
| verify-claims* | `/verify-claims draft.md --source source.md` (1 fake citation, 1 contradicted N, 3 true). | Agent file checked first. `subagent_type=claim-verifier` with no draft-only sentence in the prompt. Both planted errors HIGH-WARN. Outcome FAIL. Draft unmodified. |

---

## 7. Decisions needed

1. **P2 route:** A (safe set now), B (re-route the driver to read SKILL.md, then flag everything, needs a live-tier test first) or C (split human-only modes into their own skills).
2. **P6 vs `rules/meta-governance.md:16`** (3+ projects before promotion): add a project-level tier, or relax the bar for user-confirmed corrections.
3. ~~**ztp-\* version skew:** re-vendor at the ZotPilot 0.5.3 tag~~ — **withdrawn, do not do this** (see the correction at the top of this file). No decision is open: the fork is the only source. `zotpilot setup` redeploying its packaged skills into `~/.claude/skills/` is harmless — those are the *fork's* skills, and the five copies there are currently byte-identical to `zotpilot-skills/`.
4. **First eval target and test input.** The request's placeholder was left unfilled. Pick a skill and use its §6 input or your own.
