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
import sys
from datetime import date, datetime, timezone
from pathlib import Path

DATA_FILE = Path(__file__).parent / "central_bank_dates.json"
STALENESS_THRESHOLD_DAYS = 90

# Maps bank name -> key in the JSON's "sources" dict, so each event's
# "source" field can carry the actual clickable URL rather than plain text.
BANK_TO_SOURCE_KEY = {
    "FOMC": "USD_FOMC",
    "ECB": "EUR_ECB",
    "BOE": "GBP_BOE",
    "BOC": "CAD_BOC",
    "RBA": "AUD_RBA",
    "BOJ": "JPY_BOJ",
}


def check_staleness(data: dict) -> None:
    """Warns (does not fail the build) if central_bank_dates.json hasn't
    been reviewed against official sources in a while. This is the closest
    thing to an 'automatic change detector' this module has -- it can't
    know if a bank actually changed a date, but it can make sure a human
    re-checks periodically instead of the file silently going stale."""
    last_verified_str = data.get("last_verified")
    if not last_verified_str:
        print(
            "[central_bank_source] WARNING: no 'last_verified' field found in "
            "central_bank_dates.json -- add one (YYYY-MM-DD) to enable staleness checks.",
            file=sys.stderr,
        )
        return

    try:
        last_verified = datetime.strptime(last_verified_str, "%Y-%m-%d").date()
    except ValueError:
        print(
            f"[central_bank_source] WARNING: could not parse last_verified "
            f"'{last_verified_str}' -- expected YYYY-MM-DD.",
            file=sys.stderr,
        )
        return

    days_stale = (date.today() - last_verified).days
    if days_stale > STALENESS_THRESHOLD_DAYS:
        print(
            f"[central_bank_source] WARNING: central_bank_dates.json was last "
            f"verified {days_stale} days ago ({last_verified_str}). Central banks "
            f"occasionally reschedule meetings -- re-check the official source "
            f"links in this file and bump 'last_verified' once confirmed.",
            file=sys.stderr,
        )


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

    check_staleness(data)
    sources_map = data.get("sources", {})

    events = []
    for ev in data.get("events", []):
        if ev.get("date") == "PLACEHOLDER":
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
            print(
                f"[central_bank_source] WARNING: could not parse entry {ev}: {e}",
                file=sys.stderr,
            )
            continue

        source_key = BANK_TO_SOURCE_KEY.get(ev.get("bank"))
        source_url = sources_map.get(source_key, f"{ev.get('bank')} official calendar")

        events.append(
            {
                "title": f"{ev['bank']} Interest Rate Decision",
                "country": ev["country"],
                "date": dt.isoformat(),
                "impact": "High",  # all central bank rate decisions treated as High
                "forecast": "",
                "previous": "",
                "source": source_url,
                "note": ev.get("note", ""),
            }
        )

    return events


if __name__ == "__main__":
    evs = load_central_bank_events()
    print(f"Loaded {len(evs)} confirmed central bank events:")
    for e in evs:
        print(f"  {e['date']}  {e['country']}  {e['title']}  ({e['note']})")
