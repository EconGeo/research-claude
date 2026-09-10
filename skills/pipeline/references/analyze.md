# Reference: analyze

**Delegates to:** `/analyze [goal or strategy-memo path]`

**Creators:** data-engineer (wrangling, `.claude/agents/data-engineer.md`), then coder
(estimation, `.claude/agents/coder.md`) — both kind: agent, both scored under the same
component.
**Critic:** coder-critic (kind: agent — `.claude/agents/coder-critic.md`), dispatched after
each.
**Component recorded:** `code` (weight and threshold: `.claude/rules/quality.md`). Because
both creators share this component, a passing `post coder` after data-engineer's work only
confirms a critic ran recently — not that it reviewed coder's chunks specifically
(`.claude/rules/lifecycle.md`, "A limitation this does not close").

`requires`: `strategy` score ≥ 80, for both creators.

## Driver sequence
```
python3 .claude/scripts/pipeline.py pre coder
python3 .claude/scripts/pipeline.py conflicts data-engineer coder     # sanity: never concurrent
                                                                         # invoke /analyze [goal]
python3 .claude/scripts/pipeline.py post coder
```
`/analyze` dispatches data-engineer then coder-critic (Step 2), then coder then coder-critic
(Step 3), recording `state record-score code <score> --critic coder-critic --report <path>`
after each round.

## Approval-gate summary
Rendered output path, chunk labels added (`tbl-*`, `fig-*`, `build-*`), the coder-critic
score, and open items (missing data, specs the memo names that could not be run).

## Escalation (strike 3, target: strategist-critic — not user)
"coder-critic flags <specification/estimand mismatch against the strategy memo> after 3
rounds — does the memo's design need to change, or is the code wrong?"
