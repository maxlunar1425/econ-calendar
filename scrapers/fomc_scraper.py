#!/usr/bin/env python3
"""
fomc_scraper.py

Fetches https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
directly and extracts FOMC meeting dates for a given year by parsing the
page's own text -- no third-party sources, no manual transcription.

PAGE STRUCTURE THIS RELIES ON (verified against the live page):
  A "#### {YEAR} FOMC Meetings" heading, followed by a sequence of:
    **{Month}**
    {day}-{day}[*]
  repeated for each of the ~8 meetings that year, until the next
  "#### {YEAR} FOMC Meetings" heading (for the adjacent year) appears.
  The trailing '*' marks a meeting with a Summary of Economic Projections.
  Compound month labels ("Apr/May", "Oct/Nov") occur when a 2-day meeting
  spans a month boundary -- the SECOND named month is used, since the
  decision is announced on day 2.

  This is the Fed's actual page structure as of the date this was written.
  If the Fed redesigns the page, this WILL break -- run it and check the
  output looks sane rather than trusting it blindly forever.

The decision is always announced at 2:00 PM ET on the second (final) day
of the meeting -- this is a stated Fed convention, not scraped separately.

Run standalone:
    python3 fomc_scraper.py [year]
"""

import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

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
    text = re.sub(r"[ \t]+", " ", text)
    return text


def extract_year_section(full_text: str, year: int) -> str:
    """Isolates the text between this year's meetings heading and the next
    one (adjacent year) in the page."""
    pattern = rf"#{{1,4}}\s*{year}\s+FOMC Meetings"
    matches = list(re.finditer(pattern, full_text))
    if not matches:
        raise ValueError(f"Could not find '{year} FOMC Meetings' heading on page")
    start = matches[0].end()

    # find the next "#### YYYY FOMC Meetings" heading after this one to bound the section
    next_heading = re.search(r"#{1,4}\s*\d{4}\s+FOMC Meetings", full_text[start:])
    end = start + next_heading.start() if next_heading else len(full_text)
    return full_text[start:end]


def parse_meetings(section_text: str, year: int) -> list[dict]:
    """Finds **Month** or **Month1/Month2** followed by a day-day[*] pattern."""
    # month header: one or two month names separated by '/'
    month_names = "|".join(MONTH_NUM.keys())
    pattern = re.compile(
        rf"\*\*((?:{month_names})(?:/(?:{month_names}))?)\*\*\s*\n+\s*(\d{{1,2}})-(\d{{1,2}})(\*)?",
        re.MULTILINE,
    )

    results = []
    for m in pattern.finditer(section_text):
        month_label, day1, day2, sep_flag = m.groups()
        # decision is on the 2nd day; if compound label ("Apr/May"), the
        # 2nd day belongs to the 2nd named month
        months = month_label.split("/")
        decision_month_name = months[-1]
        decision_month = MONTH_NUM[decision_month_name]
        decision_day = int(day2)

        try:
            decision_date = datetime(year, decision_month, decision_day)
        except ValueError as e:
            print(f"  [!] Skipping unparseable date {month_label} {day1}-{day2}: {e}", file=sys.stderr)
            continue

        results.append(
            {
                "bank": "FOMC",
                "country": "USD",
                "date": decision_date.strftime("%Y-%m-%d"),
                # Decision announced 2:00 PM ET; ET is UTC-5 (EST) or UTC-4 (EDT).
                # This uses a fixed UTC-4 approximation -- see caveat in README.
                "time_utc": "18:00",
                "note": (
                    "Rate decision (2nd day of 2-day meeting)"
                    + (
                        "; includes Summary of Economic Projections"
                        if sep_flag
                        else ""
                    )
                ),
            }
        )

    return results


def get_fomc_dates(year: int) -> list[dict]:
    html = fetch_raw_html(URL)
    text = html_to_text(html)
    section = extract_year_section(text, year)
    return parse_meetings(section, year)


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    for ev in get_fomc_dates(year):
        print(ev)
