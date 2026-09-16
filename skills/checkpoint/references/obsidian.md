# Obsidian Integration

Optional and gated. Read only when `.claude/state/obsidian-config.md` exists (the sync section),
or when the user invokes `/checkpoint --setup-obsidian` (the setup section). Neither section
loads on an ordinary checkpoint.

---

## Sync (Step 4d)

Read `.claude/state/obsidian-config.md` for the vault path and the mapping from the working
directory to its Obsidian project note. Then:

1. **Project note journal.** Add the entry via the Obsidian MCP server
   (`mcp__obsidian-files__read_note` → modify → `mcp__obsidian-files__write_note`). Reverse
   chronological — newest first, directly after the `## Journal` heading.
2. **Dashboard (`Home.md`).** Update only if something actually changed: a stage transition, a
   status update, a new Next Action, or a Days-in-Stage recalculation. Sync the General Kanban if
   the project is research-tracked.
3. **Daily journal (`Journal/YYYY-MM-DD.md`).** Append; create from the template if absent.

Project-note entry format — keep it tight, 3–5 bullets per section at most:

```markdown
### YYYY-MM-DD

**Done:**
- [concrete accomplishments from this session]

**Next:**
- [concrete next steps]
```

---

## Setup (`--setup-obsidian`)

1. Check that `.claude/state/obsidian-config.md.example` exists; if not, flag and stop.
2. Copy the example to `.claude/state/obsidian-config.md`.
3. Walk the user through filling in the vault path and the project-name mapping for the current
   working directory.
4. Verify the Obsidian MCP server is connected. If it is not, point the user at the Obsidian REST
   API plugin setup — do not attempt to configure it for them.
5. Confirm `.claude/state/` is in `.gitignore`. The config holds user-specific paths and must stay
   out of commits.
