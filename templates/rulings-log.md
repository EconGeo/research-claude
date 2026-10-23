# Rulings log

Written only by `pipeline.py ruling add` and by ledger decline/accept/reject (spec §0.8). Each row
is a decision a session made without the author, kept so it can be reversed cheaply. A ruling
never contradicts a decision the author recorded and never changes `design:`; those are
questions (`quality_reports/questions_for_author.md`).

| date | by | decision | alternative | reason |
|---|---|---|---|---|
