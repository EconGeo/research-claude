# Vendored ZotPilot skills

These are the ZotPilot Claude skills (`ztp-*` and `seed-papers`), **vendored** into this repo.
`apply.sh` installs them into each project's `.claude/skills/`.

They are vendored — not a git submodule — on purpose. research-claude only needs these
~68 KB of skill files; pulling the whole ZotPilot fork as a submodule also dragged in its
224 MB Chrome **connector** toolchain (pdf.js, translators, …) that nothing here uses.

**The ZotPilot MCP server itself is installed separately** (README Step 7,
`pip install git+https://github.com/EconGeo/ZotPilot.git`) — that is what delivers the
server code and the Ollama-embedding additions. These skills only tell Claude how to call
that server's MCP tools.

## Provenance / refresh

**Two sources, deliberately.** The upstream project ships the `ztp-*` skills inside the
package (`src/zotpilot/skills/*.md`) — that is what `zotpilot setup` deploys into a user's
`~/.claude/skills/`, so it is the version people actually run. The EconGeo fork also carries a
`claude-skills/` directory, but its `ztp-*` copies are a **v0.5.0-era snapshot** that has not
tracked upstream. `seed-papers` exists only in the fork.

| Skill | Source | Version |
|---|---|---|
| `ztp-profile`, `ztp-research`, `ztp-review`, `ztp-setup`, `ztp-tutor` | `xunhe730/ZotPilot`, `src/zotpilot/skills/*.md` | tag `v0.5.3` (commit `8b706c6`) |
| `seed-papers` | `EconGeo/ZotPilot`, `claude-skills/seed-papers/` | commit `a8120c5` (`v0.5.0-62-ga8120c5`) |

The five `ztp-*` files are byte-identical to the `v0.5.3` package skills (verified by SHA-256
against the `.zotpilot-version.json` stamps that `zotpilot setup` writes alongside its deploy).

To refresh, run:

```bash
scripts/sync-zotpilot-skills.sh [upstream-tag] [fork-ref]
```

It sparse-fetches only `src/zotpilot/skills/` from upstream and only `claude-skills/` from the
fork (no connector in either), rebuilds this directory from both, and prints the new source
commits. Update the table above when you do.

### Do not sync the `ztp-*` skills from the fork

Until 2026-09-15 this directory was refreshed wholesale from the fork's `claude-skills/`, which
silently held all five `ztp-*` skills at v0.5.0 while users' own `~/.claude/skills/` ran v0.5.3.
Three skills were materially behind — `ztp-setup` lacked the two-layer embedding vendor/model
catalog and `--verify` self-heal, `ztp-research` lacked the `manual_completion_required` /
`publisher_canary_pending` actions and the `notices` handling, and `ztp-tutor` lacked the
separate annotation-language, reading-purpose, domain-familiarity and comment-style axes. The
sync script now pulls those five from upstream instead. The fork's `claude-skills/ztp-*` carry
no fork-specific edits (checked at `a8120c5`: four are byte-identical to the v0.5.0 package
skills and `ztp-tutor` is a strict subset of the upstream text), so nothing is lost by
preferring upstream. **If the fork ever does start editing a `ztp-*` skill, the overlay in
`scripts/sync-zotpilot-skills.sh` must become a real three-way merge.**
