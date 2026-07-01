#!/usr/bin/env python3
"""
rba_scraper.py

Fetches https://www.rba.gov.au/schedules-events/calendar/ directly and
extracts RBA Monetary Policy Board rate-decision dates by parsing the
page's own text -- no third-party sources, no manual transcription.

PAGE STRUCTURE THIS RELIES ON (verified against the live page):
  This page lists EVERY RBA event (speeches, publications, holidays,
  meetings). The reliable, unambiguous marker for a rate decision is the
  "Monetary Policy Decision Statement" / "Media Release" entry, which is
  followed by the actual decision date and time, e.g.:
    #### Monetary Policy Decision Statement
    Media Release
    3 February 2026 2.30 pm AEDT
  This is distinct from the "Monetary Policy Board Meeting" entry (which
  gives a 2-day RANGE, not the decision date) -- we deliberately use the
  Decision Statement entry instead since it's an exact date+time.

  This is the RBA's actual page structure as of the date this was written.
  If the RBA redesigns the page, this WILL break -- run it and check the
  output looks sane rather than trusting it blindly forever.

Announcement time is stated directly on the page (2.30 pm AEDT or AEST,
Australian Eastern time with its own DST). This script converts using a
fixed approximation -- see DST caveat in README, same issue as other
banks' scrapers, arguably more pronounced here since AEDT/AEST is a
10-11 hour swing from UTC depending on time of year.

Run standalone:
    python3 rba_scraper.py [year]
"""

import re
import sys
import urllib.request
from datetime import datetime

URL = "https://www.rba.gov.au/schedules-events/calendar/"

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
        rf"Monetary Policy Decision Statement\s*\n+\s*Media Release\s*\n+\s*"
        rf"(\d{{1,2}})\s+({month_names})\s+(\d{{4}})\s+(\d{{1,2}})\.(\d{{2}})\s*(am|pm)\s*(AEDT|AEST)",
    )

    results = []
    for m in pattern.finditer(text):
        day, month_name, yr, hour, minute, ampm, tz_label = m.groups()
        if int(yr) != year:
            continue

        month = MONTH_NUM[month_name]
        try:
            decision_date = datetime(int(yr), month, int(day))
        except ValueError as e:
            print(f"  [!] Skipping unparseable date {day} {month_name} {yr}: {e}", file=sys.stderr)
            continue

        # Convert local AEDT(UTC+11)/AEST(UTC+10) time to UTC
        hour_24 = int(hour) % 12 + (12 if ampm == "pm" else 0)
        utc_offset_hours = 11 if tz_label == "AEDT" else 10
        raw_utc_hour = hour_24 - utc_offset_hours
        utc_hour = raw_utc_hour % 24

        utc_date = decision_date
        if raw_utc_hour < 0:
            from datetime import timedelta
            utc_date = decision_date - timedelta(days=1)

        results.append(
            {
                "bank": "RBA",
                "country": "AUD",
                "date": utc_date.strftime("%Y-%m-%d"),
                "time_utc": f"{utc_hour:02d}:{minute}",
                "note": f"Rate decision ({tz_label} {hour}:{minute}{ampm} local, "
                        f"{decision_date.strftime('%Y-%m-%d')} local date)",
            }
        )

    return results


def get_rba_dates(year: int) -> list[dict]:
    html = fetch_raw_html(URL)
    text = html_to_text(html)
    return parse_meetings(text, year)


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    for ev in get_rba_dates(year):
        print(ev)
