#!/usr/bin/env python3
"""
boj_scraper.py

Fetches https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm directly and
extracts BOJ Monetary Policy Meeting decision dates by parsing the page's
own text -- no third-party sources, no manual transcription.

PAGE STRUCTURE THIS RELIES ON (verified against the live page):
  A table under a "## {YEAR}" heading with a "Date of MPM" column, one row
  per meeting, formatted like:
    Jan. 22 (Thurs.), 23 (Fri.)
  i.e. Month, day1 (weekday), day2 (weekday) -- a 2-day meeting. The
  decision is announced on the SECOND day. Month abbreviations are
  inconsistent on this page (some months use a period, "June"/"July" do
  not) -- the parser accounts for both forms.

  CAVEAT: all 2026 meetings fall within a single calendar month (no
  Dec/Jan-style rollover this year). A meeting spanning a month boundary
  is NOT handled by this parser and would need special-casing if it occurs
  in a future year -- check output manually if a meeting's days look like
  they don't belong to the same month.

  This is the BoJ's actual page structure as of the date this was written.
  If the BoJ redesigns the page, this WILL break -- run it and check the
  output looks sane rather than trusting it blindly forever.

ANNOUNCEMENT TIME: the BoJ does NOT publish a fixed release time for its
policy statement -- its own schedule literally lists it as "undecided" on
the day, stating only that it lands sometime after the second day's
session begins (typically late morning to early afternoon JST in
practice, but officially unfixed). This script uses a rough 03:00 UTC
(~noon JST) placeholder and flags every entry as approximate in the note
-- treat the DATE as reliable and the TIME as a rough guess only.

Run standalone:
    python3 boj_scraper.py [year]
"""

import re
import sys
import urllib.request
from datetime import datetime

URL = "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm"

MONTH_NUM = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "June": 6,
    "July": 7, "Aug": 8, "Sept": 9, "Oct": 10, "Nov": 11, "Dec": 12,
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
    pattern = rf"##\s*{year}\b"
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f"Could not find '## {year}' heading on page")
    start = m.end()
    next_heading = re.search(r"##\s*\d{4}\b", text[start:])
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def parse_meetings(section_text: str, year: int) -> list[dict]:
    month_names = "|".join(MONTH_NUM.keys())
    # e.g. "Jan. 22 (Thurs.), 23 (Fri.)" or "June 15 (Mon.), 16 (Tues.)"
    pattern = re.compile(
        rf"({month_names})\.?\s*(\d{{1,2}})\s*\([^)]*\),\s*(\d{{1,2}})\s*\([^)]*\)",
    )

    results = []
    for m in pattern.finditer(section_text):
        month_name, day1, day2, = m.groups()
        month = MONTH_NUM[month_name]
        try:
            decision_date = datetime(year, month, int(day2))
        except ValueError as e:
            print(f"  [!] Skipping unparseable date {month_name} {day1}-{day2}, {year}: {e}", file=sys.stderr)
            continue

        results.append(
            {
                "bank": "BOJ",
                "country": "JPY",
                "date": decision_date.strftime("%Y-%m-%d"),
                "time_utc": "03:00",  # rough placeholder -- BoJ does not fix a release time
                "note": "Rate decision (2nd day of 2-day meeting); "
                        "TIME IS APPROXIMATE -- BoJ does not officially fix a release time",
            }
        )

    return results


def get_boj_dates(year: int) -> list[dict]:
    html = fetch_raw_html(URL)
    text = html_to_text(html)
    section = extract_year_section(text, year)
    return parse_meetings(section, year)


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    for ev in get_boj_dates(year):
        print(ev)
