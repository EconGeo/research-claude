# Improvement ledger

Append-only. Written by `/checkpoint` (one row per pipeline improvement candidate), read by `/promote`. A target named by 2 distinct projects is flagged REPEATED by `.claude/scripts/ledger.py show`. Status is `open`, `landed <sha>` or `declined: <reason>`. Notes are generic — no dataset, journal or paper nouns; this repo is public.

| id | date | project | target | note | status |
|---|---|---|---|---|---|
