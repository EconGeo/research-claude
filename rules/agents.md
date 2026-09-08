# Agents: Pairs, Separation of Powers, and Escalation

---

## 1. Adversarial Pairing

**Every worker agent has a paired critic. The Orchestrator never dispatches a creator without scheduling its critic.**

### Worker-Critic Pairs

| Worker (Creator) | Critic (Reviewer) | What's Reviewed |
|-----------------|-------------------|-----------------|
| explorer | explorer-critic | Data feasibility, quality, identification fit |
| data-engineer | coder-critic | Data pipeline quality, reproducibility, transformation correctness |
| strategist | strategist-critic | Identification validity, assumptions, robustness |
| theorist | theorist-critic | Proof validity, assumption minimality, notation, citations |
| coder | coder-critic | Code quality, reproducibility, code-strategy alignment |
| writer | writer-critic | Manuscript polish, Quarto format compliance, hedging |
| storyteller | storyteller-critic | Talk structure, audience calibration, visual quality |

### Peer Review (Special Case)

Peer Review uses a different structure — the Orchestrator dispatches two independent referees:

1. Orchestrator assigns the paper to domain-referee and methods-referee (blind, independent)
2. Both referees produce scored reports
3. Orchestrator synthesizes a decision: Accept / Minor Revisions / Major Revisions / Reject

### Enforcement

- The Orchestrator checks: if a creator artifact exists without a critic score, it is **not approved**
- No artifact advances to the next phase without its critic's score >= 80
- Critics produce scores; creators produce artifacts — never the reverse

---

## 2. Separation of Powers

**Critics never create. Creators never self-score.**

### Critics Never Create

A critic's job is to evaluate, not to produce artifacts. If a critic produces code, text, or data during its review, something is wrong.

**What critics DO:**
- Score artifacts against a rubric
- List issues with severity and deductions
- Suggest fixes (as recommendations, not implementations)

**What critics DON'T DO:**
- Write code to fix the issues they found
- Rewrite paper sections
- Produce alternative implementations

**Why:** A critic who fixes their own findings has incentive to find only fixable issues. Separation keeps criticism honest.

### Creators Can't Self-Score

A creator cannot evaluate the quality of its own work. The score always comes from the paired critic.

| Agent | Creates | Scored By |
|-------|---------|-----------|
| librarian | Annotated bibliography | librarian-critic |
| explorer | Data assessment | explorer-critic |
| data-engineer | Data pipeline and cleaned datasets | coder-critic |
| strategist | Strategy memo | strategist-critic |
| theorist | Assumptions, theorems, proofs (theory section) | theorist-critic |
| coder | R/Python/Julia scripts | coder-critic |
| writer | Paper manuscript | writer-critic |
| storyteller | Beamer talk | storyteller-critic |

### Enforcement

The Orchestrator flags violations:
- If a critic invocation produces a file in `scripts/`, `paper/`, or `paper/talks/` → flag
- If a creator reports its own score → discard, dispatch critic

---

## 3. Three Strikes Escalation

**If a worker-critic pair fails to converge after 3 rounds, the Orchestrator escalates.**

### The Protocol

```
Round 1: Critic reviews → Worker fixes
Round 2: Critic reviews → Worker fixes
Round 3: Critic reviews → Worker fixes
         Still failing?
              ↓
         ESCALATION
```

### Escalation Routing

When a pair hits 3 strikes, escalate as follows:

| Pair | Escalates to |
|---|---|
| explorer / explorer-critic | User — data feasibility is a resource trade-off, not a technical call |
| strategist / strategist-critic | User — a fundamental design question needs human judgment |
| theorist / theorist-critic | User — the user adjudicates whether the result holds |
| coder / coder-critic | strategist-critic — re-evaluate whether the strategy is implementable |
| data-engineer / coder-critic | strategist-critic — re-evaluate whether the data spec is tractable |
| writer / writer-critic | User — a structural rewrite is a decision, not a fix |
| storyteller / storyteller-critic | writer — talk problems usually come from paper structure |

Escalating to the user requires a specific question, never "they disagree."

### Rules

- **Max 3 rounds per pair per invocation** — no infinite loops
- **Escalation is logged** in the research journal with strike count
- **User escalation requires a clear question** — not "they disagree," but "strategist-critic requires X, which contradicts Y. Which takes priority?"
- **Post-escalation:** The worker starts fresh from the escalation target's decision, not from its previous attempt

---

## 4. No phase graph

Worker→critic pairing is the whole protocol. There is no orchestrator, no
dependency graph, and no phase gating. Any skill may invoke any agent when its
inputs exist.

The coder↔writer loop in particular is expected to cycle: a result changes the
prose, the prose exposes a question the code has to answer, and that is normal
research rather than a failure of sequencing. Serializing it was the
orchestrator's mistake, and it is why the orchestrator is gone (see
`docs/decisions/2026-09-08_cut-the-orchestration-graph.md`).

What survives from the old graph is what actually did work: the pairs above,
three-strikes escalation, and the rule that a creator never scores its own output.
