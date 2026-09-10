# Cut the orchestration graph and the librarian pair

**Date:** 2026-09-08
**Status:** Decided (D1, D3 of the Quarto-native fork)
**Superseded in part 2026-09-08** by `2026-09-08_d1-superseded.md`: D1 stands for the *agent*; the registry, lifecycle and governance rules return. D3 stands for the *collector*; its critic returns as `lit-critic` (see `2026-09-08_d3-addendum-lit-critic.md`).

**Decision:** delete `orchestrator`, `guide-writer`, `librarian`, `librarian-critic`,
and with them `rules/permissions.md`, `rules/lifecycle.md`, `rules/workflow.md`.

## Why

**`orchestrator`** was structurally unreachable — only `/new-project` dispatched it, and
`apply.sh` refused to install `/new-project` (that is what `CLO_SKIP_SKILLS` existed to
express). Its phase graph also serializes the coder↔writer loop that the research journal
shows actually cycles. Worker→critic pairing and three-strikes escalation — the parts that
do work — survive in `rules/agents.md`, which gains a `## 4. No phase graph` section
stating that any skill may invoke any agent once its inputs exist.

**`guide-writer`** wrote documentation for a public template. This is not a public template;
it is one researcher's pipeline. `meta-governance.md` goes for the same reason.

**`librarian` / `librarian-critic`** were WebSearch-first, which directly contradicts
`rules/literature-search-order.md` (local Zotero corpus first, external databases only for
what the library lacks). Their substantive content — frontier mapping, positioning against
the closest paper, and the six `librarian-critic` review categories — survives in
`skills/lit-position/`, a bridge skill over the vendored ZotPilot skills.

## What would invalidate this

- A project that genuinely needs multi-phase autonomous dispatch, where a human deciding
  "what runs next" is the actual bottleneck.
- A literature workflow ZotPilot cannot serve — e.g. a field whose corpus is not in Zotero
  and cannot be ingested.

Either would justify restoring a dispatch layer. Neither is true of any project under
`~/Research` today.

## Related

- `agents/verifier.md` — note that POGM4's `verifier.md` was **not** harvested. It is a
  `~/Courses` slide verifier that leaked into a `~/Research` project (12 Beamer/TikZ/slide
  hits against clo-author's 6 LaTeX hits), the exact domain crossover the user's global
  CLAUDE.md forbids. clo-author's two-mode verifier was taken instead, with check 1
  rewritten `latexmk` → `quarto render`. See plan correction C1.
