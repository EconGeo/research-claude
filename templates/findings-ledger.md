# Finding ledger

Written only by `pipeline.py ledger` (spec §6). One row per critic or referee finding. Status:
`open` · `closed <sha>` · `closed pending` (fixed while review was stale; settled to the commit
that ends the stale window) · `declined: <reason>` · `proposal: pending|accepted|rejected`.
A finding labelled `[missed-earlier]` was raised in a later round on text an earlier round passed.
`guard` names the `stopifnot()` guard that now checks a closed finding, when one does.

| id | created | creator | report | location | finding | status | guard |
|---|---|---|---|---|---|---|---|
