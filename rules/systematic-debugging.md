# Systematic Debugging: Root Cause Before Retry

Governs any **mechanical failure** an agent hits mid-task — a `quarto render` error, a
failing chunk, a script that throws, a replication that does not match, a test that fails.
This is not `.claude/rules/agents.md` §3 (three-strikes): that governs *quality* rounds
between a creator and its paired critic, on work that already ran. This governs what
happens *before* a critic ever sees it, inside one creator's own turn, when the thing
does not run at all.

**Adopted from `garrytan/gstack`'s `/investigate` discipline** (max three failed fixes
before stopping), scoped down to a two-attempt cap here because a creator that reaches a
third mechanical failure already has two documented, falsified hypotheses to hand to its
critic or to the user — a third blind attempt adds a guess, not information.

## The loop

1. **Capture the exact error, verbatim.** Not a paraphrase, not "it didn't work" — the
   actual `quarto render` log line, the actual R/Python traceback, the actual diff between
   expected and actual output. A hypothesis built on a paraphrase is a hypothesis about the
   paraphrase, not the bug.
2. **State one falsifiable hypothesis for the root cause before changing anything.**
   "The chunk fails because `df` still has the old column name after the rename in the
   setup chunk" — not "let me try adding `na.rm = TRUE` and see."
3. **Make the smallest change that tests only that hypothesis.** One variable. Do not
   also reformat, also add error handling, also change something unrelated noticed along
   the way — a fix that touches three things and works leaves no way to know which of the
   three mattered.
4. **Re-run and compare against the captured error, not against "no error."** The same
   exact error persisting is refutation. A *different* error is not progress — it is a new
   symptom, and step 1 restarts from it, not from the goal.
5. **If refuted, discard the change.** Do not stack a second speculative fix on top of a
   first one that did not fix anything — an agent that has "tried three things at once" by
   the time something works cannot say which one it was, and the next person to touch this
   code inherits a change nobody can explain.
6. **After two falsified hypotheses on the same symptom, stop.** Do not attempt a third
   fix. Report: the exact error, both hypotheses tried and how each was falsified, and
   what to try next — as a question, not a silent third attempt. `coder` and
   `data-engineer` put this in their returned report instead of the score neither has the
   authority to give itself; a skill running standalone surfaces it to the user directly.

## Anti-patterns

- Changing code before reading the actual error text.
- Re-running the identical command unchanged, hoping for a different result.
- Suppressing the error (`try/except: pass`, `eval: false` on the failing chunk, a flag
  that skips the check) instead of understanding it — this closes the report, not the bug.
- A fix that "shouldn't matter" left in after the real fix is found — every change made
  during the loop that did not survive step 5 must be reverted, not left as harmless
  residue.

## Where this applies

`.claude/agents/coder.md`, `.claude/agents/data-engineer.md` (script and chunk failures);
`.claude/skills/analyze/SKILL.md` (the dispatching skill, when a dispatched agent's report names a
two-hypothesis stop). It does not apply to `.claude/agents/verifier.md` — the verifier only
reports FAIL, it never fixes anything (`.claude/rules/agents.md` §2, `verifier.md`: "The
tree is not yours to change") — and it does not apply to a critic's quality deductions,
which is `.claude/rules/agents.md` §3, a different axis entirely.
