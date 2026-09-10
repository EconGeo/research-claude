# Revision Protocol — R&R Cycle

**When referee reports arrive, `/revise` classifies each comment and routes it to the right agent.**

## Comment Classification

| Classification | What It Means | Routed To |
|---------------|---------------|-----------|
| **NEW ANALYSIS** | Requires new estimation or data work | Coder, then coder-critic |
| **CLARIFICATION** | Text revision sufficient | Writer, then writer-critic |
| **DISAGREE** | Diplomatic pushback needed | Flagged for User review |
| **MINOR** | Typos, formatting | Writer, then writer-critic |
| **FATAL** | Invalidates a headline claim if correct | Stop; escalate to User before any drafting |

Each pairing above is declared in `.claude/rules/registry.yaml`; this column names who to dispatch, not a second source of truth for the pairing.

## The R&R Flow

```
Referee reports arrive (real, not simulated)
        │
        ▼
   /revise classifies each comment
        │
        ├── NEW ANALYSIS → Coder, then coder-critic → Writer updates
        ├── CLARIFICATION → Writer, then writer-critic
        ├── DISAGREE → User decides → diplomatic response drafted
        └── MINOR → Writer, then writer-critic
        │
        ▼
   Revised paper → writer-critic → pipeline.py post writer
        │
        ▼
   Response letter produced
```

Pairing per `.claude/rules/registry.yaml`; this diagram names dispatch order, not the pairing itself.

## Rules

- This uses the same agents but in a targeted way — not a full pipeline restart
- Each comment gets its own routing — a single referee report may trigger multiple agent pairs
- The response letter maps each referee comment to the specific change made
- DISAGREE items are always flagged for user review — Claude never autonomously pushes back on referees
- `/revise` tracks which comments are resolved in `quality_reports/referee_response_tracker.md`
