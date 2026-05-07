# tasks/todo.md — Streamarr

Current work tracking. Updated as tasks are completed.

---

## Current Session — Session G (CHG-043)

### Completed this session
- [x] P3-1 — Rank tracking over time (CHG-044)
- [x] T-015 — ID-based library matching / title mismatch fix (CHG-043)

### Completed previous session
- [x] P2-5 — Simulation / dry-run mode (CHG-042)
- [x] T-016 — Default poster placeholder (CHG-041)

---

## ✓ Confirmed satisfied — no implementation work required

### P2-3 — Compute status from tags not stored state
**Status: Satisfied.**
- `managed` = `streamarr` tag (tag-based ✓)
- `eligible` = `days_remaining <= 0 and not protected` (computed ✓)
- `date_added` from SyncLog is **metadata**, not state — Radarr/Sonarr `added`
  dates are unreliable (re-imports, upgrades). SyncLog.date_added stays.

### P2-4 — Standardise reason generation
**Status: Satisfied.**
All reason logic lives in `media_state.py`. `web.py` endpoints pass through
`entry["reason"]` directly. No duplication exists.
**Guardrail:** Do not move reason logic into `web.py` endpoints or frontend.

---

## Backlog — Session H+

---

## Backlog — Session H+
- P3-2 — Cross-source aggregation

### T-017 — Cross-card dismiss sync
When a title is dismissed in one Top 10 source card, the dismissed state should
immediately reflect in all other cards showing the same title. Currently the
dismiss button is applied per-card via `_applyTop10Data()` which reads the
shared `dismissed.json` store — but the UI only refreshes the card the user
interacted with. Fix: after a dismiss or undo, call `loadTop10Status()` which
re-applies to all `.top10-item` elements across all cards.

### T-019 — Tautulli: filter to tagged items only + active watches UI card
Two parts:

**Part 1 — Filter:** Tautulli currently fetches all recently-watched titles and
calls `set_last_watched()` for everything. Only titles tagged `streamarr` in
Radarr/Sonarr are managed by Streamarr — updating `last_watched` for unmanaged
items is wasted work and could produce misleading retention state if a title
later gets tagged. Fix: cross-reference the Tautulli result against the
tagged-items list from Radarr/Sonarr before writing to SyncLog. The tagged
item lists are already fetched in `_run()` — pass them through or fetch once
and reuse.

**Part 2 — UI card:** Add a card below the Protection Manager in the Protection
tab showing Tautulli-watched items (streamarr-tagged titles that have a
`last_watched` date in SyncLog). Label as "Active watches — retention extended"
to be precise (Tautulli is not a protection source per D4 — it only extends
the retention clock). Show title, type, and last watched date. Needs a new
API endpoint or extension of the existing `/api/media-state` response.

### T-018 — FlixPatrol scrape ban detection and rate limiting
FlixPatrol occasionally temp-bans scrapers. Need to:
- Detect ban signals (HTTP 429, 403, or empty/malformed response when content
  was previously available) and surface them clearly in the UI / logs
- Consider a per-hour sync cap for FlixPatrol fetches specifically (separate
  from the global sync interval) so repeated manual syncs don't trigger a ban
- Possibly expose last FlixPatrol fetch status in the Settings cache status
  area that already exists (`fpCacheStatus`)

---

## On Hold
- P4-1 — Plex collections
- P5-1 — Smart retention
- P6-1 — Policy engine

---

## Completed

### Session F hygiene (CHG-040)
- [x] T-012 — `config/manual_overrides.json` deleted; stale `.gitignore` entry removed
- [x] T-013 — `__pycache__/` confirmed in `.gitignore`
- [x] T-014 — `streamarrtree.txt` confirmed absent from repo
- [x] T-010 — 3 smoke tests added in `tests/test_netflix_fetcher.py` (pytest, all passing)

### Session E (CHG-038)
- [x] Fix `run_weekly_preview` tautulli_protected regression
- [x] Fix Radarr tag validation: `tag_source()` replaces `_` with `-`
- [x] Fix `undo_until` timezone: append `Z` so JS parses as UTC
- [x] P3-0 — Top 10item dismissal: `dismissed.py`, `config.py`, `sync_service.py`, `main.py`, `web.py`, `script.js`, `style.css`
- [x] Dismiss button (×) prepended left; undo button (↩) appears within 15-min window
- [x] `config/dismissed.json` added to `.gitignore`

### Session D (CHG-037)
- [x] P2-1 — Addition history: `log_add()` now accepts `sources: list[str]`; API returns `sources` list; UI displays joined ("Trakt + FlixPatrol")
- [x] P2-2 — Tautulli removed from protection model: `build_media_state()` takes only `manual_protected`; `protection_source` is `"manual" | None` only; stale UI text and CLAUDE.md rules updated

### Session C (CHG-036)
- [x] P1-5 — Deletion eligibility = streamarr tag only; all title-string matching removed from `run_deletions()`
- [x] P1-6 — Grace period removed; 7-day pre-deletion Pushover warning added (tracked in `pre_deletion_notified`)
- [x] P1-7 — Confirmed: `run_deletions()` and `_fetch_media_state()` source exclusively from `get_tagged_movies()` / `get_tagged_series()`

### Session B (CHG-033 / CHG-034 / CHG-035)
- [x] CHG-033 — tasks/ directory created and aligned with CLAUDE.md §13/§14
- [x] CHG-034 — P1-2 + P1-3: `streamarr-state-protected` tag introduced; ManualOverrides removed; protection writes immediately on UI toggle
- [x] CHG-035 — P1-4: `last_watched` retention anchor; Tautulli response parsing fixed

### Earlier
- [x] CHG-032 — P1-0 + P1-1: Multi-source tags + ownership check
- [x] CHG-031 — P1 core realignment (multi-source + ownership)
- [x] CHG-030 — Tag namespace: netflix-sync → streamarr
- [x] CHG-029 — Rebrand: Netflix Sync → Streamarr
- [x] CHG-028 — Dashboard UI improvements
- [x] CHG-027 — Phase 7: Docs and cleanup
- [x] CHG-026 — Phase 6: Caching, refresh, resilient errors
- [x] CHG-025 — Phase 5: Per-service movie/TV toggles
- [x] CHG-024 — Phase 3: Service selector with live preview
- [x] CHG-023 — Fix: lookup errors no longer crash sync
- [x] CHG-022 — Phase 2: FlixPatrol settings wiring
- [x] CHG-021 — Phase 1: FlixPatrol scraper vendored
