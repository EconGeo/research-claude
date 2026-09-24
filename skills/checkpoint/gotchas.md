# Checkpoint Skill -- Gotchas

- Obsidian MCP must be connected for vault updates. If offline, checkpoint saves memory + SESSION_REPORT only.
- Convert relative dates to absolute dates in memory entries ("Thursday" --> "2026-05-09").
- Don't save code patterns or architecture to memory -- those are derivable from reading the code.
- Check existing memory files before creating new ones to avoid duplicates.
- SESSION_REPORT.md is append-only. Never overwrite existing entries.
- The research journal only gets an entry if agent work happened this session. Don't log empty sessions.
- Pipeline state JSON and research journal are complementary, not redundant. JSON is for `pipeline.py`; journal is for humans.
- Obsidian sync stays in the main context, on purpose (audit 2026-09-15 §3 P5 row, closed
  2026-09-24 as D4b). The MCP server name is user-configured in `.claude/state/obsidian-config.md`,
  so a shipped agent cannot declare `mcpServers:` for it without hardcoding a machine-specific
  name; and every `/checkpoint` runs as `--auto`, so there is no interactive cost to recover.
