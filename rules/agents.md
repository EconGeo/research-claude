# Agents: Pairs, Separation of Powers, Escalation, Dispatch Ownership

## 1. Adversarial pairing

**Every creator has a paired critic, declared in `.claude/rules/registry.yaml` and nowhere else.**
The dispatching skill dispatches the critic after the creator, every time, in every mode
(orchestrated or standalone). `python3 .claude/scripts/pipeline.py post <creator>` refuses to
mark a creator complete until the dispatch log shows its critic completing afterwards and the
state file carries the critic's score.

**Enforcement.**
- `pipeline.py post` — `critic-ran` predicate (structural).
- `.claude/hooks/critic-pairing.py` (Stop) — reads `quality_reports/agent_dispatch.jsonl` and
  surfaces a creator that ran without its critic in the current session.
- `check_fork.sh registry-complete` — no creator with a non-zero weight lacks a critic.

**Peer review** is the one asymmetric structure: the editor dispatches two blind referees and
synthesises a decision. Referees are already reviewers and have no critic (registry `role: referee`).

## 2. Separation of powers

**Critics never create. Creators never self-score.**

A critic scores against a rubric, lists issues with deductions, and recommends fixes as
recommendations. A critic that writes code, rewrites a section, or produces an alternative
implementation has failed its role. A creator's own assessment of its work is discarded; the
score always comes from the paired critic, recorded by the dispatching skill with
`pipeline.py state record-score`.

**Enforcement.** The dispatching skill flags: a critic dispatch that leaves a file under a
creator's `WRITES` prefix; a creator that reports a score.

## 3. Three-strikes escalation

Round 1: critic reviews → creator fixes. Round 2. Round 3. Still below threshold → escalate to
the `ESCALATION_TARGET` declared for the creator in the registry. `pipeline.py state strike
<creator>` counts rounds and prints the target at three.

- Max 3 rounds per pair per invocation; 5 rounds overall; never loop indefinitely.
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

Pairs, weights and escalation targets are **not** restated here. Read
`.claude/rules/permissions.md` (rendered from the registry).
