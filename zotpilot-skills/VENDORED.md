# Vendored ZotPilot skills

These are the ZotPilot Claude skills (`ztp-*` and `seed-papers`), **vendored** from the
`claude-skills/` directory of the EconGeo/ZotPilot fork. `apply.sh` installs them into each
project's `.claude/skills/`.

They are vendored — not a git submodule — on purpose. research-claude only needs these
~68 KB of skill files; pulling the whole ZotPilot fork as a submodule also dragged in its
224 MB Chrome **connector** toolchain (pdf.js, translators, …) that nothing here uses.

**The ZotPilot MCP server itself is installed separately** (README Step 7,
`pip install git+https://github.com/EconGeo/ZotPilot.git`) — that is what delivers the
server code and the Ollama-embedding additions. These skills only tell Claude how to call
that server's MCP tools.

## Provenance / refresh

- Source: `https://github.com/EconGeo/ZotPilot.git`, `claude-skills/`
- Vendored from commit: `577b812` (`v0.5.0-50-g577b812`)

To refresh after the fork's skills change, run:

```bash
scripts/sync-zotpilot-skills.sh
```

It sparse-fetches only `claude-skills/` from the fork (no connector), overwrites this
directory, and prints the new source commit. Update the commit line above when you do.
