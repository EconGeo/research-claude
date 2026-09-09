# Submit Skill -- Gotchas

- Submission requires overall >= 95 AND every component >= 80. A 96 average with one component at 75 fails.
- Journal formatting requirements override the pipeline's format rules (`quarto-pdf.md` / `quarto-word.md`). Check `journal-profiles.md`.
- AEA journals require no significance stars (INV-4) -- report SEs and CIs instead.
- Replication README must include computational requirements (runtime, memory). Reviewers test this.
- Cover letters should be brief (under 1 page). Don't summarize the entire paper.
- Verify the manuscript renders from a cold cache (`rm -rf *_cache`).
- The verifier is pass/fail (0 or 100). There is no partial credit.
- Don't generate submission materials for a failing paper -- fix the issues first.
