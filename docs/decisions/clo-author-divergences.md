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

### D-2 — Install / connection / shadowing safeguard — **GAP, and the priority finding**

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

**Reason for the current state:** unknown — the audit found no decision record choosing manual
invocation over automatic.

**Recorded on disk:** the *script* is documented (`README.md:207`, `CLAUDE.md:103`). **That it is
never automatically run is unrecorded**, and no rule, hook or skill states who is responsible for
running it.

---

### D-3 — `protect-files.sh`: wired in clo-author, shipped dead here — **GAP**

**clo-author:** `.claude/settings.json` wires it as the **first** `PreToolUse` hook on
`Edit|Write`. The script blocks edits to `settings.json`, `strategy-memo-*.md`,
`referee-report-*.md` and `quality-score-*.json` — i.e. config plus generated artifacts that an
agent must not quietly rewrite.

**research-claude:** Ships `hooks/protect-files.sh` and documents it in `hooks/README.md:35` as
*"`protect-files.sh` | PreToolUse | Blocks edits to protected paths"*. **`seeds/settings.json`
never names it** (`grep -c protect-files seeds/settings.json` → `0`), and that file's own
`$comment` states the rule: *"Hooks are linked into `.claude/hooks/` but fire only because they
are named here."* The hook therefore never fires in any project.

**Class:** **GAP** — a regression introduced by the port, not a decision.

**Does the problem still exist under Quarto?** Yes. The protected class is even more exposed now:
critic reports and `pipeline_state.json` are the pipeline's own evidence, and `/review` already
had to add a `git status --porcelain` check because *"a project gate restamped two committed
reports"* (`skills/review/SKILL.md`).

**Reason:** none found. The hooks README documents behaviour the shipped wiring does not deliver.

**Recorded on disk:** **unrecorded.** `hooks/README.md:35` asserts the opposite of the truth.

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

**Class:** INHERITED (values) with an unlitigated format change.

**Does the problem still exist?** Yes, unchanged — cross-language replication is format-agnostic.

**Reason:** unknown. `skills/review/config/` exists and holds only `scoring-rubrics.md`, so the
config directory was kept while this one config was prosified. A number in a table is read by an
LLM; a number in JSON can be asserted against.

**Recorded on disk:** **unrecorded.**

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

### D-17 — Two humanizers inherited from two upstreams, never litigated — **GAP**

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

**Class:** **DELIBERATE DIVERGENCE — ruled 2026-09-23, execution deferred.** (Was GAP — two
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

**This defers the item's own Gate** ("the two skills' trigger lists no longer overlap"): it cannot
close from inside research-claude today. Recorded here rather than marked done — the collision
described below is still live until the upstream rename lands and is synced.

**Does the problem still exist?** Yes, and the collision is worse than a duplicate. The two
overlap heavily in detection (AI vocabulary, em-dash overuse, tricolon abuse, hedge stacking, "not
only X but also Y", filler phrases, promotional framing) while disagreeing on thresholds — *"more
than 2 em dashes per page"* (`cleanup-patterns.md:13`) against *"more than 3 em-dashes per
paragraph"* (`humanize` category 3). And because `/humanize` sets
`disable-model-invocation: true` while `/write humanize` does not, the **wrong** one wins: a user
typing *"de-AI this draft"* — a phrase in `/humanize`'s own trigger list — is routed to the
rewriter that `/humanize` exists to argue against. A third copy exists in
`agents/writer-critic.md`, which scores *"AI PATTERNS FOUND"*.

**Reason:** none. The vendoring of ai-audit (2026-09-09) and the retention of clo-author's
`/write humanize` were separate decisions; neither considered the other.

**Recorded on disk:** **unrecorded as a decision.** Noted as a symptom at "Low" severity in
`docs/audits/2026-09-15_skill-best-practices-audit.md` §4 — *"`/write humanize` rewrites in place
while `/humanize` is detect-only by design"* — and not acted on. **Needs litigating: one of the two
must win, and the loser must say so in its own file.**

---

### D-18 — `ai-audit` installed but connected to nothing — **GAP**

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

**Reason:** none found. Vendoring solved *distribution* and stopped there.

**Recorded on disk:** **unrecorded.**

---

## G. Port fidelity

### D-19 — Harvested capability whose caller was never updated: `editor --variance`

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

## Summary

| Class | Entries |
|---|---|
| INHERITED | D-8 (values; format change unrecorded) |
| DELIBERATE DIVERGENCE | D-1, D-5, D-6, D-9, D-10 (weakly recorded), D-11, D-12, D-13, D-14, D-15, D-16 (fixed 2026-09-23), D-17 (ruled 2026-09-23, execution deferred to an upstream `EconGeo/ai-audit` rename) |
| OBSOLETE | D-4 (mechanism), D-7 |
| **GAP — defects** | **D-2, D-3, D-18, D-19 (partially corrected 2026-09-23 — see entry)** |

**Unrecorded reasons — the register's own finding:** D-2 (that `check_install.sh` never runs
automatically), D-3, D-8, D-16 (now recorded — see the entry above), D-17 (now recorded — see the
ruling above), D-18, D-19 (now recorded — see the entry above). Seven of nineteen divergences had
no reason recorded anywhere on disk before this file existed.

**The pattern worth carrying forward.** Five of the six GAPs share one shape: *a mechanism was
correctly retired or correctly introduced, and its **purpose** was never assigned a new owner.*
D-4 is the case that was eventually caught and fixed — but only after four wrong numbers reached a
manuscript that scored 100/100. D-2, D-3 and D-18 are the same shape, still open; D-19's false
enforcement claim is corrected but the underlying capability remains unreachable through `/review`.
When retiring, porting or vendoring anything, state the purpose separately from the mechanism and
name where the purpose now lives — and add an entry here.
