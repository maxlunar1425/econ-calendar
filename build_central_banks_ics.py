#!/usr/bin/env python3
"""
build_central_banks_ics.py

Orchestrator: pulls central bank rate decision events only (FOMC, ECB,
BOE, BOC, RBA, BOJ, SNB) and writes them to their OWN separate .ics
file, distinct from the Forex Factory calendar. This lets you subscribe
to it as a separate Outlook calendar with its own color.

This file contains NO fetching or filtering logic of its own -- that
lives in sources/central_bank_source.py. ICS-building logic lives in
ics_utils.py (shared across all calendar builders in this project).

Usage:
    python3 build_central_banks_ics.py
Produces:
    ./output/central_banks_calendar.ics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sources"))
from central_bank_source import load_central_bank_events as get_cb_events  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from ics_utils import dedupe, build_ics  # noqa: E402

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "central_banks_calendar.ics"

NAMESPACE = "central-banks-calendar"
CALENDAR_NAME = "Central Bank Rate Decisions"


def main():
    cb_events = get_cb_events()
    print(f"Central banks: {len(cb_events)} events")

    all_events = dedupe(cb_events, NAMESPACE)
    all_events.sort(key=lambda e: e["date"])

    ics_text = build_ics(all_events, CALENDAR_NAME, NAMESPACE)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(ics_text, encoding="utf-8")

    print(f"Wrote {len(all_events)} total events to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
