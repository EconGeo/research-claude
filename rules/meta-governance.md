# Meta-Governance: Learning Promotion and Self-Modification

research-claude is one researcher's pipeline linked into every paper project. Anything in
`agents/`, `skills/`, `rules/`, `hooks/`, `templates/` or `seeds/` reaches every project, so a
change there is a decision, not a side effect.

## The one rule

Before committing to the shared tree, ask: **would every project linked to this pipeline be
better off with this?** Yes → commit through `/promote`. No → keep it in the project as a real
file override (a non-symlink under `.claude/`, with a negation line in `.gitignore`) or in
`.claude/state/`.

## Learning promotion

When a pattern has been validated across 3+ projects and the user confirms it:

| Pattern | Promotion target | Requires |
|---|---|---|
| PATTERN (replicable success) | best-practice line in the relevant agent's protocol | user approval |
| FRICTION (recurring three-strikes) | agent prompt revision or rubric adjustment | user approval |
| HIGH-PERF (consistent first-pass ≥ 90) | new content invariant or rule line | user approval |

**Protocol.** `/pipeline` surfaces "Suggested Learnings" at the end of a run from the dispatch log
and state file (recurring strikes, escalations to the user, first-pass ≥ 90). The user approves or
rejects each. An approved learning is landed upstream with `/promote`, which is the **only**
promotion mechanism.

**Constraint.** Promotion always requires user approval. The system suggests; the user decides.
No autonomous modification of rules, invariants, agent prompts or the registry.
