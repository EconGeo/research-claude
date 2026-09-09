# Permission Registry (rendered — do not edit)

Rendered from `rules/registry.yaml` by `scripts/render_registry.py`. `check_fork.sh`
fails if this file differs from the render. The YAML is what `pipeline.py`, the gate
and `/pipeline` read; this file exists so the registry is readable in a linked project.

**Limits:** 3 rounds per pair, 5 overall, 2 verification retries.

## Components

| Component | Weight | Scored by | Conditional |
|---|---|---|---|
| literature | 10 | lit-critic | no |
| data | 10 | explorer-critic | no |
| strategy | 25 | strategist-critic | no |
| theory | 20 | theorist-critic | yes |
| code | 15 | coder-critic | no |
| manuscript | 10 | writer-critic | no |
| referees | 25 | editor | no |
| replication | 5 | verifier | no |

## Agents

### lit-position

- **ROLE:** creator (skill) · **PARALLEL_GROUP:** discovery
- **REQUIRES:** nothing beyond the research idea
- **PRODUCES:**
  - `quality_reports/literature/*/annotated_bibliography.md`
  - `quality_reports/literature/*/frontier_map.md`
  - `quality_reports/literature/*/positioning.md`
  - paired critic completed after the creator, **and** the creator's component carries a score recorded after that completion (no component: log only) — *appended by `post`, not declared*
- **CRITIC:** lit-critic
- **ESCALATION_TARGET:** user
- **QUALITY_WEIGHT:** 10 (literature)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/literature/`

### lit-critic

- **ROLE:** critic (agent) · **PARALLEL_GROUP:** discovery
- **REQUIRES:** 
  - `quality_reports/literature/*/positioning.md` — produced by `/lit-position`
- **PRODUCES:**
  - `quality_reports/reviews/lit-critic_*.md`
- **CRITIC:** none
- **ESCALATION_TARGET:** user
- **QUALITY_WEIGHT:** 0 (literature)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/reviews/`

### explorer

- **ROLE:** creator (agent) · **PARALLEL_GROUP:** discovery
- **REQUIRES:** nothing beyond the research idea
- **PRODUCES:**
  - `quality_reports/data-assessment/*/data_sources.md`
  - `quality_reports/data-assessment/*/data_dictionary.md`
  - `quality_reports/data-assessment/*/access_instructions.md`
  - paired critic completed after the creator, **and** the creator's component carries a score recorded after that completion (no component: log only) — *appended by `post`, not declared*
- **CRITIC:** explorer-critic
- **ESCALATION_TARGET:** user
- **QUALITY_WEIGHT:** 10 (data)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/data-assessment/`

### explorer-critic

- **ROLE:** critic (agent) · **PARALLEL_GROUP:** discovery
- **REQUIRES:** 
  - `quality_reports/data-assessment/*/data_sources.md` — produced by `/discover data`
- **PRODUCES:**
  - `quality_reports/reviews/explorer-critic_*.md`
- **CRITIC:** none
- **ESCALATION_TARGET:** user
- **QUALITY_WEIGHT:** 0 (data)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/reviews/`

### strategist

- **ROLE:** creator (agent) · **PARALLEL_GROUP:** strategy
- **REQUIRES:** 
  - any of: `quality_reports/literature/*/positioning.md` — produced by `/lit-position`; `quality_reports/data-assessment/*/data_sources.md` — produced by `/discover data`
  - literature score ≥ 80 if the component has been scored — produced by `/lit-position`
  - data score ≥ 80 if the component has been scored — produced by `/discover data`
- **PRODUCES:**
  - `quality_reports/strategy/*/strategy_memo.md`
  - heading **Estimand** in `quality_reports/strategy/*/strategy_memo.md`
  - heading **Specification** in `quality_reports/strategy/*/strategy_memo.md`
  - heading **Assumptions** in `quality_reports/strategy/*/strategy_memo.md`
  - heading **Robustness Plan** in `quality_reports/strategy/*/strategy_memo.md`
  - heading **Threats** in `quality_reports/strategy/*/strategy_memo.md`
  - paired critic completed after the creator, **and** the creator's component carries a score recorded after that completion (no component: log only) — *appended by `post`, not declared*
- **CRITIC:** strategist-critic
- **ESCALATION_TARGET:** user
- **QUALITY_WEIGHT:** 25 (strategy)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/strategy/`

