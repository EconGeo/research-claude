# Data Manifest — [Project Name]

Provenance registry for all raw data files. Every file in `data/raw/` must have a row here.
Update this file whenever a new file is added to `data/raw/` or an acquisition script is written.
See `.claude/rules/data-manifest.md` for the full protocol.

| Dataset | Variables Used | Local Path | Source URL / Vendor | Acquisition Script | Date Acquired | Access Type | Notes |
|---------|---------------|------------|--------------------|--------------------|---------------|-------------|-------|
| <!-- Example: County Business Patterns --> | <!-- employment, naics, fips --> | <!-- data/raw/cbp/cbp_county_2020.csv --> | <!-- https://www.census.gov/programs-surveys/cbp.html --> | <!-- scripts/acquire/01_download_cbp.py --> | <!-- 2024-03-15 --> | <!-- free --> | <!-- Coverage: 50 states; suppressed cells flagged --> |
