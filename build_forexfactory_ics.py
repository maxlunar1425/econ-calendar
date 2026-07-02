#!/usr/bin/env python3
"""
build_forexfactory_ics.py

Orchestrator: reads the accumulated Forex Factory history (see
build_forexfactory_history.py -- run that FIRST, on a schedule, since it
does the actual live fetching and 30-day accumulation) and writes it to
its own separate .ics file, distinct from the central bank calendar.
This lets you subscribe to it as a separate Outlook calendar with its
own color.

This file contains NO fetching or filtering logic of its own -- that
lives in sources/forexfactory_source.py (live fetch) and
build_forexfactory_history.py (accumulation/pruning). ICS-building logic
lives in ics_utils.py (shared across all calendar builders in this
project).

Usage:
    python3 build_forexfactory_ics.py
Produces:
    ./output/forexfactory_calendar.ics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sources"))
from forexfactory_history_source import load_forexfactory_events as get_ff_events  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from ics_utils import dedupe, build_ics  # noqa: E402

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "forexfactory_calendar.ics"

NAMESPACE = "forexfactory-calendar"
CALENDAR_NAME = "Forex Factory (High/Medium Impact)"


def main():
    ff_events = get_ff_events()
    print(f"Forex Factory (accumulated history): {len(ff_events)} events")

    # day-level UID granularity: many distinct FF events share the same
    # title+country across different days within a month (e.g. recurring
    # monthly releases), unlike month-level granularity used for central
    # banks -- see the UID rule in MAINTENANCE.md / REBUILD_PROMPT.md
    for ev in ff_events:
        ev["uid_granularity"] = "day"

    all_events = dedupe(ff_events, NAMESPACE)
    all_events.sort(key=lambda e: e["date"])

    ics_text = build_ics(all_events, CALENDAR_NAME, NAMESPACE)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(ics_text, encoding="utf-8")

    print(f"Wrote {len(all_events)} total events to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
