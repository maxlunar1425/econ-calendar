#!/usr/bin/env python3
"""
generate_economic_calendar_ics.py

Fetches the free Forex Factory economic calendar feed, filters it down to
High-impact events for a chosen set of countries/currencies, converts the
event times to a fixed UTC-4 offset, and writes an Outlook-subscribable
.ics file.

Data source (free, no API key, unofficial but widely used):
    https://nfs.faireconomy.media/ff_calendar_thisweek.json

Notes / limitations (read before relying on this):
  - The feed only reliably covers the CURRENT WEEK. There is no confirmed
    public "next month" or "next quarter" endpoint, so this script gives
    you a rolling near-term window, not a months-ahead calendar.
  - Forex Factory organizes events by CURRENCY, not country. France and
    Germany do not appear separately -- their events are bucketed under EUR
    along with the rest of the Euro Area.
  - The source is rate-limited by Forex Factory (roughly 2 requests per
    5 minutes per IP). Don't run this script more often than that.
  - Times are converted to a FIXED UTC-4 offset (not US Eastern with DST).
    If you want US Eastern with automatic DST handling instead, see the
    TARGET_TZ note below.

Usage:
    python3 generate_economic_calendar_ics.py
Produces:
    ./output/economic_calendar.ics
"""

import json
import hashlib
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ----------------------------------------------------------------------
# CONFIG -- edit this section to change countries / impact / timezone
# ----------------------------------------------------------------------

# Map the countries you asked about to Forex Factory's currency codes.
# (Euro Area, France, and Germany all collapse to EUR -- see limitation above.)
WANTED_CURRENCIES = {
    "AUD",  # Australia
    "CAD",  # Canada
    "EUR",  # Euro Area / France / Germany (FF does not split these out)
    "JPY",  # Japan
    "GBP",  # United Kingdom
    "USD",  # United States
}

# Impact levels to include. FF uses: "High", "Medium", "Low", "Holiday"
WANTED_IMPACT = {"High"}

# NOTE ON TIMEZONES: iCalendar events are written in UTC (the "Z" suffix
# below) because that is the one format every calendar client -- including
# Outlook -- parses unambiguously. A custom "UTC-4" TZID without a full
# VTIMEZONE block is technically invalid ICS and some clients will reject
# or misparse it. The simplest robust fix: write everything in UTC and set
# your Outlook calendar's default display timezone to UTC-4 once -- Outlook
# will then show every event (from every calendar) converted to UTC-4
# automatically. This also means your feed keeps working correctly even if
# Outlook's timezone setting changes later.
FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "economic_calendar.ics"

DEFAULT_EVENT_DURATION_MINUTES = 30

# ----------------------------------------------------------------------


def fetch_events(url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def parse_event_datetime(date_str: str) -> datetime:
    """FF's 'date' field is an ISO8601 string with an explicit UTC offset,
    e.g. '2026-07-01T08:30:00-04:00'. datetime.fromisoformat handles this
    natively in Python 3.11+; for 3.9/3.10 we do a small manual fallback."""
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        # Fallback for older Python: strip a trailing 'Z' if present
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        return datetime.fromisoformat(date_str)


def make_uid(event: dict) -> str:
    """Stable UID per event so that, when this file is regenerated, Outlook
    recognizes a changed-time event as an UPDATE to the same item rather
    than a duplicate. Based on country + title, NOT on the date/time
    (since the whole point is to let the date/time change between runs)."""
    key = f"{event.get('country','')}-{event.get('title','')}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return f"{digest}@econ-calendar"


def escape_ics_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def build_ics(events: list[dict]) -> str:
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//econ-calendar-script//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Economic Calendar (High Impact)",
    ]

    for ev in events:
        try:
            dt_raw = parse_event_datetime(ev["date"])
        except Exception:
            continue  # skip malformed entries (e.g. all-day holidays with odd dates)

        dt_utc = dt_raw.astimezone(timezone.utc)
        dt_end = dt_utc + timedelta(minutes=DEFAULT_EVENT_DURATION_MINUTES)

        dtstart = dt_utc.strftime("%Y%m%dT%H%M%SZ")
        dtend = dt_end.strftime("%Y%m%dT%H%M%SZ")

        title = ev.get("title", "Untitled event")
        country = ev.get("country", "")
        forecast = ev.get("forecast", "")
        previous = ev.get("previous", "")

        summary = escape_ics_text(f"{country} - {title}")
        description = escape_ics_text(
            f"Country/Currency: {country}\n"
            f"Impact: {ev.get('impact','')}\n"
            f"Forecast: {forecast}\n"
            f"Previous: {previous}\n"
            f"Source: Forex Factory (free feed)"
        )

        lines += [
            "BEGIN:VEVENT",
            f"UID:{make_uid(ev)}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main():
    events = fetch_events(FEED_URL)

    filtered = [
        ev
        for ev in events
        if ev.get("country") in WANTED_CURRENCIES
        and ev.get("impact") in WANTED_IMPACT
    ]

    ics_text = build_ics(filtered)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(ics_text, encoding="utf-8")

    print(f"Wrote {len(filtered)} events to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
