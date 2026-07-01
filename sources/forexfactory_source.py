#!/usr/bin/env python3
"""
forexfactory_source.py

Fetches and filters the free Forex Factory economic calendar feed.
Normalizes events into the same shape as central_bank_source.py so both
can be merged by build_calendar.py.

This module is INTENTIONALLY separate from the central bank logic --
Forex Factory changes constantly (near-term data releases), central bank
dates change rarely (a handful of updates per year). Keeping them in
separate files means updating one never risks breaking the other.

Can be run standalone for testing:
    python3 forexfactory_source.py
"""

import json
import urllib.request
from datetime import datetime, timezone

FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

WANTED_CURRENCIES = {"AUD", "CAD", "EUR", "JPY", "GBP", "USD"}
WANTED_IMPACT = {"High", "Medium", "Low", "Holiday"}


def parse_event_datetime(date_str: str) -> datetime:
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        return datetime.fromisoformat(date_str)


def get_events() -> list[dict]:
    """Returns a list of normalized events:
    { 'title', 'country', 'date' (ISO8601 UTC string), 'impact', 'forecast',
      'previous', 'source' }
    """
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw_events = json.loads(resp.read().decode("utf-8"))

    normalized = []
    for ev in raw_events:
        if ev.get("country") not in WANTED_CURRENCIES:
            continue
        if ev.get("impact") not in WANTED_IMPACT:
            continue

        try:
            dt_utc = parse_event_datetime(ev["date"]).astimezone(timezone.utc)
        except Exception:
            continue  # skip malformed entries (e.g. odd all-day holiday dates)

        normalized.append(
            {
                "title": ev.get("title", "Untitled event"),
                "country": ev.get("country", ""),
                "date": dt_utc.isoformat(),
                "impact": ev.get("impact", ""),
                "forecast": ev.get("forecast", ""),
                "previous": ev.get("previous", ""),
                "source": "Forex Factory (free feed)",
                "note": "",
            }
        )

    return normalized


if __name__ == "__main__":
    evs = get_events()
    print(f"Fetched {len(evs)} filtered Forex Factory events:")
    for e in evs:
        print(f"  {e['date']}  {e['country']}  {e['title']}")
