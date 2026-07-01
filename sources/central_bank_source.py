#!/usr/bin/env python3
"""
central_bank_source.py

Loads static central bank meeting dates from central_bank_dates.json and
normalizes them into the same event shape used by forexfactory_source.py,
so the two can be merged by build_calendar.py.

This module is INTENTIONALLY separate from the Forex Factory logic. To
update central bank dates, edit central_bank_dates.json -- you should
never need to touch this .py file for a routine date update.

Can be run standalone for testing:
    python3 central_bank_source.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

DATA_FILE = Path(__file__).parent / "central_bank_dates.json"


def load_central_bank_events() -> list[dict]:
    """Returns a list of normalized events:
    { 'title', 'country', 'date' (ISO8601 UTC string), 'impact', 'forecast',
      'previous', 'source' }
    matching the shape produced by forexfactory_source.get_events(), so
    build_calendar.py can merge the two lists without special-casing either.

    Placeholder entries (date == 'PLACEHOLDER') are silently skipped, with
    a warning printed to stderr so broken/incomplete data is visible in
    CI logs without crashing the whole pipeline.
    """
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    events = []
    for ev in data.get("events", []):
        if ev.get("date") == "PLACEHOLDER":
            import sys
            print(
                f"[central_bank_source] WARNING: skipping unfilled placeholder "
                f"for {ev.get('bank')} ({ev.get('country')}) -- {ev.get('note','')}",
                file=sys.stderr,
            )
            continue

        try:
            dt = datetime.strptime(
                f"{ev['date']} {ev['time_utc']}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)
        except (ValueError, KeyError) as e:
            import sys
            print(
                f"[central_bank_source] WARNING: could not parse entry {ev}: {e}",
                file=sys.stderr,
            )
            continue

        events.append(
            {
                "title": f"{ev['bank']} Interest Rate Decision",
                "country": ev["country"],
                "date": dt.isoformat(),
                "impact": "High",  # all central bank rate decisions treated as High
                "forecast": "",
                "previous": "",
                "source": f"{ev['bank']} official calendar",
                "note": ev.get("note", ""),
            }
        )

    return events


if __name__ == "__main__":
    evs = load_central_bank_events()
    print(f"Loaded {len(evs)} confirmed central bank events:")
    for e in evs:
        print(f"  {e['date']}  {e['country']}  {e['title']}  ({e['note']})")
