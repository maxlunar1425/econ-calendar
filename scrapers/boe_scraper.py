#!/usr/bin/env python3
"""
boe_scraper.py

Fetches https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates
directly and extracts Bank Rate decision dates by parsing the page's own
text -- no third-party sources, no manual transcription.

PAGE STRUCTURE THIS RELIES ON (verified against the live page):
  A table under a "## {YEAR} confirmed dates" (or "provisional dates")
  heading, with rows starting "Thursday {day} {Month}". No year appears in
  each row -- it's inherited from the section heading. The section ends at
  the next "##" heading.

  This is the BoE's actual page structure as of the date this was written.
  If the BoE redesigns the page, this WILL break -- run it and check the
  output looks sane rather than trusting it blindly forever.

Decision announcement time: 12:00 noon UK time (GMT or BST depending on
time of year). This script uses a fixed 12:00 UTC approximation -- see
DST caveat in README, same issue as the other banks' scrapers.

Run standalone:
    python3 boe_scraper.py [year]
"""

import re
import sys
import urllib.request
from datetime import datetime

URL = "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates"

MONTH_NUM = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}


def fetch_raw_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def html_to_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"&amp;", "&", text)
    return text


def extract_year_section(text: str, year: int) -> str:
    pattern = rf"##\s*{year}\s+(?:confirmed|provisional)\s+dates"
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f"Could not find '{year} confirmed/provisional dates' heading")
    start = m.end()
    next_heading = re.search(r"##\s", text[start:])
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def parse_meetings(section_text: str, year: int) -> list[dict]:
    month_names = "|".join(MONTH_NUM.keys())
    pattern = re.compile(rf"Thursday\s+(\d{{1,2}})\s+({month_names})")

    results = []
    for m in pattern.finditer(section_text):
        day, month_name = m.groups()
        month = MONTH_NUM[month_name]
        try:
            decision_date = datetime(year, month, int(day))
        except ValueError as e:
            print(f"  [!] Skipping unparseable date {day} {month_name} {year}: {e}", file=sys.stderr)
            continue

        results.append(
            {
                "bank": "BOE",
                "country": "GBP",
                "date": decision_date.strftime("%Y-%m-%d"),
                "time_utc": "12:00",  # approximation -- see DST caveat above
                "note": "Rate decision",
            }
        )

    return results


def get_boe_dates(year: int) -> list[dict]:
    html = fetch_raw_html(URL)
    text = html_to_text(html)
    section = extract_year_section(text, year)
    return parse_meetings(section, year)


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    for ev in get_boe_dates(year):
        print(ev)
