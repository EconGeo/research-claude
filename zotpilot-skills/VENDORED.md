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
- Vendored from commit: `6e63dd8` (`v0.5.0-76-g6e63dd8`, merges of `feat/secrets-env` and PR #6 `refactor/ztp-tutor-progressive-disclosure`)

## The fork is the only source — do not sync from upstream

**A newer version number upstream is not a reason to update this directory.** The ZotPilot we
run is the **EconGeo fork**, and it deliberately does not track `xunhe730/ZotPilot`. Its base is
v0.5.0 plus ~40 fork commits — a local Ollama embedding provider, multi-library indexing,
token-aware chunking, ChromaDB batching, a `delete_note` MCP tool — that upstream does not have
and that a rebase would put at risk. Upstream implemented Ollama *differently* (OpenAI-compat
shim + vendor catalog), so the two lineages conflict rather than merge.

The skills here must match the server we actually run, not the newest text available:

- `zotpilot` reports **0.5.0**; `zotpilot setup` accepts only `--non-interactive`,
  `--provider {gemini,dashscope,local}` and `--zotero-dir`.
- Upstream v0.5.3's `ztp-setup` is built on `setup --list-vendors --json` and `--verify`.
  Neither exists here. Tested 2026-09-15: `zotpilot setup --list-vendors --json` →
  `error: unrecognized arguments`.

**This was tried on 2026-09-15 and reverted the same day.** All five `ztp-*` skills were
"updated" to upstream v0.5.3 on the reasoning that the copies in `~/.claude/skills/` carried a
higher version stamp. That stamp comes from upstream's packaged skills, which are simply a
different lineage — not a newer version of these. The change shipped a `ztp-setup` that errors
against our own CLI. Everything here is back to fork `a8120c5`.

If a specific upstream improvement is wanted, port it into the fork's own `claude-skills/` and
sync it down from there. Never overlay upstream onto this directory.

### Do not run `zotpilot upgrade`

The fork's `upgrade` resolves "latest" from **PyPI**, which publishes upstream. Tested
2026-09-15 on the installed 0.5.0 build:

```
$ zotpilot upgrade --check
  Installed: 0.5.0
  Latest:    0.5.3
Update available: 0.5.0 → 0.5.3
```

That "update" is a different lineage, not a newer revision — and it is what triggered the
false alarm above. `_detect_cli_installer` (`src/zotpilot/_platforms.py:1086`) returns
`editable` only for a dev checkout; any other install falls through to `pip`, and
`cmd_update` then runs `pip install --upgrade zotpilot`, **replacing the fork with
upstream**. Update with the fork install instead:

```bash
pip install --upgrade --force-reinstall git+https://github.com/EconGeo/ZotPilot.git
```

**Fixed in the fork as of `b13bf83`.** `upgrade` now follows the install's recorded source:
a VCS install reinstalls from its own `git+` URL, an editable install is told to `git pull`,
and PyPI is queried only when the install actually came from PyPI. On a fixed build
`upgrade --check` prints no `Latest:` number — that is how to tell a fixed build from an
older one, which is still dangerous and must not be run.

To refresh after the fork's skills change, run:

```bash
scripts/sync-zotpilot-skills.sh
```

It sparse-fetches only `claude-skills/` from the fork (no connector), overwrites this
directory, and prints the new source commit. Update the commit line above when you do.
