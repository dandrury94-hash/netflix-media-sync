"""
app.scraper — vendored FlixPatrol streaming Top 10 scraper.

Copied from https://github.com/dandrury94-hash/streaming-scraper (Option A —
files copied directly, no submodule or pip dependency).

If FlixPatrol changes its HTML structure and titles stop returning, update
app/scraper/sources/streaming.py selectors and test with a manual fetch.

Public surface used by NMS:
    from app.scraper.sources.streaming import fetch, COUNTRIES
    from app.scraper.core.aggregator import aggregate, group_by_source_and_type
"""
