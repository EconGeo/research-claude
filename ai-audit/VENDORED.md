# Vendored ai-audit

These are the two ai-audit skills (`/humanize`, `/verify-claims`) and their paired agents
(`humanize-auditor`, `claim-verifier`), **vendored** from `EconGeo/ai-audit`. `apply.sh`
links `agents/` and `skills/` into each project's `.claude/agents/` and `.claude/skills/`,
the same way it links everything else under `agents/` and `skills/` at repo root.

They are vendored — not a git submodule — on purpose. research-claude only needs these
8 files; a submodule needs `git submodule update --init` and silently yields an EMPTY
directory when a clone or a coauthor skips that step. That failure was hit for real
against this repo's `submodules/` mechanism, which is why both submodules it carried
(`ai-audit` and `journal-digest`) were removed on 2026-09-09 and `.gitmodules` deleted
entirely. This mirrors `zotpilot-skills/VENDORED.md`, which made the same call about
ZotPilot's skills for the same reason.

## What was taken

- `agents/claim-verifier.md`, `agents/humanize-auditor.md`
- `skills/humanize/SKILL.md`, `skills/verify-claims/SKILL.md`
- `README.md` (upstream's own, describing both tools — copied verbatim)

## What was deliberately left out

- **`rules/ai-disclosure.md` is NOT carried here.** The submodule shipped its own copy of
  this rule (127 lines) that had drifted from the top-level `rules/ai-disclosure.md`
  (128 lines): the submodule's copy still described a dual LaTeX+Quarto placement
  ("LaTeX pipeline (`paper/main.tex`)" / "Quarto pipeline (`manuscript_quarto.qmd`)")
  and listed `latexmk, pandoc, knitr` as compilation tools requiring no disclosure. The
  top-level copy already reflects the single-manuscript Quarto-only pipeline (a generic
  `manuscript_<project>.qmd`, `quarto render` as the only compilation-adjacent entry) and
  was kept as the one true copy. `apply.sh` used to link the standard `rules/` first and
  then this submodule's `rules/` second, so `ln -sfn` let the *stale* submodule copy win
  in every installed project — verified live in `~/Research/POGM4/.claude/rules/ai-disclosure.md`.
  That link step is gone; `ai-audit/` ships no `rules/` directory at all, so
  `rules/ai-disclosure.md` at repo root is the only copy and cannot be shadowed again.
- `.gitignore`, `.git` (submodule plumbing — not applicable to a vendored copy)

## Provenance / refresh

- Source: `https://github.com/EconGeo/ai-audit.git`
- Vendored from commit: `8122ea930e7fb6c59e0cd222e6d882a89f819384`

To refresh after the upstream repo's skills or agents change, run:

```bash
scripts/sync-ai-audit.sh
```

It sparse-fetches `agents/`, `skills/` and `README.md` from the upstream repo — never
`rules/`, see above — and overwrites this directory in place. Update the commit line
above when you do, and re-check `rules/ai-disclosure.md` by hand for drift if upstream's
copy changed.
