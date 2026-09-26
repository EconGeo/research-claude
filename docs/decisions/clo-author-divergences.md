# clo-author divergence register

**Purpose.** research-claude was forked from `hugosantanna/clo-author` on 2026-09-08 and rebuilt as
a Quarto-only pipeline. **It is legitimate for this pipeline to diverge from clo-author on any
decision.** What is not legitimate is diverging *silently*: a capability that quietly stopped
existing, or a safeguard whose purpose was never re-homed, is indistinguishable from an accident
six months later.

This file is the standing record. One entry per divergence. It outlives any single audit and is
**appended to whenever a new divergence surfaces** — including divergences introduced from here
on, not only those inherited from the 2026-09-08 fork.

**Established 2026-09-23** by the skill-inventory audit
(`docs/audits/2026-09-23_skill-inventory.md`). Entries D-1 … D-19 are that audit's seed set.

## Evidence base

Unlike the parity table in the audit report — which rested on
`docs/superpowers/specs/2026-09-08-quarto-native-research-pipeline-design.md` as a *record of*
clo-author — this register was written against **clo-author itself**, cloned from
`https://github.com/hugosantanna/clo-author.git` and checked out at **`d36c408`**, the exact
commit this repo's submodule was pinned to (recovered via
`git ls-tree bda2d1b submodules/clo-author`). Quotations below are from that tree. It was cloned
to a scratch directory, read, and not retained.

## Entry format

```
### D-n — <short title>
**clo-author:**   what it did, and the problem it was solving (quoted from its own files)
**research-claude:** what we do instead
**Class:** INHERITED | DELIBERATE DIVERGENCE | GAP | OBSOLETE
**Does the problem still exist under Quarto?**  yes / no / in a different form — and why
**Reason:**      why we chose differently
**Recorded on disk:** file:line, or **unrecorded**
```

**Classes.** `INHERITED` — same approach, carried over. `DELIBERATE DIVERGENCE` — different
approach, reasoned. `GAP` — clo-author solved a live problem we do not. `OBSOLETE` — the problem
was dissolved by the Quarto architecture.

**Any GAP is a defect** and is cross-listed in the audit report's prioritized findings.

---

## A. Architecture and installation

### D-1 — Distribution model: one repo vs shared tree + symlinks

**clo-author:** *Was* the project. `.claude/` held 138 tracked real files and **zero symlinks**;
there is no `apply.sh`, no `bootstrap-pipeline.sh`, and no installer anywhere in its history. The
pipeline and the paper lived in one repo, so "is the pipeline correctly installed" was not a
question that could be asked.

**research-claude:** One canonical tree; `apply.sh --link` creates one relative symlink per skill
directory, agent, rule and hook into each paper project.

**Class:** DELIBERATE DIVERGENCE

**Does the problem still exist under Quarto?** Unrelated to Quarto. The divergence answers a
problem clo-author's model *created*: six copies drifting apart. README: *"one project's `editor`
agent grew from 67 lines to 366 while every new project still scaffolded from 67."*

**Reason:** Copying is the drift engine; linking removes drift by construction.

**Recorded on disk:** `README.md` §"Why link instead of copy?"; `rules/shared-pipeline.md` (whole
file); `CLAUDE.md` §"Where things go".

---

### D-2 — Install / connection / shadowing safeguard — **CLOSED 2026-09-24** (was GAP, the priority finding)

**clo-author:** Had none, and **needed none.** With `.claude/` as real tracked files in the same
repo, there is no install step to verify, no link to dangle, and no shared item a local file can
shadow. A local copy of a rule *was* the rule.

**research-claude:** The symlink model creates four failure modes clo-author could not have: an
item never linked; a link resolving to nothing; a link pointing at a different checkout; and a
real file silently shadowing a canonical one. `scripts/check_install.sh` detects all four.

**Class:** **GAP** — not an inherited safeguard that was dropped, but a **new failure mode
introduced by D-1 whose detector was built and then wired to nothing automatic.**

**Does the problem still exist under Quarto?** Yes, and it is architecture-induced rather than
format-induced — it would exist identically in a LaTeX pipeline built on symlinks.

**Verified this session:** `check_install.sh` is named in exactly four places —
`README.md:207`, `CLAUDE.md:103` (both as manual instructions to a human),
`skills/promote/SKILL.md` Step 5, and two test files. **`seeds/settings.json` carries eight hook
entries and none of them invokes it**; its only `SessionStart` hook matches `compact|resume` and
runs `post-compact-restore.py`. So nothing automated ever runs it, and `/promote` is the sole
in-session caller — a skill invoked only when someone is already deliberately reconciling the
tree. The coordinator's framing ("runs only inside `/promote`") is close; the operative fact is
stronger: **no automated trigger exists at all.**

This is the mechanism behind the reported incident in which a project-local skill shadowed a
shared rule for three months and waived a real defect through two critic rounds. The detector
existed the whole time.

**Reason for the current state (as of 2026-09-23):** unknown — the audit found no decision record
choosing manual invocation over automatic.

**Re-homed 2026-09-24 (Phase 0 of `docs/plans/2026-09-23_pipeline-repair.md`, verified in Phase
4.1).** `hooks/install-check.py` runs `check_install.sh` at every `SessionStart` and is wired in
`seeds/settings.json`, so `check_install.sh`'s own required-hook derivation (`hooks-wired`) demands
it fleet-wide the moment it is seeded — the same mechanism that closed D-3 below. `tested:`
`./scripts/check_install.sh --all` reports `PASS [hooks-wired]` in all six linked repos, each of
which carries `install-check.py` in its own committed `.claude/settings.json`. The install/
connection/shadowing check now runs automatically on every session, not only inside `/promote`.

