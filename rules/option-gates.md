# Option Gates

An **Option gate** is a wait that offers the user a ranked list and takes a pick. It is the
only kind of wait a skill adds on its own initiative; binary approve/abort waits and the
below-80 critic loop are not option gates and are not governed here.

## Contract

1. **Where it sits.** Before a creator is dispatched, or after a critic has scored. Never
   between a critic's score and the below-80 loop, and never in place of a numeric gate
   (R-42, R-44, R-132).
2. **What it shows.** Five to eight options (5–8), ranked, in a table whose columns the skill
   names. Rank 1 is the skill's own recommendation and is marked. Fewer than five is allowed
   only when the skill says why (e.g. two feasible designs exist); more than eight is a sign
   the options have not been ranked.
3. **What it does.** Present the table, then **wait** for one of: a rank number, `edit`
   (the user rewrites an option and it becomes rank 1), or `none` (the skill stops and
   reports).
4. **`--yes`.** Under `--yes`, or when the invoking `/pipeline run` carried `--yes`, the gate
   does not wait: it takes rank 1 and records `auto: rank 1 (--yes)` where it records the
   pick. `--yes` answers option gates only; it never skips a blocking gate (`/tools commit`
   Step 0, `pipeline.py pre`, a critic score).
5. **Where the pick is recorded.** In the artifact the step already writes — a decision
   record's *Alternatives considered*, `positioning.md`, the referee tracker, the talk file's
   YAML comment block, `journal_recommendations_[date].md`. The rejected options and the
   reason each lost are recorded with it. No new state file, no new `pipeline.py` flag.
6. **How a skill declares one.** One line in the mode section, starting with the literal
   marker `**Option gate**`, naming the columns, the minimum, where the pick lands, and
   this file: `.claude/rules/option-gates.md`. `tests/test_option_gates.py` (in the
   research-claude repo, not linked into projects) checks each declared gate for the marker,
   the rule name and the minimum.

## Why one rule

Fourteen skills each describing their own wait produced fourteen different phrasings of
`--yes` and no test. The mechanism is here once; each skill contributes only the columns,
the minimum and the landing place.
