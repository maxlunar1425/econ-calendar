# econ-calendar
Filtered economic calendar for Outlook from Forex Factory
It also parse major Central Banks websites to extract meeting dates
It saves a .ics file that Outlook will retrieve
Outlook will also CalDav Synch with Gmail calendar for Android

After a modification go to Actions and Run Workflow for:
Update Central Bank Dates (Scraped from Official Sources) and then for Update Economic Calendar ICS


This will automatically forever be automated. 
The schedule runs itself. The workflow has cron: "0 6 * * 1" — every Monday at 06:00 UTC, forever, with no expiration. GitHub Actions doesn't need you to "renew" or re-trigger anything.
The year logic is dynamic, not hardcoded. Inside build_central_bank_json.py:
This always fetches "this year + next year" relative to whenever it happens to run. So in January 2027, it'll automatically fetch 2027 and 2028 — no code edit, no manual trigger, nothing. It rolls forward on its own permanently.
What actually happens month to month: each Monday, the scrapers hit all six official pages fresh, pick up whatever's newly published (banks typically publish next year's schedule sometime around August–December), and commit the updated JSON automatically. Your Outlook feed then picks up the changes on its own next poll — you never touch anything.

The one thing worth occasionally checking (not running, just watching): if a bank ever redesigns its webpage, that specific scraper could start returning 0 results or erroring out. You wouldn't need to manually fix this in the moment — the fallback logic already handles it gracefully (falls back to last-known-good data, tagged STALE in the note, rather than silently going empty). But eventually someone would need to update that one scraper's regex to match the new page layout. A reasonable habit: skim the weekly Action run logs every month or two, or just wait until you notice a STALE tag show up in Outlook, since that's a visible signal something needs attention.
So to directly answer: no manual runs required, ever, under normal circumstances. The only trigger for manual intervention is a website redesign breaking a scraper — and even then, it degrades gracefully rather than breaking silently.
