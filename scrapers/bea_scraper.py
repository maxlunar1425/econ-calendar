#!/usr/bin/env python3
"""
bea_scraper.py

Fetches the Bureau of Economic Analysis' OFFICIAL iCalendar feed directly
(https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics)
and filters it down to the releases listed in watched_releases.json under
"BEA" -- currently "Personal Income and Outlays", which is the release
containing the PCE price index (the Fed's preferred inflation gauge).

Like bls_scraper.py, this parses a genuine official ICS feed directly --
no HTML scraping. BEA's feed is even simpler than BLS's: timestamps are
already in UTC (a trailing "Z"), so no timezone conversion is needed at
all -- just parse and use directly.

IMPORTANT: BEA titles include a variable month/year suffix (e.g.
"Personal Income and Outlays, June 2026"), unlike BLS's static titles.
Matching against watched_releases.json is therefore PREFIX-based
(startswith), not exact -- see matches_watchlist() in bls_scraper.py
(reused here) for the shared logic.

TO ADD OR REMOVE RELEASES: edit watched_releases.json ("BEA" list).

Run standalone:
    python3 bea_scraper.py [year]
"""

import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bls_scraper import unfold_ics, matches_watchlist  # shared helpers

URL = "https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics"
WATCHLIST_FILE = Path(__file__).parent / "watched_releases.json"


def fetch_ics(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def load_watchlist() -> set[str]:
    with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("BEA", []))


def parse_events(ics_text: str, watchlist: set[str], year: int) -> list[dict]:
    ics_text = unfold_ics(ics_text)
    blocks = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics_text, re.DOTALL)

    results = []
    for block in blocks:
        summary_m = re.search(r"SUMMARY:(.+)", block)
        # BEA format is a plain UTC timestamp, optionally with a
        # VALUE=DATE-TIME parameter depending on when the entry was added:
        #   DTSTART:20260730T123000Z
        #   DTSTART;VALUE=DATE-TIME:20250107T133000Z
        dtstart_m = re.search(r"DTSTART(?:;VALUE=DATE-TIME)?:(\d{8})T(\d{6})Z", block)
        if not summary_m or not dtstart_m:
            continue

        summary = summary_m.group(1).strip().rstrip("\\").strip()
        # unescape ICS comma/semicolon escaping for a clean display title
        summary = summary.replace("\\,", ",").replace("\\;", ";")

        if not matches_watchlist(summary, watchlist):
            continue

        date_str, time_str = dtstart_m.groups()
        try:
            utc_dt = datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S")
        except ValueError as e:
            print(f"  [!] Skipping unparseable DTSTART in block for '{summary}': {e}", file=sys.stderr)
            continue

        if utc_dt.year != year:
            continue

        results.append(
            {
                "bank": "BEA",
                "country": "USD",
                "release": summary,
                "date": utc_dt.strftime("%Y-%m-%d"),
                "time_utc": utc_dt.strftime("%H:%M"),
                "note": f"{summary} release (BEA feed is already in UTC, no conversion needed)",
            }
        )

    return results


def get_bea_dates(year: int) -> list[dict]:
    ics_text = fetch_ics(URL)
    watchlist = load_watchlist()
    return parse_events(ics_text, watchlist, year)


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    for ev in get_bea_dates(year):
        print(ev)
