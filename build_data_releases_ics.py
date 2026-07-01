#!/usr/bin/env python3
"""
build_data_releases_ics.py

Orchestrator: pulls watched data release events (BLS/BEA -- CPI, PPI,
PCE) and writes them to their OWN separate .ics file, distinct from
economic_calendar.ics. This lets you subscribe to it as a separate
Outlook calendar with its own color, rather than merging it into the
main economic calendar.

This file contains NO fetching or filtering logic of its own -- that
lives in sources/data_release_source.py (which reads
sources/data_releases.json, produced by scrapers/build_data_releases_json.py).
ICS-building logic lives in ics_utils.py (shared with build_calendar.py).

Usage:
    python3 build_data_releases_ics.py
Produces:
    ./output/data_releases.ics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sources"))
from data_release_source import load_data_release_events as get_dr_events  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from ics_utils import dedupe, build_ics  # noqa: E402

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "data_releases.ics"

NAMESPACE = "data-releases-calendar"
CALENDAR_NAME = "Data Releases (BLS/BEA)"


def main():
    dr_events = get_dr_events()
    print(f"Data releases (BLS/BEA): {len(dr_events)} events")

    all_events = dedupe(dr_events, NAMESPACE)
    all_events.sort(key=lambda e: e["date"])

    ics_text = build_ics(all_events, CALENDAR_NAME, NAMESPACE)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(ics_text, encoding="utf-8")

    print(f"Wrote {len(all_events)} total events to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
