# Reference: adopt (a project with existing work)

The driver was built for a paper that starts at literature. Most papers it meets did not:
they have a manuscript, an analysis, sometimes referee rounds, and no `pipeline_state.json`.
`state init` writes an empty state, so every stage reads as unstarted and `run` would point
`writer` at a paper already through review. Adoption is how the state file comes to say what
is true about the work, without inventing anything.

## The rule

**A score is recorded only by the registry's critic, only against a report that critic wrote,
only after it actually read the work.** `record-score` refuses any other `--critic`
(`.claude/rules/registry.yaml`, `scored_by`), and the driver never back-fills a score from the
research journal, a memory of a review, or a legacy state file's number without the report
behind it. A component whose artifact does not exist stays unscored: renormalisation excludes
it from `overall`, and `next` reports it as SKIPPED rather than pretending.

`next` treats a component score with no logged creator completion as **CLOSED** — that is
what adoption produces, and also what a coauthor's clone produces (the dispatch log is
gitignored and does not travel). It is a statement about the score, not the round: `post`
stays the in-run gate, and a creator completion after the score reopens the stage.

## Sequence

```
python3 .claude/scripts/pipeline.py manuscript        # declared? (setup.md)
python3 .claude/scripts/pipeline.py state init
python3 .claude/scripts/pipeline.py next              # everything READY / BLOCKED / SKIPPED
```

Then, for each component whose **artifact already exists**, dispatch its critic on it through
the critic-only route and record the score the critic gives. Do this in registry order and
stop where the work stops:

| Component | Artifact that must exist | Critic-only route | Records |
|---|---|---|---|
| `literature` | `quality_reports/literature/<project>/positioning.md` (+ bibliography, frontier map) | dispatch lit-critic as `/lit-position` Step 7 does | `literature` |
| `data` | `quality_reports/data-assessment/<project>/data_sources.md` | dispatch explorer-critic as `/discover data` Step 6 does | `data` |
| `strategy` | `quality_reports/strategy/<project>/strategy_memo.md` — or, absent a memo, the manuscript's own design section | `/review --methods` | `strategy` |
| `theory` | a `# Theory` heading in the manuscript | `/review --theory` | `theory` (opt-in; conditional) |
| `code` | `tbl-*` chunks in the declared manuscript | `/review --code <declared manuscript>` | `code` |
| `manuscript` | the declared manuscript renders | `/review` on the declared manuscript (comprehensive) | `manuscript`, plus `strategy` and `replication` |
| `referees` | a completed `/review --peer` | `/review --peer [journal]` — this *is* the stage; nothing to adopt | `referees` |

`/review` on the declared manuscript records three components in one pass, so for a
finished draft the whole adoption is usually: `/review --code <manuscript>` then `/review`.
Re-run `next` after each recording and watch the frontier move.

## What adoption does not do

- It does not write a strategy memo, a positioning file or a data assessment that the project
  never had. If a downstream `pre` needs one (`coder` needs `strategy` ≥ 80; `strategist`
  needs `positioning.md` or `data_sources.md`), the honest routes are: run the stage for real,
  or leave it and work from the frontier. Both are visible in `next`.
- It does not lower a score to make a gate pass or raise one to make a stage close. A critic
  that scores adopted work at 61 has told you where the paper stands; `next` will suggest that
  stage, and the creator fixes what the report names — the same loop as any other round.
- It does not touch the dispatch log. Adopted stages have no creator completion, which is
  exactly how `next` recognises them.

## Two limitations, stated

- `data-engineer` and `coder` share `code`; a single coder-critic score closes both
  (`.claude/rules/lifecycle.md`, "A limitation this does not close").
- A legacy state file may carry scores from an earlier pipeline. Port one only when the
  report it names exists and was written by the critic the registry declares for that
  component; otherwise re-score. Point `--report` at the real report, never at the legacy
  state file.
