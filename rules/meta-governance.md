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

This table is for learnings **inferred from the dispatch log and state file** — strikes,
escalations, first-pass scores. Inferred once, in one project, they are noise; the bar is
validation across 3+ projects and the user's confirmation. A user's own correction is not
inferred and is not governed by this bar — see "User corrections" below.

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

## User corrections

A user correcting the output of a shared skill, agent or rule — or naming an output as the
example to follow — is decided evidence, not a pattern to be counted. Two paths, and a
correction is **never silently** applied to the shared tree:

1. **The rule: ask once, at the moment of the correction** — "Make this permanent in
   `<target file>`?" On yes: edit through the link, run `check_fork.sh`, and land it
   with `/promote`, whose commit names the project it came from. On no, or when the
   correction is project-specific: a real-file override or a gotchas line in the project.
2. **Whatever the answer, `/checkpoint` records it** — one row in the shared ledger,
   `python3 .claude/scripts/ledger.py add`, and one report line. `/promote` reads the ledger
   (`ledger.py show --open`) and flags any target named by **2 distinct projects** as
   REPEATED. That is the signal that a correction declined or missed once is a recurring
   mistake, and it goes to the user with the rows attached.

The ledger is `docs/improvement-ledger.md` in the research-claude checkout. Rows are generic
(no dataset, journal or paper nouns). A row whose target is under `zotpilot-skills/` or
`ai-audit/` is reported as "upstream PR" and never edited here (`/promote` Step 2.5).

No skill carries a closing "apply the improvement rule" step: that is a per-invocation tax
across every SKILL.md, declined 2026-09-16 and declined again here. The rule is this section;
the mechanism is `/checkpoint` → ledger → `/promote`.
