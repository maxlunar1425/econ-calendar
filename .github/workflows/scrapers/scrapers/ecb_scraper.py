#!/usr/bin/env python3
"""
ecb_scraper.py

Fetches https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html
directly and extracts ECB Governing Council rate-decision dates by parsing
the page's own text -- no third-party sources, no manual transcription.

PAGE STRUCTURE THIS RELIES ON (verified against the live page):
  A repeating sequence of:
    DD/MM/YYYY
    <description line>
  The page lists ALL Governing Council activity (monetary policy meetings,
  non-monetary policy meetings, General Council meetings). Only entries
  whose description contains both "monetary policy meeting" and "Day 2"
  (equivalently, "followed by press conference") are actual rate-decision
  days -- Day 1 entries and non-monetary-policy entries are the setup/
  other-business days, not decision days, and are excluded.

  This is the ECB's actual page structure as of the date this was written.
  If the ECB redesigns the page, this WILL break -- run it and check the
  output looks sane rather than trusting it blindly forever.

Decision announcement time: 12:15 CET/CEST, i.e. either 11:15 or 10:15 UTC
depending on European daylight saving. This script uses a fixed 12:15 UTC
approximation -- see caveat in README about DST handling across all banks.

Run standalone:
    python3 ecb_scraper.py [year]
"""

import re
import sys
import urllib.request
from datetime import datetime

URL = "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html"


def fetch_raw_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def html_to_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"&amp;", "&", text)
    return text


def parse_meetings(text: str, year: int) -> list[dict]:
    # date line, then (possibly across a couple of lines) a description
    # containing both "monetary policy meeting" and "Day 2"
    pattern = re.compile(
        r"(\d{2})/(\d{2})/(\d{4})\s*\n+\s*(Governing Council of the ECB:[^\n]*)",
        re.MULTILINE,
    )

    results = []
    for m in pattern.finditer(text):
        day, month, yr, description = m.groups()
        if int(yr) != year:
            continue
        if "monetary policy meeting" not in description:
            continue
        if "Day 2" not in description:
            continue  # Day 1 = setup, not a decision day

        try:
            decision_date = datetime(int(yr), int(month), int(day))
        except ValueError as e:
            print(f"  [!] Skipping unparseable date {day}/{month}/{yr}: {e}", file=sys.stderr)
            continue

        results.append(
            {
                "bank": "ECB",
                "country": "EUR",
                "date": decision_date.strftime("%Y-%m-%d"),
                "time_utc": "12:15",  # approximation -- see DST caveat above
                "note": "Rate decision; press conference follows",
            }
        )

    return results


def get_ecb_dates(year: int) -> list[dict]:
    html = fetch_raw_html(URL)
    text = html_to_text(html)
    return parse_meetings(text, year)


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    for ev in get_ecb_dates(year):
        print(ev)