### strategist-critic

- **ROLE:** critic (agent) · **PARALLEL_GROUP:** strategy
- **REQUIRES:** 
  - `quality_reports/strategy/*/strategy_memo.md` — produced by `/strategize`
- **PRODUCES:**
  - `quality_reports/reviews/strategist-critic_*.md`
- **CRITIC:** none
- **ESCALATION_TARGET:** user
- **QUALITY_WEIGHT:** 0 (strategy)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/reviews/`

### theorist

- **ROLE:** creator (agent) · **PARALLEL_GROUP:** strategy
- **REQUIRES:** 
  - strategy score ≥ 80
- **PRODUCES:**
  - heading **Theory** in `manuscript`
  - `quality_reports/theory/*/theory_memo.md`
  - `quality_reports/theory/*/notation_glossary.md`
  - `quarto render` exit 0
  - paired critic completed after the creator, **and** the creator's component carries a score recorded after that completion (no component: log only) — *appended by `post`, not declared*
- **CRITIC:** theorist-critic
- **ESCALATION_TARGET:** user
- **QUALITY_WEIGHT:** 20 (theory)
- **CONDITIONAL:** yes
- **WRITES:** `manuscript`, `quality_reports/theory/`

### theorist-critic

- **ROLE:** critic (agent) · **PARALLEL_GROUP:** strategy
- **REQUIRES:** 
  - heading **Theory** in `manuscript` — produced by `/strategize theory`
- **PRODUCES:**
  - `quality_reports/reviews/theorist-critic_*.md`
- **CRITIC:** none
- **ESCALATION_TARGET:** user
- **QUALITY_WEIGHT:** 0 (theory)
- **CONDITIONAL:** yes
- **WRITES:** `quality_reports/reviews/`

### data-engineer

- **ROLE:** creator (agent) · **PARALLEL_GROUP:** execution
- **REQUIRES:** 
  - strategy score ≥ 80
- **PRODUCES:**
  - `data/raw/data_manifest.md`
  - `quarto render` exit 0
  - paired critic completed after the creator, **and** the creator's component carries a score recorded after that completion (no component: log only) — *appended by `post`, not declared*
- **CRITIC:** coder-critic
- **ESCALATION_TARGET:** strategist-critic
- **QUALITY_WEIGHT:** 0 (code) — scored under code
- **CONDITIONAL:** no
- **WRITES:** `manuscript`, `data/raw/data_manifest.md`

### coder

- **ROLE:** creator (agent) · **PARALLEL_GROUP:** execution
- **REQUIRES:** 
  - strategy score ≥ 80
- **PRODUCES:**
  - ≥1 chunk(s) labelled `tbl-*`
  - ≥1 chunk(s) labelled `fig-*`
  - `quarto render` exit 0
  - `prose_number_check.py` exit 0
  - paired critic completed after the creator, **and** the creator's component carries a score recorded after that completion (no component: log only) — *appended by `post`, not declared*
- **CRITIC:** coder-critic
- **ESCALATION_TARGET:** strategist-critic
- **QUALITY_WEIGHT:** 15 (code)
- **CONDITIONAL:** no
- **WRITES:** `manuscript`

### coder-critic

- **ROLE:** critic (agent) · **PARALLEL_GROUP:** execution
- **REQUIRES:** 
  - ≥1 chunk(s) labelled `tbl-*` — produced by `/analyze`
- **PRODUCES:**
  - `quality_reports/reviews/coder-critic_*.md`
- **CRITIC:** none
- **ESCALATION_TARGET:** strategist-critic
- **QUALITY_WEIGHT:** 0 (code)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/reviews/`

### writer

- **ROLE:** creator (agent) · **PARALLEL_GROUP:** execution
- **REQUIRES:** 
  - code score ≥ 80
  - ≥1 chunk(s) labelled `tbl-*` — produced by `/analyze`
  - `quarto render` exit 0
