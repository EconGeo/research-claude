# Logging

## Session Report
Append to `SESSION_REPORT.md` at end of session or before context compression.
**Rules:** Append only. Bullet points. Include file paths and commit hashes when available.
Create the file if it doesn't exist: `# Session Report — [Project Name]`

**Other writers and readers.** `/checkpoint` appends the session entry.
`.claude/hooks/pre-compact.py` appends a compaction marker in the same format and reads the
`**Decisions:**` block of the latest entry; `.claude/hooks/post-compact-restore.py` surfaces
the latest entry's heading after compaction; `.claude/hooks/log-reminder.py` nudges when the
file is missing or stale. **This is the only session-continuity document the hooks read** —
there is deliberately no session-log directory. `.claude/rules/session-handoff.md` explains why: the
continuity design is already complete, and "the fix is not another document."

**Where it lives:** the project root, unless the project's own `CLAUDE.md` relocates it (this
repo puts it at `docs/SESSION_REPORT.md`). The hooks check the root first, then `docs/`.

**Entry format:**
```markdown
## YYYY-MM-DD HH:MM — [Brief Title]

**Operations:**
- [Scripts run, files created/modified/deleted]

**Decisions:**
- [Choice made] — [rationale]

**Results:**
- [Key findings, outputs produced]

**Commits:**
- `[hash]` [commit message]

**Status:**
- Done: [what's complete]
- Pending: [what remains]
```

## Research Journal
Append to `quality_reports/research_journal.md` whenever an agent completes work — writing code, drafting a section, producing a review, making an editorial decision, or transitioning between phases.
**Rules:** Append only. One entry per agent invocation. Include phase transitions and editorial decisions.

**Entry format:**
```markdown
### YYYY-MM-DD HH:MM — [Agent Name]
**Phase:** [Discovery/Strategy/Execution/Peer Review/Presentation]
**Target:** [file or topic]
**Score:** [XX/100 or PASS/FAIL or N/A]
**Verdict:** [one line — key finding or decision]
**Report:** [path to full report]
```
**Why it exists:** Agents read this to understand pipeline state — the editor checks what strategist-critic scored, `/pipeline` checks which agents have cleared their gates, the coder-critic checks what the coder built. It's the shared context across agents.

Agent outputs (reports, scripts, memos, decisions) are saved to `quality_reports/` by the skills that produce them.

## Pipeline State

`quality_reports/pipeline_state.json` is the machine-readable record of scores and progress.
Schema: `.claude/templates/pipeline-state.json` (v2). Written only by
`python3 .claude/scripts/pipeline.py state ...`; read by `pipeline.py score`, `/pipeline`,
`/checkpoint` (staleness sweep) and `.claude/hooks/post-compact-restore.py`. **Committed** — it is
replication provenance. The research journal entry is derived from it, never the reverse.

## Dispatch Log

`quality_reports/agent_dispatch.jsonl` — one JSON line per subagent completion, written by
`.claude/hooks/dispatch-log.py` (SubagentStop) or by `pipeline.py log <agent>` from a standalone
skill. `pipeline.py post` reads it to prove the critic ran. **Gitignored** — session mechanics.

## Learning Loop

Owned by `.claude/rules/meta-governance.md`: `/pipeline` surfaces suggested learnings from the
state file and dispatch log; the user approves; `/promote` lands them.
