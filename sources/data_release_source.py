#!/usr/bin/env python3
"""
data_release_source.py

Loads statistical data release dates from data_releases.json and
normalizes them into the same event shape used by forexfactory_source.py
and central_bank_source.py, so build_calendar.py can merge all three.

This is INTENTIONALLY a separate module from central_bank_source.py:
data releases (CPI, PPI, PCE) are not rate decisions, and titling them
correctly matters -- this module uses each release's own name (e.g.
"USD - Consumer Price Index") rather than a generic "Interest Rate
Decision" label.

Can be run standalone for testing:
    python3 data_release_source.py
"""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data_releases.json"
STALENESS_THRESHOLD_DAYS = 90


def check_staleness(data: dict) -> None:
    last_verified_str = data.get("last_verified")
    if not last_verified_str:
        print(
            "[data_release_source] WARNING: no 'last_verified' field found in "
            "data_releases.json.",
            file=sys.stderr,
        )
        return

    try:
        last_verified = datetime.strptime(last_verified_str, "%Y-%m-%d").date()
    except ValueError:
        print(
            f"[data_release_source] WARNING: could not parse last_verified "
            f"'{last_verified_str}' -- expected YYYY-MM-DD.",
            file=sys.stderr,
        )
        return

    days_stale = (date.today() - last_verified).days
    if days_stale > STALENESS_THRESHOLD_DAYS:
        print(
            f"[data_release_source] WARNING: data_releases.json was last "
            f"verified {days_stale} days ago ({last_verified_str}). Re-run "
            f"build_data_releases_json.py.",
            file=sys.stderr,
        )


def load_data_release_events() -> list[dict]:
    """Returns a list of normalized events matching the shape produced by
    forexfactory_source.get_events() and central_bank_source.load_central_bank_events(),
    so build_calendar.py can merge all three without special-casing any of them.
    """
    if not DATA_FILE.exists():
        print(
            f"[data_release_source] No {DATA_FILE.name} found yet -- run "
            f"build_data_releases_json.py first. Returning no events.",
            file=sys.stderr,
        )
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    check_staleness(data)
    sources_map = data.get("sources", {})

    events = []
    for ev in data.get("events", []):
        try:
            dt = datetime.strptime(
                f"{ev['date']} {ev['time_utc']}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)
        except (ValueError, KeyError) as e:
            print(
                f"[data_release_source] WARNING: could not parse entry {ev}: {e}",
                file=sys.stderr,
            )
            continue

        agency = ev.get("bank", "")  # "BLS" or "BEA" -- field name kept
                                       # consistent with the other source
                                       # modules for easy merging
        release_title = ev.get("release", agency)
        source_url = sources_map.get(agency, f"{agency} official release calendar")

        events.append(
            {
                "title": release_title,
                "country": ev.get("country", "USD"),
                "date": dt.isoformat(),
                "impact": "High",  # CPI/PPI/PCE are all high-impact by convention
                "forecast": "",
                "previous": "",
                "source": source_url,
                "note": ev.get("note", ""),
            }
        )

    return events


if __name__ == "__main__":
    evs = load_data_release_events()
    print(f"Loaded {len(evs)} watched data release events:")
    for e in evs:
        print(f"  {e['date']}  {e['country']}  {e['title']}  ({e['note']})")
