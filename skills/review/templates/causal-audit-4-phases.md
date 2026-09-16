# Causal Audit — 4-Phase Protocol

Read by strategist-critic for `/review --methods` and for the comprehensive review's
causal-design audit.

---

## 4-Phase Econometrics Review Protocol

**Phase 1: Claim Identification**
- What causal design is used? (DiD, IV, RDD, Synthetic Control, Event Study, etc.)
- What is the estimand? (ATT, ATE, LATE, ITT, etc.)
- What is the treatment? What is the control?
- Is the design clearly stated and internally consistent?

**Phase 2: Core Design Validity**
- Design-specific assumption check:
  - **DiD:** Parallel trends (pre-trends test, event study plot), no anticipation, stable composition
  - **IV:** Relevance (first stage F), exclusion restriction, monotonicity
  - **RDD:** Continuity, no manipulation (McCrary/density test), bandwidth sensitivity
  - **Synthetic Control:** Pre-treatment fit, donor pool selection, no interference
  - **Event Study:** Clean identification of event timing, no confounding events, appropriate window
- Sanity check: Are the sign, magnitude, and dynamics of the estimates plausible?
- **EARLY STOPPING:** If Phase 2 finds CRITICAL issues, focus there instead of continuing to Phases 3-4. A broken design invalidates everything downstream.

**Phase 3: Inference**
- Standard error clustering: Is the clustering level appropriate for the design?
- Multiple testing: Are p-values adjusted when testing multiple outcomes?
- Code-theory alignment: Does the code actually implement what the paper describes?
- Wild bootstrap or other small-sample corrections when needed?

**Phase 4: Polish and Completeness**
- Robustness checks: Alternative specifications, placebo tests, sensitivity analysis
- Sensitivity bounds: Oster (2019), Rambachan & Roth (2023), or equivalent
- Citation fidelity: Are methodological citations accurate?
- Are limitations honestly discussed?

---

## Overall Assessment Scale

- **SOUND** — Design is valid, implementation is correct
- **MINOR ISSUES** — Fixable concerns, none threatening core results
- **MAJOR ISSUES** — Significant concerns that could change conclusions
- **CRITICAL ERRORS** — Fundamental design flaw or incorrect implementation

The label is reported beside the score, not instead of it. The score is 100 minus the fixed
per-severity deductions in `.claude/skills/review/config/scoring-rubrics.md` (Strategist-Critic).
