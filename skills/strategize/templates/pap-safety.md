# PAP Safety — ASSUMED Placeholders and the Critic's Criteria

Read at the PAP drafting and review steps of `/strategize pap`.

---

## ASSUMED placeholder safety

**Flag every ASSUMED item clearly. The researcher must review and approve before registration.**

When drafting a PAP from a topic — without a full research spec or the interactive interview —
many details are assumed. For each assumed item:

- mark it **`[ASSUMED]`** in bold
- explain what was assumed and why
- give the most reasonable default, but flag it for review

A registered PAP with unchecked assumptions is worse than no PAP. The final section of every PAP
must be:

```markdown
## Pre-Registration Checklist

**Review every [ASSUMED] item before registering this plan.**

- [ ] [ASSUMED] Item 1 — [what was assumed]
- [ ] [ASSUMED] Item 2 — [what was assumed]

**Do not register until all items are reviewed and confirmed or corrected.**
```

---

## What the strategist-critic checks in a PAP

These are PAP-specific and sit on top of the critic's own rubric in
`.claude/skills/review/config/scoring-rubrics.md`:

- Are identification assumptions clearly stated and defensible?
- Is the estimator choice appropriate for the design?
- Are power calculation assumptions reasonable? Is sensitivity shown?
- Are pre-specified subgroups justified, rather than fishing?
- Are multiple testing corrections appropriate?
- Would any `[ASSUMED]` item be a problem if left uncorrected?