- **PRODUCES:**
  - `quarto render` exit 0
  - `prose_number_check.py` exit 0
  - paired critic completed after the creator, **and** the creator's component carries a score recorded after that completion (no component: log only) — *appended by `post`, not declared*
- **CRITIC:** writer-critic
- **ESCALATION_TARGET:** user
- **QUALITY_WEIGHT:** 10 (manuscript)
- **CONDITIONAL:** no
- **WRITES:** `manuscript`

### writer-critic

- **ROLE:** critic (agent) · **PARALLEL_GROUP:** execution
- **REQUIRES:** 
  - `quarto render` exit 0 — produced by `/write`
- **PRODUCES:**
  - `quality_reports/reviews/writer-critic_*.md`
  - `quality_reports/reviews/claim_evidence_*.md`
- **CRITIC:** none
- **ESCALATION_TARGET:** user
- **QUALITY_WEIGHT:** 0 (manuscript)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/reviews/`

### editor

- **ROLE:** infrastructure (agent) · **PARALLEL_GROUP:** peer-review
- **REQUIRES:** 
  - manuscript score ≥ 80
  - code score ≥ 80
- **PRODUCES:**
  - `quality_reports/peer_review_*/desk_review.md`
  - `quality_reports/peer_review_*/editorial_decision.md`
- **CRITIC:** none
- **ESCALATION_TARGET:** user
- **QUALITY_WEIGHT:** 0 (referees)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/peer_review_`

### domain-referee

- **ROLE:** referee (agent) · **PARALLEL_GROUP:** peer-review
- **REQUIRES:** 
  - `quality_reports/peer_review_*/desk_review.md` — produced by `/review --peer`
- **PRODUCES:**
  - `quality_reports/peer_review_*/referee_domain.md`
- **CRITIC:** none
- **ESCALATION_TARGET:** editor
- **QUALITY_WEIGHT:** 12.5 (referees)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/peer_review_`

### methods-referee

- **ROLE:** referee (agent) · **PARALLEL_GROUP:** peer-review
- **REQUIRES:** 
  - `quality_reports/peer_review_*/desk_review.md` — produced by `/review --peer`
- **PRODUCES:**
  - `quality_reports/peer_review_*/referee_methods.md`
- **CRITIC:** none
- **ESCALATION_TARGET:** editor
- **QUALITY_WEIGHT:** 12.5 (referees)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/peer_review_`

### storyteller

- **ROLE:** creator (agent) · **PARALLEL_GROUP:** presentation
- **REQUIRES:** 
  - manuscript score ≥ 80
- **PRODUCES:**
  - `talks/*_talk.qmd`
  - `quarto render` exit 0 for `talks/*_talk.qmd`
  - paired critic completed after the creator, **and** the creator's component carries a score recorded after that completion (no component: log only) — *appended by `post`, not declared*
- **CRITIC:** storyteller-critic
- **ESCALATION_TARGET:** writer
- **QUALITY_WEIGHT:** 0 (none)
- **CONDITIONAL:** no
- **WRITES:** `talks/`

### storyteller-critic

- **ROLE:** critic (agent) · **PARALLEL_GROUP:** presentation
- **REQUIRES:** 
  - `talks/*_talk.qmd` — produced by `/talk`
- **PRODUCES:**
  - `quality_reports/reviews/storyteller-critic_*.md`
- **CRITIC:** none
- **ESCALATION_TARGET:** writer
- **QUALITY_WEIGHT:** 0 (none)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/reviews/`

### verifier

- **ROLE:** infrastructure (agent) · **PARALLEL_GROUP:** submission
- **REQUIRES:** 
  - overall score ≥ 95
- **PRODUCES:**
  - `quality_reports/verification_report.md`
  - `quarto render` exit 0
  - `prose_number_check.py` exit 0
- **CRITIC:** none
- **ESCALATION_TARGET:** user
- **QUALITY_WEIGHT:** 5 (replication)
- **CONDITIONAL:** no
- **WRITES:** `quality_reports/verification_report.md`
