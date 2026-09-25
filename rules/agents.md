# Agents: Pairs, Separation of Powers, Escalation, Dispatch Ownership

## 1. Adversarial pairing

**Every creator has a paired critic, declared in `.claude/rules/registry.yaml` and nowhere else.**
The dispatching skill dispatches the critic after the creator, every time, in every mode
(orchestrated or standalone). `python3 .claude/scripts/pipeline.py post <creator>` refuses to
mark a creator complete until the dispatch log shows its critic completing afterwards and the
state file carries the critic's score.

**Enforcement.** These are not three equal gates. Only the first refuses anything.
- **`pipeline.py post` — the gate.** Its `critic-ran` predicate refuses to close a creator's
  stage without a critic completion that postdates the creator AND a component score recorded
  after it, by the critic the registry declares. Nothing else here can stop a session.
- **`.claude/hooks/critic-pairing.py` (Stop) — advisory.** It reads
  `quality_reports/agent_dispatch.jsonl` and surfaces a creator that ran without its critic.
  It blocks **once per creator per session**, then goes advisory, so a session can pass it by
  stopping twice. That is deliberate — a Stop hook that blocks unconditionally can trap a
  session with no way out — but it means the hook makes a session *notice*, it does not make a
  session *comply*.
- **`check_fork.sh registry-complete` — a template check, not a runtime one.** It only asserts
  that no creator with a non-zero weight lacks a declared critic in the registry.

Note that nothing forces `pipeline.py post` to be *called*. A session that never runs it is
never gated; `/pipeline` is what runs it on every stage.

**Peer review** is the one asymmetric structure: the editor dispatches two blind referees and
synthesises a decision. Referees are already reviewers and have no critic (registry `role: referee`).

## 2. Separation of powers

**Creators write the artifact. Critics write the review.** A creator never scores its own work;
a critic never edits the artifact it reviews. A critic scores against a rubric, lists issues with
deductions, and recommends fixes as recommendations — a critic that writes code, rewrites a
section, or produces an alternative implementation has failed its role. The score always comes
from the paired critic, recorded by the dispatching skill with `pipeline.py state record-score`.

**A critic also never saves its own report.** No critic, referee or infrastructure-role reviewer
(`editor`, `domain-referee`, `methods-referee`, `verifier`) declares `Write`, and none should —
`Write` is all-or-nothing in an agent's frontmatter, and a reviewer that could write *anything*
could edit the manuscript it scores. `verifier` carries `Bash` for its render and cold-cache
checks, not for authoring; `writer-critic` carried `Bash` too, but nothing in its file used it for
anything but self-saving the report, so that tool is now removed. The model is
`ai-audit/agents/civilize-auditor.md`'s `## Output` section: *"Structured report — return as your
final response. Do NOT write any files yourself — the skill orchestrates report-saving."*

**Every returned report is saved the instant it comes back — never batched until a workflow, a
parallel dispatch, or a multi-phase flow finishes.** An agent without `Write` has no other way
onto disk; its report exists only in the conversation until the dispatching skill writes it. A
session that ends between dispatch and save — closed laptop, crash, context limit — loses that
work permanently if it was not written immediately (observed: `/review`'s comprehensive mode once
lost a completed strategist-critic report because the skill waited to save all three critics'
reports together). This does not protect a report still being composed *inside* one long critic
turn — no dispatched agent can stream partial output to the session that called it, so a critic
reviewing an entire manuscript in one turn is exposed for the length of that turn. Splitting a
long review into several smaller dispatches would close that gap too, at the cost of the critic's
cross-category holistic judgment across the whole manuscript; considered and deliberately not done
— clo-author has the identical exposure (checked directly: its `writer-critic` also has no `Write`
and also reviews the whole manuscript in one turn; its only mitigation is a manual `/checkpoint`
before session end, which is weaker than saving on every return).

**Enforcement.** The dispatching skill flags: a critic dispatch that leaves a file under a
creator's `WRITES` prefix; a creator that reports a score.

## 3. Three-strikes escalation

Round 1: critic reviews → creator fixes. Round 2. Round 3. Still below threshold → escalate to
the `ESCALATION_TARGET` declared for the creator in the registry. `pipeline.py state strike
<creator>` counts rounds and prints the target at three.

