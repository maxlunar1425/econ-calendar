#!/usr/bin/env python3
"""
snb_scraper.py

Fetches https://www.snb.ch/en/services-events/digital-services/event-schedule
directly and extracts SNB (Swiss National Bank) rate-decision dates by
parsing the page's own text -- no third-party sources, no manual
transcription.

PAGE STRUCTURE THIS RELIES ON (verified against the live page):
  A flat chronological list of ALL upcoming SNB events (data releases,
  speeches, reports, monetary policy events), each formatted as a single
  line:
    DD.MM.YYYY HH:MM <description>
  The unambiguous marker for an actual rate decision is a description
  containing both "Monetary policy assessment of" and "(press release)".
  This excludes the same-day "(introductory remarks, news conference)"
  entry (30 min later, not the decision itself) and the unrelated
  "Summary of monetary policy discussion" entries (published weeks later).

  Unlike the other five banks, this page already lists dates well into
  the following year (SNB publishes further ahead than most), so this
  scraper does not need month-range or day-2 logic -- the decision
  date+time is stated directly and completely on one line.

  This is the SNB's actual page structure as of the date this was written.
  If the SNB redesigns the page, this WILL break -- run it and check the
  output looks sane rather than trusting it blindly forever.

Announcement time is stated directly on the page (09:30 local Swiss time,
CET or CEST depending on the time of year). This script uses a fixed
CET (UTC+1) approximation -- see DST caveat in README, same issue as
every other bank's scraper; during CEST months the true UTC time is one
hour earlier than what's stored here.

Run standalone:
    python3 snb_scraper.py [year]
"""

import re
import sys
import urllib.request
from datetime import datetime, timedelta

URL = "https://www.snb.ch/en/services-events/digital-services/event-schedule"


def fetch_raw_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def html_to_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"&amp;", "&", text)
    return text


def parse_meetings(text: str, year: int) -> list[dict]:
    pattern = re.compile(
        r"(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})\s+"
        r"Monetary policy assessment of[^\n\]]*\(press release\)",
    )

    results = []
    for m in pattern.finditer(text):
        day, month, yr, hour, minute = m.groups()
        if int(yr) != year:
            continue

        try:
            local_dt = datetime(int(yr), int(month), int(day), int(hour), int(minute))
        except ValueError as e:
            print(f"  [!] Skipping unparseable date {day}.{month}.{yr}: {e}", file=sys.stderr)
            continue

        # Fixed CET (UTC+1) approximation -- see DST caveat in module docstring
        utc_dt = local_dt - timedelta(hours=1)

        results.append(
            {
                "bank": "SNB",
                "country": "CHF",
                "date": utc_dt.strftime("%Y-%m-%d"),
                "time_utc": utc_dt.strftime("%H:%M"),
                "note": f"Rate decision ({hour}:{minute} local Swiss time, "
                        f"CET/CEST approximation applied)",
            }
        )

    return results


def get_snb_dates(year: int) -> list[dict]:
    html = fetch_raw_html(URL)
    text = html_to_text(html)
    return parse_meetings(text, year)


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    for ev in get_snb_dates(year):
        print(ev)
