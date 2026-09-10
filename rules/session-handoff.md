# Session Handoff: Keep the Cold-Start Document True

**Additive rule.** It extends what `/checkpoint` must verify. It does not change
`/checkpoint`'s save targets and does not require any new document to exist.

## The problem this fixes

Session continuity is already designed: `SESSION_REPORT.md` (append-only history),
`quality_reports/research_journal.md` (agent trail), auto-memory (cross-conversation
learnings), and the checkpoint file itself. **The active plan is the cold-start
document** — the plan template says so in its own §0: *"written to be read cold, with
no prior conversation context."*

That design works. What it does not defend against is **the plan going stale while
still claiming to be current.** A plan whose status section is three days behind is
worse than no plan, because it is trusted. A resuming session reads "this is task M1
and it is first," starts M1, and discovers an hour later that M1 finished on Tuesday.

Observed in practice: over four days of fast work, a plan's status section
simultaneously understated the defect count (4 vs 14 actual), reported a stale audit
result (0 failures / 6 warnings vs 0/0 actual), and named a completed task as the next
one. Every individual session was disciplined. The drift was cumulative and nobody
owned it.

**The fix is not another document. It is making the checkpoint verify the one that
already exists.**

## Requirement 1 — Plan staleness sweep (MANDATORY at every `/checkpoint`)

Before the checkpoint is reported as saved, re-read the active plan's status section
and confirm each of these still holds:

- [ ] Counts are current — defects, tasks done, rows closed.
- [ ] Quoted tool output is current — audit results, test results, gate states.
- [ ] "Next is X" actually names something not yet done.
- [ ] Phase gates described as pending are in fact pending.
- [ ] Any "this is first" / "this is blocking" claim is still true.

**Fix the plan. Do not record the drift somewhere else.** Two documents disagreeing is
worse than one being wrong, and a note saying "the plan is out of date" will not be
read by the session that needs it.

Report the outcome in the checkpoint confirmation: `Plan staleness sweep: clean` or
`fixed: <what>`.

## Requirement 2 — HANDOFF.md (OPTIONAL, per project)

Most projects do not need one. Add it when the plan is a poor cold-read for a specific
reason — typically it has grown large (an R&R plan running to hundreds of lines), or
the project has diverged from the plan's structure, or work is proceeding on tracks the
plan does not cover.

When a project does have one:

- **It is REGENERATED at every checkpoint, never appended to.** `SESSION_REPORT.md` is
  append-only history; `HANDOFF.md` is a replaced snapshot of *now*. A handoff that
  accumulates becomes a second session log and stops being trustworthy.
- Use `.claude/templates/handoff.md` for structure.
- It never contradicts the plan. The plan is authoritative for *what to do*; the
  handoff is authoritative for *where things stand*. A disagreement is a bug to fix in
  the same checkpoint, not a state to live with.

## Requirement 3 — Verify, do not just write

Writing the document is the easy half. Both requirements above are verified before the
checkpoint reports success.

**Reference dry-run** — every file named in `HANDOFF.md` must resolve:

```bash
grep -oE '`[A-Za-z0-9_./-]+\.(md|R|py|json|csv|qmd|tex|sh|yml)`' HANDOFF.md \
  | tr -d '`' | sort -u | while read -r f; do
    [ -e "$f" ] && continue
    # bare filename used in prose rather than as a path — resolve by basename
    [ -n "$(find . -name "$(basename "$f")" -not -path './.git/*' -print -quit)" ] && continue
    echo "BROKEN REFERENCE: $f"
  done
```

Two notes, both learned by getting it wrong first:

- The basename clause is required. Prose legitimately writes ``model_corrections.md``
  without its directory; a naive check flags those and trains you to ignore the output.
- **Files that legitimately live outside the repo will flag. Do not suppress them** —
  write them with enough path to be obviously external (`../shared-data/crosswalk/foo.csv`,
  not `foo.csv`) so the next session knows it is not hunting a missing repo file. Read
  the output; do not just look for an empty result.

**Health commands** — actually run whatever the handoff tells the next session to run,
and confirm the output matches what you wrote. A handoff that says "expect 0 failures"
when the audit now fails is an active trap.

## Scope

This rule governs checkpoint verification only. It does not alter `/checkpoint`'s
existing save targets and does not require `HANDOFF.md` to exist.
