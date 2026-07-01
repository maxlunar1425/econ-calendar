#!/usr/bin/env python3
"""
build_forexfactory_ics.py

Orchestrator: pulls Forex Factory events only and writes them to their
OWN separate .ics file, distinct from the central bank calendar. This
lets you subscribe to it as a separate Outlook calendar with its own
color.

This file contains NO fetching or filtering logic of its own -- that
lives in sources/forexfactory_source.py. ICS-building logic lives in
ics_utils.py (shared across all calendar builders in this project).

Usage:
    python3 build_forexfactory_ics.py
Produces:
    ./output/forexfactory_calendar.ics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sources"))
from forexfactory_source import get_events as get_ff_events  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from ics_utils import dedupe, build_ics  # noqa: E402

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "forexfactory_calendar.ics"

NAMESPACE = "forexfactory-calendar"
CALENDAR_NAME = "Forex Factory (High/Medium Impact)"


def main():
    ff_events = get_ff_events()
    print(f"Forex Factory: {len(ff_events)} events")

    all_events = dedupe(ff_events, NAMESPACE)
    all_events.sort(key=lambda e: e["date"])

    ics_text = build_ics(all_events, CALENDAR_NAME, NAMESPACE)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(ics_text, encoding="utf-8")

    print(f"Wrote {len(all_events)} total events to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
