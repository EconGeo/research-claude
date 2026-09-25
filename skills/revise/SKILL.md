---
name: revise
description: R&R cycle — classify referee comments and route to appropriate agents. Replaces the old respond-to-referee command.
argument-hint: "[referee-report file path] [paper path (optional)] [--yes]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent
---

# Revise

Structure point-by-point referee responses with classification, agent routing per revision protocol, and diplomatic drafting.

**Input:** `$ARGUMENTS` — path to referee report file(s), optionally followed by paper path.

---

## Workflow

### Step 1: Parse Inputs
1. Read referee report(s) from `$ARGUMENTS`
2. Resolve the manuscript (`python3 .claude/scripts/pipeline.py manuscript`, or the specified path)
3. Read the revision protocol (`.claude/rules/revision.md`) and the known failure points in
   `.claude/skills/revise/gotchas.md`
4. **List** the manuscript's `#| label:` lines, `#` headings and the setup-chunk naming map (a
   grep, not a read) to know what analyses already exist; the writer or coder dispatched in
   Step 5 reads the sections it revises. **Do not Read the manuscript in this session** — not
   in full and not to check whether a referee's premise holds. Checking a FATAL premise is the
   re-estimation Step 2 escalates to the user, not something this step does first

### Step 2: Classify severity, then route

Every referee comment gets both a severity and a route. Severity first — it
decides whether the paper survives; the route only decides who does the work.

| Severity | Meaning | Consequence |
|---|---|---|
| **FATAL** | The finding, if correct, invalidates a headline claim | Stop. Re-estimate before drafting any response. Escalate to the user. |
| **ADDRESSABLE** | Real, fixable within the current design | Route normally (table below). |
| **TASTE** | The referee would have written a different paper | Draft a diplomatic disagreement; never silently comply. |

Classify on the comment **as written** — FATAL means "invalidates a headline claim *if
correct*", so the class does not wait on verifying the referee; the listing from Step 1.4 is
all the manuscript context classification needs.

A TASTE comment answered with new analysis wastes a revision cycle. A FATAL
comment answered with prose is how papers get rejected on the second round.

Show the classification table and **wait** for the user to confirm or re-class rows before
routing — a mis-classed FATAL is the expensive mistake. For every FATAL, **Option gate**
(`.claude/rules/option-gates.md`): at least 5 paths — *re-estimate*, *narrow the claim*,
*add the robustness check the referee implies*, *concede in limitations*, *change venue* —
each with what it costs and what it saves; `--yes` takes rank 1. The pick lands in the
tracker's action item.

### Step 3: Route Every Comment

| Class | Routing | Action |
|-------|---------|--------|
| **NEW ANALYSIS** | → Coder agent | Flag for user, create analysis task |
| **CLARIFICATION** | → Writer agent | Draft rewritten passage (local) |
| **REWRITE** | → Writer agent | Draft structural revision (section or argument reorganised) |
| **DISAGREE** | → User (mandatory) | **Option gate**: 3–5 response strategies (evidence-led, partial concession, reframing, scope clarification, decline with citation), pick one, then draft; flag for review |
| **MINOR** | → Writer agent | Draft fix directly |

### Step 4: Build Tracking Document
Fill `.claude/skills/revise/templates/response-tracker.md` and save it to
`quality_reports/referee_response_tracker.md` with:
- Summary counts per referee
- Action items by priority (HIGH: new analysis, MEDIUM: clarification, FLAGGED: disagreements, LOW: minor)

### Step 5: Dispatch Agents
- CLARIFICATION/REWRITE → dispatch writer, then writer-critic; record the score
- NEW ANALYSIS → after user approval dispatch coder, then coder-critic; record the score. Then dispatch writer and writer-critic for the affected section; record the score.
  - `code`: `python3 .claude/scripts/pipeline.py state record-score code <score> --critic coder-critic --deductions <total> --report <path>`
  - `manuscript`: `python3 .claude/scripts/pipeline.py state record-score manuscript <score> --critic writer-critic --deductions <total> --report <path> --scope section:<name>`
- DISAGREE → draft diplomatic response, flag prominently for user

After the last critic dispatch and its `record-score`, run
`python3 .claude/scripts/pipeline.py post writer`. FAIL (critic-ran / render / prose-check) →
fix and re-dispatch; do not write the response letter against a manuscript that has not
passed `post`.

### Step 6: Draft Response Letter
Write the letter **from** `.claude/skills/revise/templates/response-letter.qmd` (one `##` per
referee, one `###` per comment):
- Summary of major changes
- Point-by-point responses quoting each referee comment verbatim, visually separated from the response
- Where each change landed, by cross-reference (`@sec-`, `@tbl-`, `@fig-`) — never a page number; pages move, anchors do not

### Step 7: Diplomatic Disagreement Protocol
When DISAGREE: open with acknowledgment, provide evidence, offer partial concession, NEVER say
"the referee is wrong" — the phrasing patterns are
`.claude/skills/revise/templates/diplomatic-disagreement.md`. FLAG for user review.

### Step 8: Save Outputs
1. Tracker: `quality_reports/referee_response_tracker.md`
2. Response letter: `quality_reports/referee_response_[journal]_[date].qmd` (renders to PDF or Word from its own YAML)
3. Revised prose: edited in place in `manuscript_<project>.qmd` (for CLARIFICATION/REWRITE items)

---

## Principles
- **The response letter is the user's voice.** Match their tone.
- **Never fabricate results.** Mark NEW ANALYSIS items as TBD.
- **Flag all DISAGREE items.** These need human judgment.
- **Track everything.** Every comment appears in both tracker and response letter.
