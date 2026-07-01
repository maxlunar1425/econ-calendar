#!/usr/bin/env python3
"""
dol_scraper.py

Generates dates for the Department of Labor's (Employment and Training
Administration) weekly "Unemployment Insurance Weekly Claims Report" --
commonly called "Jobless Claims."

UNLIKE every other scraper in this project, this release doesn't have a
published list of specific dates. It's a RECURRING RULE instead: every
Thursday, 8:30am Eastern time, with exceptions when a Thursday falls on
a Federal Holiday. This script fetches the OFFICIAL exceptions list from
DOL's own page and applies it to an otherwise-generated "every Thursday"
calendar -- no third-party sources, no manual transcription of the
exception dates.

PAGE STRUCTURE THIS RELIES ON (verified against the live page):
    https://oui.doleta.gov/unemploy/claims_arch.asp
  A small table titled "the following is a list of dates when the weekly
  news release will be published on a day other than Thursday":
    | Release Date                 | Release Time |
    | Wednesday, November 25, 2026 | 8:30 AM EST  |
  Each override REPLACES that calendar week's default Thursday (it does
  not add an extra release) -- e.g. Thanksgiving week 2026: the default
  Thursday (Nov 26) is removed and replaced with the override (Nov 25).

  This exceptions list is normally sparse (often just 1-2 entries per
  year, for Thanksgiving specifically, since that's the one federal
  holiday guaranteed to always fall on a Thursday). Other federal
  holidays only occasionally land on a Thursday depending on the year --
  if DOL hasn't published an exception for one, this script has no way
  to know it should adjust, and will show a plain Thursday that might
  turn out to be wrong. Re-run periodically; DOL updates this table as
  it goes, not necessarily a full year ahead.

  This is DOL's actual page structure as of the date this was written.
  If DOL redesigns the page, the OVERRIDE-fetching will break (falls
  back to "no known exceptions" rather than crashing) -- run it and
  check the output looks sane rather than trusting it blindly forever.

Announcement time: 8:30am Eastern local time, using zoneinfo for exact
EST/EDT conversion (like bls_scraper.py) rather than a fixed offset.

NOTE: there is no watched_releases.json entry for DOL -- unlike BLS/BEA,
there's only one release type here, so there's nothing to select among.

Run standalone:
    python3 dol_scraper.py [year]
"""

import re
import sys
import urllib.request
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

URL = "https://oui.doleta.gov/unemploy/claims_arch.asp"
EASTERN = ZoneInfo("America/New_York")

MONTH_NUM = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}


def fetch_page_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")
    text = re.sub(r"<[^>]+>", "\n", raw)
    return text


def fetch_exceptions(url: str) -> list[date]:
    """Returns a list of override release dates, parsed from DOL's own
    exceptions table. Returns an empty list (not an error) if the table
    can't be found/parsed -- a missing exceptions list just means "fall
    back to every Thursday," which is still a reasonable default."""
    try:
        text = fetch_page_text(url)
    except Exception as e:
        print(f"  [!] Could not fetch DOL exceptions page: {e}", file=sys.stderr)
        return []

    month_names = "|".join(MONTH_NUM.keys())
    pattern = re.compile(
        rf"(?:Monday|Tuesday|Wednesday|Thursday|Friday),?\s+({month_names})\s+(\d{{1,2}}),\s+(\d{{4}})"
    )

    overrides = []
    for m in pattern.finditer(text):
        month_name, day, year = m.groups()
        try:
            overrides.append(date(int(year), MONTH_NUM[month_name], int(day)))
        except ValueError:
            continue

    return overrides


def generate_thursdays(year: int) -> list[date]:
    d = date(year, 1, 1)
    # advance to the first Thursday (weekday() == 3)
    d += timedelta(days=(3 - d.weekday()) % 7)
    thursdays = []
    while d.year == year:
        thursdays.append(d)
        d += timedelta(days=7)
    return thursdays


def apply_overrides(thursdays: list[date], overrides: list[date]) -> list[date]:
    """Each override replaces whichever default Thursday falls in the
    same ISO calendar week (year, week number) -- not just adds a new
    date -- so a holiday week doesn't end up with two releases."""
    override_weeks = {o.isocalendar()[:2] for o in overrides}
    kept = [t for t in thursdays if t.isocalendar()[:2] not in override_weeks]
    return sorted(kept + overrides)


def get_dol_dates(year: int) -> list[dict]:
    thursdays = generate_thursdays(year)
    overrides = [o for o in fetch_exceptions(URL) if o.year == year]
    release_dates = apply_overrides(thursdays, overrides)

    results = []
    for d in release_dates:
        local_dt = datetime(d.year, d.month, d.day, 8, 30, tzinfo=EASTERN)
        utc_dt = local_dt.astimezone(ZoneInfo("UTC"))

        is_override = d in overrides
        results.append(
            {
                "bank": "DOL",
                "country": "USD",
                "release": "Unemployment Insurance Weekly Claims Report",
                "date": utc_dt.strftime("%Y-%m-%d"),
                "time_utc": utc_dt.strftime("%H:%M"),
                "note": (
                    "Jobless Claims (weekly); exact EST/EDT conversion via IANA tz data"
                    + (" -- OFFICIAL HOLIDAY EXCEPTION DATE (moved off Thursday)" if is_override else "")
                ),
            }
        )

    return results


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    for ev in get_dol_dates(year):
        print(ev)