**Class:** now DELIBERATE DIVERGENCE — purpose **re-homed**, matching the D-4/D-11 pattern.

**Recorded on disk:** `hooks/install-check.py`'s own docstring states why it exists (quoted in
`hooks/README.md`); `seeds/settings.json`; this entry.

---

### D-3 — `protect-files.sh`: wired in clo-author, shipped dead here — **CLOSED 2026-09-24** (was GAP)

**clo-author:** `.claude/settings.json` wires it as the **first** `PreToolUse` hook on
`Edit|Write`. The script blocks edits to `settings.json`, `strategy-memo-*.md`,
`referee-report-*.md` and `quality-score-*.json` — i.e. config plus generated artifacts that an
agent must not quietly rewrite.

**research-claude:** Ships `hooks/protect-files.sh` and documents it in `hooks/README.md:35` as
*"`protect-files.sh` | PreToolUse | Blocks edits to protected paths"*. **`seeds/settings.json`
never names it** (`grep -c protect-files seeds/settings.json` → `0`), and that file's own
`$comment` states the rule: *"Hooks are linked into `.claude/hooks/` but fire only because they
are named here."* The hook therefore never fires in any project.

**Class:** was **GAP** — but not quite "a regression introduced by the port, not a decision," as
first written. A reason *does* exist on disk: `docs/superpowers/specs/2026-09-08-pipeline-repair-design.md`
has its own ruling numbered R-7, *"Wire `context-monitor.py` after the per-session fix;
`protect-files.sh` stays opt-in,"* executed in that plan's Task 7.5. The 2026-09-23 audits (this
entry, the skill-inventory audit, the overhaul-delivery audit) all missed it and called it
unrecorded, because `docs/decisions/2026-09-08_pipeline-repair-rulings.md` — a *different* document
from a *later* session — happens to have its own, unrelated R-7 in its own appendix (*"`coder-critic.md`
must retain `Correctness Layer` and `INV-23`"*), and one line in that later rulings doc (§6, "landed
today") cites "R-7" for the opt-in decision as if it were self-referential. It never was; the two
R-7s are a same-day numbering collision between two independent documents. Chasing the citation to
its actual source (the design spec, not the rulings appendix) is what surfaced this.

**Does the problem still exist under Quarto?** Yes, and the 2026-09-08 ruling's premise did not
survive contact with reality: by 2026-09-23, `/review` had already had to bolt on its own `git
status --porcelain` check because *"a project gate restamped two committed reports"* — the exact
failure `protect-files.sh` exists to prevent, happening under the "opt-in" default. Critic reports
and `pipeline_state.json` are the pipeline's own evidence, more exposed now than in clo-author, not
less.

**Reason:** the 2026-09-08 ruling had a reason (avoid a blanket default before any project had
opted in); it just stopped being the right call once a live incident showed the default insufficient,
and nothing revisited it for two weeks because nothing was wired to notice.

**Ruled 2026-09-24 (Phase 4.1):** the 2026-09-08 opt-in default is superseded. `protect-files.sh` is
now wired in `seeds/settings.json`'s `PreToolUse` (matcher `Edit|Write`) and in all six linked
repos' own `.claude/settings.json`. `PROTECTED_PATTERNS` was repointed from clo-author's inherited
LaTeX-era names (`strategy-memo-*.md`, `referee-report-*.md`, `quality-score-*.json`) to the actual
Quarto-era artifacts (`pipeline_state.json`, `*-critic_*.md`, `civilize_*_report.md`,
`verify_claims_*.md`, `desk_review.md`, `referee_domain.md`, `referee_methods.md`, `strategy_memo.md`).
Fixing this also surfaced a second, independent bug never caught because the hook was never
exercised: `[[ "$BASENAME" == "$PATTERN" ]]` quotes `$PATTERN`, which disables glob matching in
bash, so every wildcard pattern — including the original clo-author-inherited ones — silently never
matched anything. `tested:` `tests/test_protect_files.py` (8 cases, including a wildcard case that
fails on the pre-fix quoting). `check_install.sh --all`'s `hooks-wired` derives its required set
from `seeds/settings.json`, so it FAILed on all six repos the moment the hook joined the seed and
PASSed once each repo's `settings.json` was updated to match — the same derive-don't-hardcode
mechanism that closed D-2 above.

**Recorded on disk:** now — this entry; `hooks/protect-files.sh`'s own header comment; the correction
in `scripts/check_install.sh`'s `hooks-wired` comment block, which carried the same "R-7, opt-in"
claim into the checker itself and has been corrected alongside.

**Amended 2026-09-25 — strategy memos are timestamped, one file per round.** The Phase 4.1
repoint mapped clo-author's `strategy-memo-*.md` (per-round copies, never rewritten) onto the
fixed name `strategy_memo.md` that R-111 had chosen. Neither clo-author path was dated (its skill
wrote `strategy_memo_[topic].md`, its agent `strategy_memo.md`), and R-111 was a consistency fix
that never weighed dated against fixed. Protecting a file the strategist must rewrite every
strategist→critic round then blocked the revision loop in a live project, and a critic report
cited a memo that the next round would overwrite. **Ruled by the user:** the memo is
`quality_reports/strategy/<project>/strategy_memo_<YYYY-MM-DD_HHMM>.md` (local date and 24-hour
time; several rounds can fall on one day), a new file every round, the newest name current. The
registry glob is `strategy_memo_[0-9]*.md` — the digit class keeps clo-author-era
`strategy_memo_review*.md` files, still present in projects, from matching and from sorting as
"newest". `section` predicates gained `select: newest`, because `any` would let a complete earlier
memo mask a newer one missing a required section. `artifact-paths` lets a registry character class
admit a prose placeholder. The hook pattern becomes `strategy_memo_[0-9]*.md`, which restores the
clo-author intent: a memo is created once and never rewritten. `tested:` `tests/test_pipeline.py`
(newest-only; undated and review files are not memos), `tests/test_check_refs.py`,
`tests/test_registry_lib.py`.

---

## B. Numbers, traceability, and the registry

### D-4 — The results registry — the canonical "purpose not re-homed" case

**clo-author:** `results_summary.md` was **mandatory** after every analysis run —
`analyze/SKILL.md:59` *"Produce `results_summary.md` with all estimates, SEs, and key statistics
(MANDATORY)"*, `:150` *"Every analysis run MUST produce `results_summary.md`"*. Its stated purpose
is handoff: `:203` *"Mandatory results summary output for **writer handoff**"*, and the writer
reads `:104` *"key estimates with SEs and interpretation (from `results_summary.md`)"*. The
template carries point estimates, SEs, CIs, p-values, N, and the paper location of each. **The
problem it solved: the writer wrote prose from a file, and that file had to be the authoritative,
current record of every number, because the numbers lived in `.rds` objects and `.tex` exports the
writer could not see.**

**research-claude:** No registry. The writer reads live chunk objects in the same document, and
every prose number is an inline `` `r ` `` expression.

**Class:** OBSOLETE **for expressions** — with a GAP for typed literals that persisted until
`prose_number_check.py` shipped.

**Does the problem still exist under Quarto?** **In a different form, and this is the case the
register exists to make legible.** A render proves every inline expression *evaluated*; it proves
nothing about a number someone typed. README states it plainly: *"rendering proves every inline
expression evaluated. It says nothing about a number someone typed by hand."* The consequence is
on record: a manuscript scored 100/100 EXCELLENCE while carrying 24 hardcoded values, four
provably wrong, and a sentence stating the opposite sign of its own table. Retiring the registry
was right; its *purpose* — no stale or invented number reaches prose — was uncovered for as long
as nothing checked literals.

**Reason:** the registry's mechanism was obsolete; its purpose was not.

**Recorded on disk:** yes, now. `rules/quarto-empirical.md`; `README.md` §"The single-manuscript
pipeline"; `rules/content-invariants.md` INV-11; enforcement in `skills/tools/SKILL.md` Step 0
(blocking) and `agents/verifier.md` check 4b. `scripts/SHIPPED` lists `prose_number_check.py`, so
projects receive it.

**Standing lesson for future entries:** when retiring machinery, name the *purpose* separately
from the *mechanism*, and say where the purpose now lives. Most of this register's GAPs are cases
where that was not done.

---

### D-5 — INV-22 claim-source map → Claim–Evidence Table

**clo-author:** `content-invariants.md` INV-22 — *"Every numerical claim in the manuscript must
have an entry in the claim-source map (`quality_reports/claim_source_map_{project}.md`) traceable
to a specific script line and output file."* The **writer** maintained it by hand
(`write/templates/claim-source-map.md`), and the **writer-critic** checked it (INV-1..INV-13 and
INV-22).

**research-claude:** INV-22 retired. `skills/review/templates/claim-evidence-table.md` is built
*from the manuscript by the critic* at every review.

**Class:** DELIBERATE DIVERGENCE

**Does the problem still exist under Quarto?** Split in two. Mechanical traceability is dissolved
(an inline expression *is* its own provenance). **Interpretive** traceability — does this sentence
say what the table says — is untouched by architecture and needed a home.

**Reason:** a hand-maintained map is a second copy that drifts, and the writer maintaining its own
audit trail violates separation of powers (`rules/agents.md` §2). Building it from the manuscript,
by the critic, removes both problems.

**Recorded on disk:** `skills/review/templates/claim-evidence-table.md` header — *"It replaces the
retired hand-maintained claim-source map: the table is built from the manuscript by the critic,
not maintained by the writer. INV-11 stays mechanical (`prose_number_check.py`); this table is the
interpretation check."* Also POGM4's `CLAUDE.md` (INV-22 discharged by architecture). **This is the
best-documented divergence in the register and is the model for the format.**

---

### D-6 — INV-11 redefined from a human check to a mechanical one

**clo-author:** INV-11 — *"Numbers in text match the tables and figures exactly. No rounding
discrepancies, no stale values."* A proposition a reviewer asserts.

**research-claude:** INV-11 — every prose number is an inline `` `r ` `` expression. A predicate a
script decides.

**Class:** DELIBERATE DIVERGENCE

**Does the problem still exist?** Yes; the divergence is in who checks it. clo-author's phrasing
cannot fail a build, which is how it passed while wrong.

**Reason:** an invariant no command can evaluate is a hope.

**Recorded on disk:** `rules/content-invariants.md`; `rules/quarto-empirical.md`.

---

### D-7 — INV-13: bare `tabular` exports → chunk options

**clo-author:** INV-13 — *"R/Python/Julia scripts export bare `tabular` environments — no
`\begin{table}`, `\caption{}`, or notes. The paper's `main.tex` wraps them."*

**research-claude:** Captions are `#| tbl-cap:`; `quarto_structure_check.py` fails a caption set in
R.

**Class:** OBSOLETE — the wrapping layer it coordinated no longer exists.

**Recorded on disk:** `rules/content-invariants.md`; `skills/tools/SKILL.md` Step 0.

---

### D-8 — Replication tolerances: machine-readable config → prose table

**clo-author:** `skills/analyze/config/replication-tolerances.json` — a JSON config an agent loads,
with `relative_tolerance`, `absolute_tolerance`, a `significance_boundary_flag`, and a
`common_divergence_sources` list.

**research-claude:** `skills/review/templates/replication-comparison.md`, a markdown table. The
**values are identical** — point estimates relative `1e-6` / absolute `1e-10`, SEs relative `1e-4`,
p-values relative `0.01` with 0.10/0.05/0.01 boundaries flagged regardless, sample sizes exact.

**Class:** INHERITED (values); DELIBERATE DIVERGENCE (format) — litigated 2026-09-24, see below.

**Does the problem still exist?** Yes, unchanged — cross-language replication is format-agnostic.

**Reason (as of 2026-09-23):** unknown. `skills/review/config/` exists and holds only
`scoring-rubrics.md`, so the config directory was kept while this one config was prosified. A
number in a table is read by an LLM; a number in JSON can be asserted against.

**Ruled 2026-09-24 (Phase 4.2):** keep the prose table — not OBSOLETE (the tolerances are real and
still needed) and not a GAP requiring new machinery. The distinction from D-6/INV-11 is volume and
kind of judgment, not principle: INV-11 needed a mechanical gate because a manuscript carries
hundreds of individual prose numbers, cheap to state and expensive to eyeball one-by-one, and
"matches the table" is a fact, not a judgment call. `replication-comparison.md` carries five stable
threshold values, read once per `/review --replicate`, where the actual work — deciding whether an
observed point-estimate or SE divergence is *material* given `common_divergence_sources` (solver
tolerance, RNG seed, library version) — is an interpretive judgment the critic is already making,
not a comparison a script can finish alone. Converting to JSON would let a script assert the five
thresholds exist and are well-formed; it would not remove the critic from the loop, so it buys
less than INV-11's conversion did. **This is a live scope boundary, not an oversight** — record it
as such if it is ever revisited, rather than re-opening the question from zero.

**Recorded on disk:** now — this entry.

---

## C. Orchestration and workflow

### D-9 — Orchestrator and phase graph → declarative registry

**clo-author:** `agents/orchestrator.md` plus `rules/workflow.md` §2, a hardcoded phase graph.

**research-claude:** No orchestrator. `rules/registry.yaml` declares `REQUIRES`/`PRODUCES`,
`scripts/pipeline.py` evaluates them, `/pipeline` loops. `rules/agents.md` §4: *"Phases activate by
`REQUIRES`, never by sequence."*

**Class:** DELIBERATE DIVERGENCE

**Does the problem still exist?** Yes — ordering must still be decided; the divergence is that it
is now derived rather than written down twice.

**Reason:** the orchestrator was *structurally unreachable* (only `/new-project` dispatched it, and
`apply.sh` refused to install `/new-project`), and its graph serialized the coder↔writer loop that
the research journal shows actually happens.

**Recorded on disk:** `docs/decisions/2026-09-08_cut-the-orchestration-graph.md`; design spec D1;
`rules/agents.md` §4.

---

### D-10 — Plan-first protocol and requirements-spec — dropped from the shipped tree

**clo-author:** `rules/workflow.md` §1, a mandatory 9-step plan-first protocol for any non-trivial
task — enter plan mode, read `MEMORY.md` `[LEARN]` entries, write a requirements spec marking each
requirement MUST/SHOULD/MAY and CLEAR/ASSUMED/BLOCKED, save the plan to
`quality_reports/plans/YYYY-MM-DD_*.md`, get approval, then implement. Stated benefit: *"Catches
ambiguity BEFORE planning. Reduces mid-plan pivots by 30-50%."*

**research-claude:** No `rules/workflow.md`; no plan-first rule ships. The design spec's C-list
retired `requirements-spec` as *"superseded by `superpowers:brainstorming`"*.

**Class:** DELIBERATE DIVERGENCE, **weakly recorded**

**Does the problem still exist?** Yes. Ambiguous research tasks are the norm. The replacement is a
*third-party skill the pipeline does not ship, declare or depend on* — so a coauthor who bootstraps
`research-claude` alone gets neither the rule nor the replacement.

**Reason:** avoid duplicating a general-purpose capability inside a domain pipeline.

**Recorded on disk:** only in `docs/superpowers/specs/2026-09-08-quarto-native-research-pipeline-design.md`
(C-list, one clause). **Nothing in the shipped tree** (`rules/`, `skills/`, `README.md`,
`CLAUDE.md`) mentions plan-first, `quality_reports/plans/`, or `superpowers:brainstorming` — yet
`skills/checkpoint/SKILL.md` Step 1 still scans `quality_reports/plans/` and
`rules/session-handoff.md` R1 makes a plan staleness sweep **mandatory at every checkpoint**. The
pipeline consumes plans it no longer tells anyone to write. Individual projects re-added the rule
locally (POGM4's `CLAUDE.md`: *"Plan first — enter plan mode before non-trivial tasks; save plans
to `quality_reports/plans/`"*), which is drift of exactly the kind D-1 exists to prevent.

---

### D-11 — HTML research dashboard → pipeline state file

**clo-author:** `rules/html-dashboard.md` plus a `/dashboard` skill generating
`research_overview.html`, *"regenerated after every pipeline-related interaction"* — a single
scrollable page tracking full pipeline state.

**research-claude:** Retired (ruling R-4). The purpose is served by
`quality_reports/pipeline_state.json` plus `pipeline.py status` / `next`, which print one line per
component with CLOSED / OPEN / READY / BLOCKED / SKIPPED / OPTIONAL / PENDING.

**Class:** DELIBERATE DIVERGENCE — purpose **re-homed**, not dropped.

**Does the problem still exist?** Yes: "where is this project?" is a real question. It is now
answered in the terminal from committed state rather than by a regenerated HTML artifact.

**Reason:** a regenerated HTML file is a second copy of state that can disagree with the state
file, and it is a build step on every interaction.

**Recorded on disk:** `docs/decisions/2026-09-08_pipeline-repair-rulings.md` (R-4);
`rules/lifecycle.md` §"Where to start". Worth noting the succession explicitly in the rulings, as
D-4 and D-5 do.

---

### D-12 — `new-project` skill + `quality-gates.json` → rule + bridge skill

**clo-author:** `skills/new-project/` with `config/quality-gates.json` (machine-readable
thresholds).

**research-claude:** `root-skills/` removed 2026-09-08; scaffolding is `rules/quarto-empirical.md`
plus `skills/new-project-ztp/`; thresholds live in `rules/quality.md` and `rules/registry.yaml`,
with `check_fork.sh`'s `weights-sum` failing if the two disagree.

**Class:** DELIBERATE DIVERGENCE — and an improvement: the thresholds are now cross-checked.

**Recorded on disk:** `CLAUDE.md` §"Where things go";
`docs/decisions/2026-09-08_cut-the-orchestration-graph.md`.

---

## D. Literature

### D-13 — `librarian` agent → `/lit-position` skill + `lit-critic` agent

**clo-author:** `agents/librarian.md` and `agents/librarian-critic.md`, WebSearch-first, with
restricted tools and no MCP access — so it could not query a local library at all.

**research-claude:** Both agents deleted. `skills/lit-position/` runs in the main session with
ZotPilot access; `agents/lit-critic.md` is a real paired critic holding `mcpServers: [zotpilot]`
and its own six-category rubric; `rules/literature-search-order.md` makes local-first
non-negotiable.

**Class:** DELIBERATE DIVERGENCE — **stronger than the spec asked for.** Spec item E proposed only
a *self-check* against librarian-critic's six categories; what shipped is an independent scored
critic with a registry component and weight.

**Does the problem still exist?** Yes, inverted: with a 3,270-item indexed library, searching the
web first is the defect.

**Reason:** *"`librarian.md` is WebSearch-first, contradicting `literature-search-order.md`"*
(spec D3).

**Recorded on disk:** design spec D3 and E; `docs/decisions/2026-09-08_d3-addendum-lit-critic.md`;
`rules/literature-search-order.md`.

---

## E. Output format

### D-14 — LaTeX multi-file → single Quarto manuscript

**clo-author:** `paper/main.tex` + `paper/sections/*.tex` + `scripts/R/` exports, built with
`latexmk`; `write/SKILL.md:62` saves prose to `paper/sections/[section].tex`.

**research-claude:** One `manuscript_<project>.qmd`; `quarto render` is the only build.

**Class:** DELIBERATE DIVERGENCE — the fork's founding decision.

**Recorded on disk:** extensively — `rules/quarto-empirical.md`, `README.md`, the design spec.
`pipeline-precedence.md` was deleted because *"there is nothing left to take precedence over."*

---

### D-15 — Beamer slides dropped; RevealJS retained

**clo-author:** `storyteller` shipped both a Beamer scaffold and a Quarto one.

**research-claude:** `beamer-scaffold.tex` dropped; `skills/talk/templates/quarto-scaffold.qmd`
retained; `/talk` produces RevealJS.

**Class:** DELIBERATE DIVERGENCE — **owner-confirmed, not a defect.**

**Recorded on disk:** design spec Work item A (*"Quarto-only: drop `beamer-scaffold.tex`, keep
`quarto-scaffold.qmd`"*).

---

### D-16 — `kableExtra` guidance not carried through the format change — **GAP**

**clo-author:** LaTeX-first, so recommending `kableExtra` for tables was **correct**.

**research-claude:** Word is a first-class output. `rules/quarto-word.md:49` — *"`kableExtra` emits
LaTeX and produces garbage in Word — use **flextable**"* — and `:169` deducts −5 for it. But
`agents/data-engineer.md:92` still carries the inherited, unqualified line:
`| Tables | gt, kableExtra, modelsummary |`, with **flextable absent entirely**.

**Class:** **DELIBERATE DIVERGENCE** — **fixed 2026-09-23 (Phase 2.5).** (Was GAP — an inherited
instruction the format change invalidated and the port did not reconcile; the agent was told to
do the thing its own paired critic deducts for.)

**Did the problem still exist?** Yes until fixed: the *guidance* was correct for PDF and wrong for
Word; every other site already qualified it (`chunk-structure.md:71`, `quarto-pdf.md`,
`coding-standards-r.md`). This agent file was the sole outlier.

**Recorded on disk:** now — `agents/data-engineer.md:92`'s table row is qualified by format
(PDF: `kableExtra`; Word: `flextable`, pointing at `rules/quarto-word.md`), matching every other
site.

---

## F. Prose quality

### D-17 — Two humanizers inherited from two upstreams, never litigated — **CLOSED 2026-09-24** (was GAP)

**clo-author:** `/write humanize` — and the intent is inherited **verbatim**. clo-author's
`write/SKILL.md:137-141`: *"### `/write humanize [file]` — Cleanup Pass Only … **Agent:** Writer
(cleanup mode) … **Output:** Edited file with AI patterns removed"*. Its description line 3 reads
*"Replaces /draft-paper and /humanizer"* — the same clause research-claude's `/write` carries
today. clo-author shipped a **rewriter**, and only a rewriter.

**research-claude:** Ships **both**. `/write humanize` (inherited from clo-author, unchanged —
*"Output: Edited file with AI patterns removed"*) **and** `ai-audit/skills/humanize` (vendored from
`EconGeo/ai-audit`), whose stated design principle is the opposite: *"**Not a rewriter.** No
`--rewrite` mode. Auto-rewriting AI tells degrades prose quality … the author preserves voice by
editing manually."*

**Class:** **DELIBERATE DIVERGENCE — ruled 2026-09-23, executed 2026-09-24.** (Was GAP — two
upstreams, two answers, no decision — until litigated below.)

**Ruling (2026-09-23), Phase 2.4 of `docs/plans/2026-09-23_pipeline-repair.md`:** `/write humanize`
(clo-author's rewriter) is the pipeline's humanizer. The "cross-vendor research" `/humanize` cites
for its detect-only design was checked before ruling: `ai-audit/skills/humanize/SKILL.md`'s own
text is *"Cross-vendor research (Cursor / Aider community findings)"* — unattributed community
observation from two AI coding tools' user bases, no paper, no author, no URL. Not a citation
strong enough to override keeping the inherited, working rewriter.

`/humanize` is **not retired** — the author wants it available under a different name for
occasional detect-only use, distinct from `/write humanize`'s always-rewrite default. Because
`ai-audit/` is vendored verbatim and never edited in place here (`CLAUDE.md` §"Where things go"),
the rename happens **upstream, in `EconGeo/ai-audit`**, not as a local edit or bridge skill — the
author will rename `skills/humanize` there and this repo picks it up on the next
`scripts/sync-ai-audit.sh`.

**Gate met 2026-09-24** (`c737ac6`): upstream `EconGeo/ai-audit` PR #2 renamed the skill and agent
to `/civilize`/`civilize-auditor` (pinned commit `a99c7a75`), synced via `scripts/sync-ai-audit.sh`.
`tested:` a full-repo grep for `humanize` outside `docs/` now hits only `skills/write/SKILL.md`
(the pipeline's own `/write humanize` mode) and `ai-audit/VENDORED.md` (a provenance note);
`ai-audit/` itself carries no `humanize` string anywhere.

**Did the problem still exist, before the rename?** Yes, and the collision was worse than a
duplicate. The two overlapped heavily in detection (AI vocabulary, em-dash overuse, tricolon
abuse, hedge stacking, "not only X but also Y", filler phrases, promotional framing) while
disagreeing on thresholds — *"more than 2 em dashes per page"* (`cleanup-patterns.md:13`) against
*"more than 3 em-dashes per paragraph"* (`humanize` category 3, now `/civilize`). And because
`/humanize` set `disable-model-invocation: true` while `/write humanize` did not, the **wrong** one
won: a user typing *"de-AI this draft"* — a phrase in `/humanize`'s own trigger list — routed to
the rewriter `/humanize` existed to argue against.

**Does it still exist, after the rename?** No natural-language phrase auto-routes to both any
more: `/civilize`'s description still lists "de-AI this draft" as a trigger phrase, but it carries
`disable-model-invocation: true` and that phrase does not appear in `/write`'s description, so the
ambiguity that remains is a user *meaning* either by that phrase — the intended behavior per this
ruling (`/write humanize`'s auto-rewrite is the default; `/civilize` is manual detect-only). A
third copy of AI-pattern detection exists in `agents/writer-critic.md`, which scores *"AI PATTERNS
FOUND"* — unchanged by this ruling, since it is the paired critic's own scoring category, not a
user-facing dispatch route, and out of this entry's scope.

**Reason:** the vendoring of ai-audit (2026-09-09) and the retention of clo-author's `/write
humanize` were separate decisions; neither considered the other, until Phase 2.4 of
`docs/plans/2026-09-23_pipeline-repair.md` litigated them on 2026-09-23. The ruling itself: keep
`/write humanize` (clo-author's rewriter, inherited and working) as the default; keep `/civilize`
available under its own name for occasional manual detect-only use, because the "cross-vendor
research" `/humanize` cited for its detect-only design turned out to be unattributed Cursor/Aider
community observation, not a study — not strong enough to override the inherited, working
rewriter, but not a reason to delete a capability the author wants kept.

**Recorded on disk:** now — this entry; `docs/plans/2026-09-23_pipeline-repair.md` Phase 2.4;
`ai-audit/VENDORED.md`'s provenance note on the upstream rename. Previously noted only as a
symptom, not litigated, at "Low" severity in `docs/audits/2026-09-15_skill-best-practices-audit.md`
§4.

---

### D-18 — `ai-audit` installed but connected to nothing — **CLOSED 2026-09-24** (was GAP)

**clo-author:** Not applicable — ai-audit was never clo-author's. This is a divergence from the
*fork's own stated intent*, recorded here because the register is the place where intent is
litigated.

**research-claude:** `README.md:28` presents `/humanize` and `/verify-claims` as part of what the
pipeline provides, and `README.md:542` lists them in the Step 9 verification checklist. But they
are referenced **only** in `README.md`. `rules/registry.yaml` has no entry for `claim-verifier` or
`humanize-auditor`, no component they score, no weight. No `/pipeline` stage and no `/review` route
reaches either.

**Class:** **GAP**

**Does the problem still exist?** Yes, sharply. `/submit final` runs review → replication audit →
AI-disclosure audit → score gate → coverage check. **Citation existence in the world is checked by
nothing in that chain.** `agents/verifier.md` check 3 confirms only that a `@key` resolves in
`references.bib` — that the key is present, not that the paper is real. A manuscript can pass the
≥95 submission gate having never been checked for a fabricated reference. Given that the pipeline's
own literature skills *ingest* papers and *draft* citations, this is the largest functional hole
found.

Compounding it: `skills/promote/SKILL.md` Step 2's pathspec is
`-- agents skills rules references hooks templates seeds scripts` — **`ai-audit/` is not in it** —
while `scripts/sync-ai-audit.sh` `rm -rf`s that tree. An improvement made to `/humanize` through a
project symlink is therefore destroyed on the next sync, silently. `/promote` warns about this for
one tree only: *"Does not edit anything under `zotpilot-skills/`, which is vendored verbatim."*
`ai-audit/` gets no equivalent warning anywhere.

**Reason (as of 2026-09-23):** none found. Vendoring solved *distribution* and stopped there.

**Re-homed 2026-09-23–24, across Phase 3 of `docs/plans/2026-09-23_pipeline-repair.md`** (landed
before this register entry was updated to say so):
- **Reachability:** Phase 3.1 gates `/submit final` on a recorded `/verify-claims` result
  (`pipeline.py state record-verify-claims`; `score --gate submission` FAILs without one). Phase
  3.4 registers `claim-verifier` and `civilize-auditor` in `rules/registry.yaml` (`role:
  infrastructure`) and makes `registry_check()` scan `ai-audit/agents/*.md`, not just `agents/*.md`,
  so `registry check` counts them instead of silently skipping the whole tree.
- **Vendored-tree protection:** Phase 3.2 makes `/promote`'s Step 2.5 warn for `ai-audit/` the same
  way it already warned for `zotpilot-skills/`, and `check_refs.py`'s `promote-vendor-warn`
  criterion (wired into `check_fork.sh`) FAILs if `skills/promote/SKILL.md` ever stops naming both.

**Does the problem still exist?** No longer sharply — `/verify-claims` is now a real, enforced gate
on the one path (`/submit final`) that certifies a manuscript ready to send. `/civilize` remains
detect-only and un-gated by design (ruling D-17, 2.4): occasional, manual use, never mandatory —
that is a scope decision, not a residual instance of this GAP.

**Recorded on disk:** now — this entry; `rules/registry.yaml`'s `claim-verifier`/`civilize-auditor`
entries; `skills/submit/SKILL.md` step 2.6; `skills/promote/SKILL.md` step 2.5;
`scripts/check_refs.py`'s `promote-vendor-warn`.

---

## G. Port fidelity

### D-19 — Harvested capability whose caller was never updated: `editor --variance` — **CLOSED 2026-09-24** (was GAP)

**clo-author:** `editor` at 67 lines, without variance mode.

**research-claude:** `agents/editor.md` (369 lines, harvested from POGM4) implements
`--variance N`, N ∈ {3,4,5}, and at `:124` states *"`--variance` cannot combine with `--stress` …
The `/review --peer` skill enforces this."* **`skills/review/SKILL.md` has no `--variance` flag**;
its full option list is `--peer`, `--r2`, `--stress`, `--methods`, `--theory`, `--proofread`,
`--code`, `--replicate`, `--all`.

**Class:** **GAP** — the capability landed, its entry point did not.

**Does the problem still exist?** The capability is real and useful (estimating referee variance
rather than enforcing diversity) but reachable only by a user who has read `editor.md`. The
conflict rule it delegates was enforced by nobody — **corrected 2026-09-23 (Phase 2.5):**
`editor.md:124` no longer claims `/review --peer` enforces a conflict rule that has no dispatch
path to run in. Checked directly against clo-author at the pinned `d36c408` commit before
correcting: clo-author's `editor` is fixed at exactly two referees with no variance mode at all,
so this is not a capability that regressed in the port — it is net-new work (from POGM4) whose
referee-3-through-N agent identity (the registry has only two specialized referee agents,
`domain-referee` and `methods-referee`, never a generic disposition-driven one) was never
resolved anywhere, including in the source it was harvested from. **Still unreachable through
`/review`** — the honest correction records that plainly rather than inventing a resolution to an
open design question.

**Recorded on disk:** now — this entry, and `editor.md:124` itself. Previously unrecorded; the
design spec lists `--variance` among the capabilities `editor` *brings*, with no note that no
skill exposes it.

**Ruled 2026-09-24 (Phase 4.1):** re-homing this the way D-4/D-2/D-3 were — building the missing
gate — is not the right move here, because there is no missing *check*; there is a missing
*design decision* (which agent identity referees 3-through-N should use), and the user was
consulted directly rather than the plan guessing. **User decision (2026-09-24, recorded at Phase
2.5):** do not build variance-mode dispatch now — a third *named, specialized* referee agent is of
more interest than N-way disposition sampling, and that is a future design task, not a connectivity
fix. **Class, finalized:** DELIBERATE DIVERGENCE (scope boundary, user-ruled) — not OBSOLETE (the
capability is real and still wanted) and not an open GAP (the false enforcement claim that made it
look reachable is already corrected). `editor.md:124` no longer overclaims; `/review --variance`
remains a documented future capability, not a broken promise.

**Update 2026-09-25:** the "third named, specialized referee" interest was resolved without a
third agent — see D-20. N-way variance sampling stays unwired, as ruled above.

**Related port artifacts** — same shape, **fixed 2026-09-23 (Phase 2.5)**, since each was a
reconciliation bug rather than a divergence in intent:
`skills/analyze/templates/paper-to-code-map.md:36`'s naming rule now names `treated` (matching
`chunk-structure.md:19,54,55`'s worked example) instead of forbidding it, and no longer
self-contradicts by both endorsing and forbidding `treat` in the same sentence;
`agents/data-engineer.md:40` now points at `figure-standards.md`'s `base_size = 11` instead of
asserting `base_size >= 14`; `agents/data-engineer.md:92`'s table package row now qualifies
`kableExtra` to PDF and names `flextable` for Word (matching `rules/quarto-word.md`); and
`skills/talk/SKILL.md`'s inline format-constraints and critic-category tables — which disagreed
with `templates/format-constraints.md` and `review/templates/talk-review-6-categories.md` on
every row, and which the actually-dispatched agent files (`storyteller.md`,
`storyteller-critic.md`) never read in the first place — are deleted in favour of the one
canonical file each, closing the same class of drift for good rather than resyncing two copies
that will drift again.

---

## H. Review design

### D-20 — Rival explanations: a required domain-referee check, not a third referee

**clo-author:** two referees, `domain-referee` and `methods-referee`. Alternative explanations
appear only inside two disposition blurbs — SKEPTIC ("What's the strongest alternative
explanation?") and STRUCTURAL ("Are alternative mechanisms ruled out?") — so whether a review
names a paper's rivals depends on which two dispositions the editor draws from the journal's
pool weights.

**research-claude:** `agents/domain-referee.md` § "Rival explanations (REQUIRED, before
scoring)". Every domain report, whatever its disposition, names 2–3 rival explanations from
the abstract and introduction *before* evaluating the paper, states each one's distinguishing
prediction, and grades it RULED OUT / PARTIAL / NOT ADDRESSED against the manuscript. An open
plausible rival is a MAJOR concern under Dimension 3. `agents/editor.md` Phase 3 classifies
open rivals as ADDRESSABLE by default and surfaces a methods-referee report that contradicts
one. Formal-theory papers are exempt.

**Class:** DELIBERATE DIVERGENCE.

**Does the problem still exist under Quarto?** Yes — it is a review-design problem, independent
of format. The motivating case is a human referee at a real-estate journal who asked for data
ruling out location-specific demand and supply confounders in both the treated and comparison
markets: a rival-explanation ask no required check in either referee would have forced.

**Reason (user-ruled, 2026-09-25):** three alternatives were weighed. A separate third referee
agent generates rivals most adversarially but needs a third dispatch and a third report slot in
the editor's synthesis — the same unresolved agent-identity question that stalled D-19.
Guaranteeing one SKEPTIC draw overrides the journal pool weights that calibrate the review, and
a SKEPTIC only emphasises rivals rather than enumerating them. Putting the check on the methods
referee places it wrong: the methods referee asks whether the design removes a threat, the
rival-explanation question is what the result means. Ordering the check *before* evaluation
buys most of a separate reviewer's independence at no extra dispatch; if live runs show a
weak table, a third agent remains available.

**Recorded on disk:** this entry; `agents/domain-referee.md` (the section, the report-format
table, R&R item 6, Dimension 3's description); `agents/editor.md` Phase 3 ("Rival
explanations").

**Companion change, same day — three reduced-form sanity checks in `agents/methods-referee.md`.**
The same human report's remaining robustness asks — autocorrelation-robust standard errors on a
short time series, the result's sensitivity to the treatment date, and a test of the single
comparison market against a synthetic control — were each reachable only through a peeve draw
or the Robustness dimension's discretion. They are now the **Time-series inference**, **Timing**
and **Comparison-group** checks, blockers like the other five, each conditional on the design
it applies to (few units observed repeatedly; a dated treatment; a single or hand-picked
comparison). clo-author's reduced-form list stops at sign, magnitude, dynamics, clustering and
sample.

---

## Summary

**Updated 2026-09-24 (Phase 4 of `docs/plans/2026-09-23_pipeline-repair.md`).** D-2, D-3, D-18 and
D-19 — every entry the audits classed GAP — are re-homed and closed, and the register's own
"unrecorded reason" finding is closed out to a single remaining, deliberate scope boundary (D-8).
Class changes made today are noted inline below; each entry above carries the reasoning and the
gate evidence.

| Class | Entries |
|---|---|
| INHERITED | D-8 (values) |
| DELIBERATE DIVERGENCE | D-1, D-2 (re-homed 2026-09-24), D-3 (re-homed 2026-09-24), D-5, D-6, D-8 (format, litigated 2026-09-24), D-9, D-10 (weakly recorded), D-11, D-12, D-13, D-14, D-15, D-16 (fixed 2026-09-23), D-17 (ruled 2026-09-23, executed 2026-09-24), D-18 (re-homed 2026-09-23–24), D-19 (ruled 2026-09-24 — scope boundary) |
| OBSOLETE | D-4 (mechanism), D-7 |
| **GAP — defects** | **none open** |

**Unrecorded reasons — closed out 2026-09-24.** The register's own 2026-09-23 finding was that
seven of nineteen divergences (D-2, D-3, D-8, D-16, D-17, D-18, D-19) had no reason recorded
anywhere on disk. D-16, D-17 and D-19 already carried recorded reasons by the time this line was
first written; D-2, D-3 and D-18 are re-homed above with reasons and gate evidence; D-8 is the one
genuinely new ruling made today (Phase 4.2), because no prior decision existed anywhere to recover
— keep the prose table, a documented scope boundary rather than an oversight. **Zero remain
unrecorded.**

**The pattern this register exists to carry forward.** Four of the five GAPs shared one shape: *a
mechanism was correctly retired or correctly introduced, and its **purpose** was never assigned a
new owner.* D-4 is the case that was eventually caught and fixed — but only after four wrong
numbers reached a manuscript that scored 100/100. D-2 (install-check.py wired at `SessionStart`),
D-3 (protect-files.sh wired by default, its patterns repointed at Quarto-era artifacts) and D-18
(`/verify-claims` gated on `/submit final`, `ai-audit/` protected in `/promote`) closed the same
way: name what reaches the mechanism, and make the required-set check *derive* from the seed
rather than trust a hardcoded list, so a newly seeded requirement is demanded everywhere the moment
it is seeded. D-19 was the one exception in this set — not a missing check but a missing design
decision, closed by asking the user rather than guessing. When retiring, porting or vendoring
anything, state the purpose separately from the mechanism and name where the purpose now lives —
and add an entry here.
