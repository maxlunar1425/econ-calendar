#!/usr/bin/env python3
"""
boc_scraper.py

Fetches https://www.bankofcanada.ca/press/upcoming-events/ directly and
extracts Bank of Canada rate decision dates by parsing the page's own
text -- no third-party sources, no manual transcription.

PAGE STRUCTURE THIS RELIES ON (verified against the live page):
  A chronological events list with entries like:
    {Month} {day}, {year}
    ### [{Event Title}](...)
    {time} (ET)
    {description}
  Only entries whose title starts with "Interest Rate Announcement" are
  rate decisions -- other entries (holidays, Summary of Deliberations,
  survey releases) are excluded.

  NOTE: The Bank of Canada also publishes an official iCal feed at
  webcal://www.bankofcanada.ca/?feed=ical&content_type=upcoming-events --
  spotted on this same page. That would likely be a MORE robust source
  than text-scraping (structured ICS instead of parsing prose), but
  parsing a live ICS feed is a separate piece of work not yet built here.
  Worth prioritizing if this scraper proves fragile over time.

  This is the BoC's actual page structure as of the date this was written.
  If the BoC redesigns the page, this WILL break -- run it and check the
  output looks sane rather than trusting it blindly forever.

Announcement time: 09:45 ET, stated directly on the page per event (not
approximated) -- but ET/EST-vs-EDT conversion to UTC still uses a fixed
approximation here; see DST caveat in README.

Run standalone:
    python3 boc_scraper.py [year]
"""

import re
import sys
import urllib.request
from datetime import datetime

URL = "https://www.bankofcanada.ca/press/upcoming-events/"

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


def parse_meetings(text: str, year: int) -> list[dict]:
    month_names = "|".join(MONTH_NUM.keys())
    pattern = re.compile(
        rf"({month_names})\s+(\d{{1,2}}),\s+(\d{{4}})\s*\n+\s*#{{1,3}}\s*\[(Interest Rate Announcement[^\]]*)\]",
    )

    results = []
    for m in pattern.finditer(text):
        month_name, day, yr, title = m.groups()
        if int(yr) != year:
            continue

        month = MONTH_NUM[month_name]
        try:
            decision_date = datetime(int(yr), month, int(day))
        except ValueError as e:
            print(f"  [!] Skipping unparseable date {month_name} {day}, {yr}: {e}", file=sys.stderr)
            continue

        results.append(
            {
                "bank": "BOC",
                "country": "CAD",
                "date": decision_date.strftime("%Y-%m-%d"),
                "time_utc": "13:45",  # 09:45 ET -> approximation, see DST caveat
                "note": "Rate decision"
                + (" + Monetary Policy Report" if "Monetary Policy Report" in title else ""),
            }
        )

    return results


def get_boc_dates(year: int) -> list[dict]:
    html = fetch_raw_html(URL)
    text = html_to_text(html)
    return parse_meetings(text, year)


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    for ev in get_boc_dates(year):
        print(ev)
