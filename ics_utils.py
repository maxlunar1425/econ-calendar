#!/usr/bin/env python3
"""
ics_utils.py

Shared iCalendar-building logic used by every calendar builder in this
project (build_calendar.py, build_data_releases_ics.py, and any future
ones). Extracted here so the UID scheme, escaping rules, and VEVENT
formatting stay identical and only need fixing in one place.

Each calendar builder is responsible for its own event-gathering; this
module only turns a list of normalized events into valid ICS text.
"""

import hashlib
from datetime import datetime, timedelta, timezone

DEFAULT_EVENT_DURATION_MINUTES = 30


def make_uid(event: dict, namespace: str) -> str:
    """Stable UID based on country + title + year-month of the event.

    The year-month component is essential: recurring events (central bank
    rate decisions, monthly CPI/PPI releases) share an identical title
    across every occurrence. Without a date component, every occurrence
    would collide into a single UID and all but the first would be
    silently dropped during de-duplication.

    'namespace' scopes the UID to a specific calendar file (e.g.
    "econ-calendar" vs "data-releases-calendar") -- this isn't strictly
    required since separate .ics files don't share UID space in Outlook,
    but keeps things unambiguous if events are ever inspected together."""
    dt = datetime.fromisoformat(event["date"])
    year_month = dt.strftime("%Y-%m")
    key = f"{event.get('country','')}-{event.get('title','')}-{year_month}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return f"{digest}@{namespace}"


def escape_ics_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def dedupe(events: list[dict], namespace: str) -> list[dict]:
    """If the same event somehow appears twice within one source list,
    keep only the first occurrence."""
    seen = {}
    for ev in events:
        uid = make_uid(ev, namespace)
        if uid not in seen:
            seen[uid] = ev
    return list(seen.values())


def build_ics(events: list[dict], calendar_name: str, namespace: str) -> str:
    """Builds a complete VCALENDAR document from a list of normalized
    events. 'calendar_name' sets X-WR-CALNAME (what Outlook shows as the
    calendar's display name). 'namespace' scopes UIDs -- see make_uid()."""
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//econ-calendar-script//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{calendar_name}",
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
            f"UID:{make_uid(ev, namespace)}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
