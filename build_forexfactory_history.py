#!/usr/bin/env python3
"""
build_forexfactory_history.py

Forex Factory's free feed only ever returns "the current week" -- there
is no historical/last-week export endpoint (confirmed: per long-running
community discussion around this exact feed, "history data are only
available at the website," and scraping the website itself is a
separate, higher-risk approach this project deliberately avoids -- see
MAINTENANCE.md / REBUILD_PROMPT.md).

This script works around that by ACCUMULATING what forexfactory_source.py
fetches each time it runs (every 4 hours) into a persistent history file,
pruning anything older than LOOKBACK_DAYS. Since the workflow already
legitimately fetches "this week" on a schedule, this builds a genuine
rolling lookback window purely from data already being fetched -- no
extra requests, no scraping of anything not already approved for use.

IMPORTANT LIMITATION: this can only accumulate GOING FORWARD from when it
starts running. It cannot retroactively backfill history from before its
first run, since that data was never captured and Forex Factory doesn't
expose it any other way. The lookback window starts at 0 days and grows
to the full LOOKBACK_DAYS over time.

Run:
    python3 build_forexfactory_history.py
Reads/writes:
    sources/forexfactory_history.json
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sources"))
from forexfactory_source import get_events  # noqa: E402

HISTORY_FILE = Path(__file__).parent / "sources" / "forexfactory_history.json"

# How many days in the past to retain. Matches the same constant name/
# convention used in build_central_bank_json.py and
# build_data_releases_json.py for consistency.
LOOKBACK_DAYS = 30


def event_key(ev: dict) -> str:
    """Dedup/merge key for an event. Day-level granularity (not full
    timestamp) since Forex Factory doesn't give a stable event ID and a
    genuine same-title-same-country event shouldn't repeat twice in one
    day. If a later fetch reports a slightly revised time for the same
    key, the newer fetch's version overwrites the older one (see merge
    logic in main())."""
    date_part = ev["date"][:10]  # YYYY-MM-DD
    return f"{ev.get('country','')}|{ev.get('title','')}|{date_part}"


def load_history() -> dict:
    if not HISTORY_FILE.exists():
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    return {event_key(ev): ev for ev in data.get("events", [])}


def main():
    try:
        live_events = get_events()
    except Exception as e:
        print(f"[!] Live fetch failed: {e} -- history file left untouched this run", file=sys.stderr)
        return

    print(f"Live fetch: {len(live_events)} current-week events")

    history_by_key = load_history()
    print(f"Existing history: {len(history_by_key)} events before merge")

    # merge: live fetch always overwrites any existing entry with the
    # same key (newest data wins), everything else in history is kept
    for ev in live_events:
        history_by_key[event_key(ev)] = ev

    # prune anything older than the lookback window
    cutoff = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).isoformat()
    pruned = {k: v for k, v in history_by_key.items() if v["date"] >= cutoff}
    removed = len(history_by_key) - len(pruned)

    all_events = sorted(pruned.values(), key=lambda e: e["date"])

    output = {
        "_readme": [
            "Accumulated Forex Factory history, since Forex Factory's feed only",
            "ever exposes 'this week' with no historical endpoint. Built up over",
            "time by build_forexfactory_history.py merging each live fetch into",
            "this file and pruning anything older than LOOKBACK_DAYS.",
            "",
            "DO NOT hand-edit -- overwritten on every run.",
            f"LOOKBACK_DAYS = {LOOKBACK_DAYS}",
        ],
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "lookback_days": LOOKBACK_DAYS,
        "events": all_events,
    }

    HISTORY_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Pruned {removed} events older than {LOOKBACK_DAYS} days")
    print(f"Wrote {len(all_events)} total events to {HISTORY_FILE}")


if __name__ == "__main__":
    main()
