#!/usr/bin/env python3
"""
bls_scraper.py

Fetches the Bureau of Labor Statistics' OFFICIAL iCalendar feed directly
(https://www.bls.gov/schedule/news_release/bls.ics) and filters it down
to the releases listed in watched_releases.json under "BLS" -- e.g.
Consumer Price Index, Producer Price Index.

Unlike every other scraper in this project, no HTML parsing is involved
at all: BLS publishes a genuine, well-formed ICS file, so this just
parses real iCalendar VEVENT blocks directly. This also means we can do
EXACT EST/EDT conversion using Python's zoneinfo (real IANA timezone
data) instead of the fixed-offset approximation used elsewhere in this
project -- the BLS feed's own VTIMEZONE block encodes the same US
Eastern DST rules, so this is provably correct rather than approximate.

TO ADD OR REMOVE RELEASES: edit watched_releases.json ("BLS" list) --
titles must match BLS's own SUMMARY field exactly (case-sensitive).

Run standalone:
    python3 bls_scraper.py [year]
"""

import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

URL = "https://www.bls.gov/schedule/news_release/bls.ics"
WATCHLIST_FILE = Path(__file__).parent / "watched_releases.json"

EASTERN = ZoneInfo("America/New_York")


def fetch_ics(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/calendar,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def load_watchlist() -> set[str]:
    with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("BLS", []))


def unfold_ics(text: str) -> str:
    """RFC 5545 line unfolding: a line break followed by a single space or
    tab is a continuation of the previous line, not a real line break.
    Titles can wrap across lines in these feeds, so this must run before
    any regex matching on SUMMARY or DTSTART."""
    return re.sub(r"\r?\n[ \t]", "", text)


def matches_watchlist(summary: str, watchlist: set[str]) -> bool:
    """Prefix match: BEA titles include a variable month/year suffix
    (e.g. 'Personal Income and Outlays, June 2026'), so exact equality
    would never match. BLS titles happen to have no suffix, so prefix
    matching works identically to exact matching for them -- using the
    same matching function for both keeps the two scrapers consistent."""
    return any(summary.startswith(w) for w in watchlist)


def parse_events(ics_text: str, watchlist: set[str], year: int) -> list[dict]:
    ics_text = unfold_ics(ics_text)
    # Split into individual VEVENT blocks
    blocks = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics_text, re.DOTALL)

    results = []
    for block in blocks:
        summary_m = re.search(r"SUMMARY:(.+)", block)
        dtstart_m = re.search(r"DTSTART;TZID=US-Eastern:(\d{8})T(\d{6})", block)
        if not summary_m or not dtstart_m:
            continue

        summary = summary_m.group(1).strip()
        if not matches_watchlist(summary, watchlist):
            continue

        date_str, time_str = dtstart_m.groups()
        try:
            naive_local = datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S")
        except ValueError as e:
            print(f"  [!] Skipping unparseable DTSTART in block for '{summary}': {e}", file=sys.stderr)
            continue

        if naive_local.year != year:
            continue

        local_dt = naive_local.replace(tzinfo=EASTERN)
        utc_dt = local_dt.astimezone(ZoneInfo("UTC"))

        results.append(
            {
                "bank": "BLS",
                "country": "USD",
                "release": summary,
                "date": utc_dt.strftime("%Y-%m-%d"),
                "time_utc": utc_dt.strftime("%H:%M"),
                "note": f"{summary} release (exact EST/EDT conversion via IANA tz data)",
            }
        )

    return results


def get_bls_dates(year: int) -> list[dict]:
    ics_text = fetch_ics(URL)
    watchlist = load_watchlist()
    return parse_events(ics_text, watchlist, year)


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    for ev in get_bls_dates(year):
        print(ev)
