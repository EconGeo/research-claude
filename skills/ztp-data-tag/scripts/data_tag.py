#!/usr/bin/env python
"""CLI entry. Run with: micromamba run -n zotpilot python skills/ztp-data-tag/scripts/data_tag.py …"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_tag.cli import main  # noqa: E402
if __name__ == "__main__":
    r = main()
    sys.exit(0 if isinstance(r, dict) else r)
