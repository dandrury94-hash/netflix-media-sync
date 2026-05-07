# tasks/todo.md — Streamarr

Current work tracking. Updated as tasks are completed.

---

## Current Session — Session I (CHG-050–058)

### Completed this session
- [x] P4-1 follow-up — Plex collection sort + remove (CHG-050)
- [x] P4-1 follow-up — Plex settings save fix (CHG-051)
- [x] P4-1 follow-up — Service collections for pre-Streamarr items (CHG-052–055)
- [x] P4-1 follow-up — Streamarr collection includes all service-tagged items (CHG-056)
- [x] CHG-057 — Batch protection endpoint; CHANGELOG separator cleanup
- [x] CHG-058 — Verified removal history wiring and netflix source stub removal

### Completed previous session (Session H)
- [x] T-017 — Cross-card dismiss sync (confirmed already working, no change needed)
- [x] T-019 — Tautulli filter to tagged items + active watches UI card (CHG-046)
- [x] T-018 — FlixPatrol ban detection + rate limiting (CHG-047)
- [x] P4-1 — Plex collections (CHG-049)

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

### P4-1 — Plex collections
**Status: Complete.** (CHG-049 through CHG-056)
- Per-service collections (Netflix, Disney+, Amazon Prime, etc.) in both libraries
- Main Streamarr collection covers all service-tagged items (root tag OR src tag)
- Source attribution keyed by tmdbId/tvdbId (not title) — title-mismatch safe
- Merge loop writes service tags to pre-Streamarr library items

---

## Backlog

### F-001 — One-shot preview sync button
**Effort: Medium**

Add a "Preview" button to the Status & Actions card that runs a single simulation-mode sync without touching the persistent `simulation_mode` setting.

- **`app/sync_service.py`** — add optional `simulate: bool | None = None` to `run_once()`; when provided, use it instead of `self.settings.get("simulation_mode")` for that call only
- **`app/web.py`** — `POST /api/sync` reads optional `{"simulate": true}` from JSON body and passes it to `run_once()`
- **`app/templates/index.html`** — add a "Preview" button alongside "Sync Now" in the Status & Actions card
- **`app/static/script.js`** — Preview handler calls `POST /api/sync` with `{simulate: true}`; renders `would_add_movies` / `would_add_series` from the response in the same result area as a normal sync

No settings change, no persistent state mutation.

---

### F-002 — Next sync countdown in Status & Actions card
**Effort: Low**

Surface "Next sync in X min" (or "Overdue") beneath the last sync timestamp. The run interval already exists as `run_interval_seconds` in settings; the last sync timestamp is in SyncLog.

- **`app/web.py`** — add `GET /api/sync-status` endpoint returning `{"last_sync_ts": float | null, "run_interval_seconds": int}` (reads `sync_log.get_last_sync()` for timestamp and `settings.get("run_interval_seconds")` for interval)
- **`app/static/script.js`** — on page load, fetch `/api/sync-status`; compute `next_sync_ts = last_sync_ts + run_interval_seconds`; display relative time in the Status & Actions card; refresh the display after any manual sync completes

No template changes needed — the display is JS-rendered.

---

### F-003 — Title search filter on scheduled removals table
**Effort: Low**

The Protection Manager already has a live client-side search input (`#protSearchInput`, `keyup` listener at script.js:794). Apply the same pattern to the scheduled removals table.

- **`app/templates/index.html`** — add `<input id="removalSearchInput" class="prot-search" placeholder="Search titles…">` above the scheduled removals table (match the Protection Manager layout)
- **`app/static/script.js`** — add `keyup` listener on `#removalSearchInput` that shows/hides `<tr>` rows based on whether the title cell matches the input; same case-insensitive substring approach as the existing protection search
- **`app/static/style.css`** — reuse existing `.prot-search` / `.prot-search-wrap`; add a wrapper div in the template if needed; no new CSS rules expected

---

## On Hold
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
