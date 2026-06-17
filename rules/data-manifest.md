# Data Provenance Rule: data_manifest.md

Every project maintains a `data/raw/data_manifest.md` — a strict, always-current table that records where every raw data file came from, how it was acquired, and which variables are used. This manifest is the audit trail linking every number in the paper to a citable, reproducible source.

**Problem this solves:** Raw data files that exist without traceable acquisition scripts make it impossible to recreate the data pipeline from scratch, verify what variables were extracted, or satisfy journal replication requirements. The manifest closes this gap.

---

## Required Location

```
data/raw/data_manifest.md
```

Every project directory that contains a `data/raw/` folder must have this file. Installed automatically by `apply.sh` at `data/raw/data_manifest.md`. If missing, copy it from the research-claude `templates/data_manifest.md`.

---

## Manifest Table Format

The manifest is a markdown table with exactly these 8 columns:

| Column | Description |
|--------|-------------|
| `Dataset` | Human-readable name (e.g., "National Zoning Atlas") |
| `Variables Used` | Comma-separated list of key variables drawn from this source |
| `Local Path` | Relative path from project root (e.g., `data/raw/nza/nza_cbsa_baseline.csv`) |
| `Source URL / Vendor` | Full URL or vendor name + database (e.g., `https://zoneomics.com/api`, `WRDS/Compustat`) |
| `Acquisition Script` | Relative path to script (e.g., `scripts/acquire/01_download_nza.py`) or `manual` |
| `Date Acquired` | ISO date (YYYY-MM-DD) |
| `Access Type` | `free` / `api-key` / `restricted` / `manual-download` |
| `Notes` | Known issues, version, coverage limitations |

### Example Row

| Dataset | Variables Used | Local Path | Source URL / Vendor | Acquisition Script | Date Acquired | Access Type | Notes |
|---------|---------------|------------|--------------------|--------------------|---------------|-------------|-------|
| National Zoning Atlas | wrluri, zoning_class, cbsa | data/raw/nza/nza_cbsa_2020.csv | https://nationalzoningatlas.org | scripts/acquire/01_download_nza.py | 2024-03-15 | free | Coverage: 49 states; excludes Hawaii |

---

## Trigger Events (Manifest Update Required)

A manifest update is **mandatory** whenever any of the following occur:

1. Writing a new acquisition script in `scripts/acquire/`
2. Adding a new file to `data/raw/` by any means
3. Referencing a new file path in a `cache.extra` block
4. Referencing a new file path in a `read_csv(here(...))` / `pd.read_csv(...)` call
5. Discovering a new dataset during analysis
6. Changing the source URL, vendor, or script for an existing dataset

Writing an acquisition script and updating the manifest are a **single atomic action** — not two separate steps. The manifest entry must exist before the acquisition script is committed.

---

## Hard Prohibitions

These violations are never acceptable:

- **No `cache.extra` file path without a manifest entry.** Every file listed in `cache.extra` must have a row.
- **No `read_csv(here("data/raw/..."))` without a manifest entry.** Every raw file read in analysis must have a row.
- **No commit of a new file in `data/raw/` without a manifest update.** The manifest and the file travel together.
- **No manifest row with `Acquisition Script = manual` without a `Notes` entry** explaining how to re-obtain the file manually.

---

## Audit Chain

To trace any number in the paper back to a source:

1. Find the inline `r` expression or hardcoded value in `manuscript.qmd`
2. Find the chunk that produces the object — follow `dependson` links
3. Find the `read_csv(here("data/raw/..."))` or `cache.extra` path in the data-loading chunk
4. Look up that path in `data/raw/data_manifest.md`
5. Follow `Acquisition Script` to the script or `Source URL / Vendor` to the origin

If any step in this chain is broken, the paper cannot be reproduced. The manifest is the link between steps 3 and 4.

---

## Enforcement Matrix

| Agent | Checks | Action on Violation |
|-------|--------|-------------------|
| **coder-critic** | INV-23: every `cache.extra` / `read_csv(here("data/raw/..."))` path has a manifest entry | −10 per missing entry |
| **verifier** | INV-24: `data/raw/data_manifest.md` exists and has at least one entry | FAIL |
| **data-engineer** | Must update manifest as part of any data acquisition work | Required output |

---

## Relation to Other Rules

- `quarto-empirical.md` — write gate item 3 requires manifest completeness before rendering
- `content-invariants.md` — INV-23 (manifest coverage) and INV-24 (manifest existence)
- `permissions.md` — data-engineer PRODUCES includes manifest updates
