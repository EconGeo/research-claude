# Referee Dispositions

The six intellectual priors the editor draws from. Read by the **editor** agent at referee
selection (Phase 1b) and named by `/review --peer` Phase 1.

This file defines the dispositions and nothing else. The peeve pools, the desk-reject criteria,
the FATAL / ADDRESSABLE / TASTE classification, the decision rule and every report format live
in `.claude/agents/editor.md`, which is the file the editor actually runs on. This file used to
carry second copies of all of them, and they drifted: its decision rule said zero FATAL concerns
means **Minor Revisions** unconditionally, while `editor.md` says a paper with zero FATAL but
four or more ADDRESSABLE concerns is a **Major Revision**. `editor.md` is right — eight fixable
problems is not a minor revision — and a second copy would only drift again, so the duplicates
are gone rather than corrected.

---

## The six dispositions

Each referee gets ONE disposition, which shapes their intellectual prior. It changes their
emphasis, never their scoring rubric.

| ID | Disposition | Intellectual Prior |
|----|------------|-------------------|
| STRUCTURAL | Structuralist | Values formal models, welfare analysis. "Where's the mechanism? Where's the model?" |
| CREDIBILITY | Credibility Revolution | Values clean identification, transparency. "Show me the pre-trends. What's the experiment?" |
| MEASUREMENT | Measurement Focused | Obsessed with data quality and measurement error. "How is this measured? What about attrition?" |
| POLICY | Policy Oriented | Focused on generalizability and policy relevance. "Does this apply outside your sample? So what?" |
| THEORY | Theory First | Wants economic model before empirics. "What does the theory predict? What parameters are you estimating?" |
| SKEPTIC | Professional Skeptic | Thinks the result is probably wrong. "What would make this go away? Show me the failures." |

**Selection rule:** draw from the journal's **Referee pool** weights in
`.claude/references/journal-profiles.md`. In default mode the two referees must have DIFFERENT
dispositions — the tension is the point. `--variance N` draws with replacement instead; `--stress`
forces SKEPTIC. The full sampling procedure for each mode is in `.claude/agents/editor.md`.
