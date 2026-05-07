# tasks/todo.md — Streamarr

Current work tracking. Updated as tasks are completed.

---

## Current Session — Session G (CHG-043)

### Completed this session
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

## Blocked — Phase 3 (after P1 + P2 complete)
- P3-1 — Rank tracking over time
- P3-2 — Cross-source aggregation

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
