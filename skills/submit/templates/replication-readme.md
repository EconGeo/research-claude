# Data and Code Availability Statement

## Overview

[Brief description of the replication package]

## Data Availability

| Data Source | Access | Location | Notes |
|-------------|--------|----------|-------|
| [Source] | [Public/Restricted] | [URL/path] | [How to obtain] |

## Computational Requirements

- **Software:** R [version] / Python [version]
- **Packages:** [list with versions]
- **Hardware:** [approximate runtime, memory requirements]
- **OS:** [tested on]

## Description of Programs

| Step | Input | Output | Description |
|------|-------|--------|-------------|
| `scripts/acquire/*` | external sources | `data/raw/` | Data acquisition (see `data/raw/data_manifest.md`) |
| `quarto render <manuscript>` | `data/raw/`, manuscript chunks | rendered manuscript | The one build step — wrangling, estimation and output generation all happen inside the manuscript's cached chunks, traceable by `tbl-`/`fig-` chunk label |

## Instructions for Replication

1. Install required packages: `[command]`
2. Place raw data in `data/raw/` (see Data Availability above), or run `scripts/acquire/*` to fetch it
3. Run `quarto render <manuscript>` — the one build step
4. Output appears inline in the rendered manuscript, traceable to `tbl-`/`fig-` chunk labels

## References

[If using others' data, cite it here]
