#!/usr/bin/env python3
"""
forexfactory_history_source.py

Reads the accumulated forexfactory_history.json (built by
build_forexfactory_history.py) and returns it in the same normalized
event shape used everywhere else in this project, so
build_forexfactory_ics.py can consume it the same way
central_bank_source.py / data_release_source.py are consumed by their
respective builders.

This is separate from forexfactory_source.py (which does the live fetch)
for the same reason the central-bank/data-release pipelines separate
scraping from reading: build_forexfactory_ics.py shouldn't need to know
or care whether the data came from a fresh fetch or accumulated history.

Can be run standalone for testing:
    python3 forexfactory_history_source.py
"""

import json
import sys
from pathlib import Path

HISTORY_FILE = Path(__file__).parent / "forexfactory_history.json"


def load_forexfactory_events() -> list[dict]:
    if not HISTORY_FILE.exists():
        print(
            f"[forexfactory_history_source] No {HISTORY_FILE.name} found yet -- "
            f"run build_forexfactory_history.py first. Returning no events.",
            file=sys.stderr,
        )
        return []

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("events", [])


if __name__ == "__main__":
    evs = load_forexfactory_events()
    print(f"Loaded {len(evs)} accumulated Forex Factory events:")
    for e in evs:
        print(f"  {e['date']}  {e['country']}  {e['title']}")
