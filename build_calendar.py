#!/usr/bin/env python3
"""
build_calendar.py

Orchestrator: pulls events from Forex Factory + static central bank
dates, merges and de-duplicates them, and writes the main economic
calendar .ics file.

This file contains NO fetching or filtering logic of its own -- that
lives in sources/forexfactory_source.py and sources/central_bank_source.py.
ICS-building logic lives in ics_utils.py (shared with build_data_releases_ics.py).
This file only merges and writes output.

Data releases (BLS/BEA CPI, PPI, PCE) are DELIBERATELY NOT included here
-- see build_data_releases_ics.py, which produces a separate .ics file so
it can be subscribed to as its own Outlook calendar with its own color.

Usage:
    python3 build_calendar.py
Produces:
    ./output/economic_calendar.ics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sources"))
from forexfactory_source import get_events as get_ff_events          # noqa: E402
from central_bank_source import load_central_bank_events as get_cb_events  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from ics_utils import dedupe, build_ics  # noqa: E402

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "economic_calendar.ics"

NAMESPACE = "econ-calendar"
CALENDAR_NAME = "Economic Calendar (High Impact)"


def main():
    ff_events = get_ff_events()
    print(f"Forex Factory: {len(ff_events)} events")

    cb_events = get_cb_events()
    print(f"Central banks: {len(cb_events)} events")

    all_events = dedupe(ff_events + cb_events, NAMESPACE)
    all_events.sort(key=lambda e: e["date"])

    ics_text = build_ics(all_events, CALENDAR_NAME, NAMESPACE)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(ics_text, encoding="utf-8")

    print(f"Wrote {len(all_events)} total events to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
