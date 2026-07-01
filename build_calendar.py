#!/usr/bin/env python3
"""
build_calendar.py

Orchestrator: pulls events from both sources (Forex Factory + static
central bank dates), merges and de-duplicates them, and writes the final
Outlook-subscribable .ics file.

This is the file the GitHub Actions workflow runs. It deliberately
contains NO fetching or filtering logic of its own -- that all lives in
sources/forexfactory_source.py and sources/central_bank_source.py. This
file only merges and writes output.

Usage:
    python3 build_calendar.py
Produces:
    ./output/economic_calendar.ics
"""

import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sources"))
from forexfactory_source import get_events as get_ff_events          # noqa: E402
from central_bank_source import load_central_bank_events as get_cb_events  # noqa: E402

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "economic_calendar.ics"

DEFAULT_EVENT_DURATION_MINUTES = 30


def make_uid(event: dict) -> str:
    """Stable UID based on country + title + year-month of the event.

    The year-month component is essential: recurring events like central
    bank rate decisions share an identical title across every occurrence
    ("USD - FOMC Interest Rate Decision" appears ~8 times a year). Without
    a date component, every occurrence would collide into a single UID and
    all but the first would be silently dropped during de-duplication.

    Including only year-month (not the full date) still lets a same-month
    time/date correction (e.g. Forex Factory revising a release time by a
    day) be treated as an UPDATE to the same event rather than a new one,
    which was the original point of keeping date granularity coarse."""
    dt = datetime.fromisoformat(event["date"])
    year_month = dt.strftime("%Y-%m")
    key = f"{event.get('country','')}-{event.get('title','')}-{year_month}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return f"{digest}@econ-calendar"


def escape_ics_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def dedupe(events: list[dict]) -> list[dict]:
    """If the same event (by UID) somehow appears in both sources, keep
    only one copy -- prefer whichever appears first (Forex Factory is
    passed in first in build_calendar's merge order below)."""
    seen = {}
    for ev in events:
        uid = make_uid(ev)
        if uid not in seen:
            seen[uid] = ev
    return list(seen.values())


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
        dt_utc = datetime.fromisoformat(ev["date"]).astimezone(timezone.utc)
        dt_end = dt_utc + timedelta(minutes=DEFAULT_EVENT_DURATION_MINUTES)

        dtstart = dt_utc.strftime("%Y%m%dT%H%M%SZ")
        dtend = dt_end.strftime("%Y%m%dT%H%M%SZ")

        summary = escape_ics_text(f"{ev['country']} - {ev['title']}")
        description = escape_ics_text(
            f"Country/Currency: {ev['country']}\n"
            f"Impact: {ev.get('impact','')}\n"
            f"Forecast: {ev.get('forecast','')}\n"
            f"Previous: {ev.get('previous','')}\n"
            f"Source: {ev.get('source','')}\n"
            + (f"Note: {ev['note']}\n" if ev.get("note") else "")
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
    ff_events = get_ff_events()
    print(f"Forex Factory: {len(ff_events)} events")

    cb_events = get_cb_events()
    print(f"Central banks: {len(cb_events)} events")

    all_events = dedupe(ff_events + cb_events)
    all_events.sort(key=lambda e: e["date"])

    ics_text = build_ics(all_events)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(ics_text, encoding="utf-8")

    print(f"Wrote {len(all_events)} total events to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
