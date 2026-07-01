# Economic Calendar Project — Maintenance Reference

Repo: `maxlunar1425/econ-calendar`

Three independent, self-updating Outlook calendars, built entirely from
official/primary sources (no third-party aggregators except Forex Factory's
free export feed). Everything runs on GitHub Actions — no local machine
required for normal operation.

## Your 3 Outlook calendar subscriptions

```
https://maxlunar1425.github.io/econ-calendar/forexfactory_calendar.ics
https://maxlunar1425.github.io/econ-calendar/central_banks_calendar.ics
https://maxlunar1425.github.io/econ-calendar/data_releases.ics
```

Outlook polls these on its own schedule (a few hours, not instant). Set
your Outlook default timezone to UTC-4 — every event is stored in UTC in
the files, and Outlook converts to your default zone automatically.

---

## The 6 GitHub Actions workflows

Find these under the repo's **Actions** tab, each with its own run
history/logs — check the matching one first if a specific calendar looks
wrong.

| Workflow | Does | Schedule |
|---|---|---|
| **Update Forex Factory Calendar** | Fetches Forex Factory's near-term feed, writes `forexfactory_calendar.ics` | Every 4h |
| **Update Central Banks Calendar** | Re-renders `central_banks_calendar.ics` from existing scraped data (no website visits) | Every 4h |
| **Update Central Bank Dates** | Actually scrapes all 7 central banks' official sites, regenerates `central_bank_dates.json` | Weekly (Mon) |
| **Update Data Releases (BLS/BEA)** | Scrapes BLS + BEA official ICS feeds, regenerates `data_releases.json` + `data_releases.ics` | Weekly (Mon) |
| **Verify Central Bank Dates** | Text-presence sanity check (legacy, less critical now that real scrapers exist) | Monthly |
| **Remind to Verify Central Bank Dates** | Opens a GitHub Issue nudge to manually double-check | Quarterly |

**Key pattern throughout the project:** scraping (touches external
websites, can fail/break) is separated from ICS-building (just reads
already-scraped JSON, rarely fails) — so a website redesign only breaks
one weekly workflow, not everything.

---

## File-by-file map

### Repo root
| File | Purpose |
|---|---|
| `build_forexfactory_ics.py` | Builds `forexfactory_calendar.ics` |
| `build_central_banks_ics.py` | Builds `central_banks_calendar.ics` |
| `build_data_releases_ics.py` | Builds `data_releases.ics` |
| `ics_utils.py` | Shared ICS-writing logic (UID scheme, escaping) used by all 3 builders above |
| `verify_central_bank_dates.py` | Legacy text-presence checker |
| `bls_local_scraper.py` | Standalone Windows backup script (no longer needed day-to-day — BLS scraping works from GitHub Actions now via curl_cffi) |

### `sources/` — normalizes data into a common event shape
| File | Purpose |
|---|---|
| `forexfactory_source.py` | Fetches/filters Forex Factory JSON feed |
| `central_bank_source.py` | Reads `central_bank_dates.json`, titles events "X Interest Rate Decision" |
| `data_release_source.py` | Reads `data_releases.json`, keeps each release's real title (CPI, PPI, etc.) |
| `central_bank_dates.json` | **Auto-generated — don't hand-edit.** Overwritten weekly. |
| `data_releases.json` | **Auto-generated — don't hand-edit.** Overwritten weekly. |

### `scrapers/` — the actual website/feed scraping logic
| File | Purpose |
|---|---|
| `fomc_scraper.py`, `ecb_scraper.py`, `boe_scraper.py`, `boc_scraper.py`, `rba_scraper.py`, `boj_scraper.py`, `snb_scraper.py` | One per central bank — Fed, ECB, BoE, BoC, RBA, BoJ, SNB |
| `build_central_bank_json.py` | Runs all 7 bank scrapers, writes `sources/central_bank_dates.json` |
| `bls_scraper.py`, `bea_scraper.py` | US data release scrapers (real official ICS feeds) |
| `build_data_releases_json.py` | Runs BLS + BEA scrapers, writes `sources/data_releases.json` |
| `watched_releases.json` | **The one file you'll actually edit.** Controls which BLS/BEA releases are included. |

---

## What's covered right now

**Forex Factory** (near-term, current week only): AUD, CAD, EUR, JPY, GBP,
USD — High + Medium impact. France/Germany show as "EUR" (Forex Factory
groups by currency, not country).

**Central banks** (rate decisions, months ahead): FOMC, ECB, BoE, BoC,
RBA, BoJ, SNB.

**US data releases** (via `watched_releases.json`): CPI, PPI, ECI, JOLTS,
U.S. Import and Export Price Indexes, PCE (via BEA's "Personal Income and
Outlays").

**Known gap:** Weekly jobless claims — published by the Department of
Labor's ETA, a different agency, no scraper built for it yet.

---

## Routine maintenance (rare, low-effort)

1. **Add/remove a BLS or BEA release** → edit `scrapers/watched_releases.json`
   only. Plain JSON, exact title strings, no code changes needed.
2. **A scraper starts failing** (bank redesigns its page) → check the
   relevant weekly workflow's log. Failed scrapers fall back to last-known
   data automatically (tagged `STALE` in the event note) rather than going
   empty — so you'll see a visible signal in Outlook, not silent wrongness,
   before you fix it.
3. **Add a new central bank or agency** → same pattern each time: (a)
   fetch the bank/agency's real official calendar page, (b) verify its
   structure, (c) write a scraper matching that structure, (d) wire it
   into the relevant `build_*_json.py` orchestrator and the matching
   `_source.py` loader's title/URL mapping.

## Known caveats worth remembering

- **Timezone conversion is exact for BLS/BEA** (real IANA tz data via
  `zoneinfo`) but a **fixed-offset approximation for the other 7 central
  banks** — can be off by ~1hr during DST transitions.
- **Forex Factory only covers the current week** — no free forward-looking
  feed exists for it; central bank + BLS/BEA scrapers are what provide
  genuine months-ahead visibility.
- **BLS specifically requires `curl_cffi`** (Chrome TLS-fingerprint
  impersonation) — plain `urllib` gets a 403 even with realistic headers.
  Already wired into the workflow's `pip install curl_cffi` step; don't
  remove it if touching that workflow later.
