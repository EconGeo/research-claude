# Data Manifest — [Project Name]

Provenance registry for all raw data files. Every file in `data/raw/` must have a row here.
Update this file whenever a new file is added to `data/raw/` or an acquisition script is written.
See `.claude/rules/data-manifest.md` for the full protocol.

| Dataset | Variables Used | Local Path | Source URL / Vendor | Acquisition Script | Date Acquired | Access Type | Notes |
|---------|---------------|------------|--------------------|--------------------|---------------|-------------|-------|
| <!-- Example: National Zoning Atlas --> | <!-- wrluri, zoning_class, cbsa --> | <!-- data/raw/nza/nza_cbsa_2020.csv --> | <!-- https://nationalzoningatlas.org --> | <!-- scripts/acquire/01_download_nza.py --> | <!-- 2024-03-15 --> | <!-- free --> | <!-- Coverage: 49 states; excludes Hawaii --> |
