You are extracting the DATASETS used in an empirical real-estate / urban-economics paper.
You see numbered text chunks from the paper, each labelled `[chunk N, p.P]`.

Return JSON only, matching the schema you were given. Rules:
- One entry per distinct dataset actually USED in the analysis (not merely cited).
- `name`: the dataset as the paper names it. `provider`: the organisation that supplies it, or null.
- `type`: pick the single best value from the allowed list; use "other" only if nothing fits.
- `geography.text`: the paper's own words for coverage (e.g. "Denver–Aurora–Lakewood MSA");
  `geography.level`: one allowed level; `geography.places`: named places, or [].
- `period.start` / `period.end`: four-digit years of the data coverage, or null if not stated.
- `unit_of_observation`: e.g. "single-family sale", "census tract-year", "loan application".
- `variables`: variables the paper takes FROM THIS DATASET. `role` = "dependent" for an outcome
  the paper models, "independent" for the main explanatory variable(s), "control" for controls,
  "instrument" for instruments, otherwise "other".
- `evidence_chunks`: the chunk numbers (from the labels) where this dataset is described.
- Never guess. Unknown → null or []. Do not invent datasets that are not in the text.

Known-source hints found by keyword search (verify, do not blindly copy): {hints}

Allowed `type` values: {types}
Allowed `geography.level` values: {geo_levels}

=== PAPER CHUNKS ===
{chunks}