- **The stage skill owns `state strike` for its own creator** — the same convention as
  `record-score`. `/pipeline` reads the count (`state show`) and escalates on it; it never adds
  to it. `pipeline.py state strike` is an unconditional increment with no round key, so a second
  call in the same failing round is a second strike, and a stage with no call site at all never
  escalates. Exceptions, stated in their reference files: `/review --all` re-scores existing
  work and sends it back to its creator's stage; `/submit` has no creator.
- Max 3 rounds per pair per invocation; 5 rounds overall (summed across creators); never loop
  indefinitely. `pipeline.py state strike` refuses, and records nothing, past either limit.
- **Each round's critic report is its own file.** Round 1 saves to
  `quality_reports/reviews/explorer-critic_<date>.md` (each critic under its own name); rounds 2 and 3 the same day save to
  `explorer-critic_<date>_r2.md` and `_r3.md`, and `record-score --report` names that file. A report is
  never overwritten: `.claude/hooks/protect-files.sh` lets a session create a report and blocks
  every rewrite of one, so a second round saved to the first round's name stalls the loop.
- **Each round is a fresh foreground dispatch the session waits on** — a new `Agent` call with
  `run_in_background: false`, never `SendMessage` to the earlier agent and never a background
  run. The round's result is what the critic re-scores; a session that ends its turn while a
  revision is still running (headless `claude -p` exits right there) leaves the stage at the
  failing score, with no re-score and none of the stage's closing artifacts (observed:
  `/strategize` 2026-09-25, round 2 sent by `SendMessage`, run ended at the round-1 49).
- Escalation is logged in the research journal with the strike count.
- Escalating to the user requires a specific question: "strategist-critic requires X, which
  contradicts Y — which takes priority?", never "they disagree".
- After escalation the creator starts from the target's decision, not from its last attempt.

## 4. Dispatch ownership

The dependency graph lives in the registry (`REQUIRES` / `PRODUCES`), the loop lives in
`/pipeline`, and every stage skill owns its pair. Phases activate by `REQUIRES`, never by
sequence; re-entry is permitted everywhere except Submission. The coder↔writer cycle is normal
research, and the registry supports it: a referee comment routes back through the code stage and
then the writing stage, each with its paired critic per the registry, without restarting the
pipeline.

| Skill | Dispatches | Then |
|---|---|---|
| `/lit-position` | (skill is the creator) | lit-critic |
| `/discover data` | explorer | explorer-critic |
| `/strategize` | strategist | strategist-critic |
| `/strategize theory` | theorist | theorist-critic |
| `/analyze` | data-engineer, coder | coder-critic (after each) |
| `/write` | writer | writer-critic (every mode that touches prose; `style-guide` exempt) |
| `/review` | critics only, by route | — |
| `/review --peer` | editor → domain-referee ∥ methods-referee → editor | — |
| `/revise` | writer or coder per comment | its critic |
| `/submit package` | coder | coder-critic |
| `/submit audit`, `/submit final` | verifier | — |
| `/talk` | storyteller | storyteller-critic |
| `/pipeline` | the skills above, in `REQUIRES` order, with `pipeline.py pre`/`post` around each | — |

The table above is **dispatch ownership** — which skill dispatches what, keyed by skill.
It is deliberately not a pairing table: a creator's bound critic, its escalation target and its
component weight are declared once, in `.claude/rules/registry.yaml`, and rendered to
`.claude/rules/permissions.md`. Where the two could ever disagree, the registry is right and this
table is stale. Read `permissions.md` before relying on a pairing.

A skill that offers the user a ranked choice before dispatching does so as an **Option gate**
under `.claude/rules/option-gates.md` — one mechanism, `--yes` takes rank 1, the pick lands
in the artifact the step already writes.

## 5. Mechanical failures are not quality rounds

A render error, a script traceback, or a chunk that will not run is not a strike (§3) —
it happens before a critic ever sees the work. `.claude/rules/systematic-debugging.md`
governs it: capture the exact error, one hypothesis at a time, stop and report after two
falsified hypotheses rather than guessing a third time.
