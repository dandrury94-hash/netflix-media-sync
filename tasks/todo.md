# tasks/todo.md — Streamarr

Current work tracking. Updated as tasks are completed.

---

## Current Session
Session C (CHG-036) — P1-5, P1-6, P1-7 implemented. Awaiting user verification.

---

## Up Next — Session D (CHG-037)

### P1-2 — Introduce streamarr-state-protected tag ✓
- [x] Add `TAG_STATE_PROTECTED = "streamarr-state-protected"` to `app/tags.py`
- [x] Add helper `tag_state_protected() -> str` to `app/tags.py`
- [x] Document in root `CLAUDE.md` tag vocabulary section (already present)

### P1-3 — Move protection to tag, write immediately on UI toggle ✓
- [x] Remove `ManualOverrides` from `app/manual_overrides.py` (deleted)
- [x] Remove `ManualOverrides` from `app/main.py` instantiation
- [x] Remove `ManualOverrides` from `app/sync_service.py`
- [x] Update `POST /api/overrides` in `app/web.py` to write
      `streamarr-state-protected` tag directly to Radarr/Sonarr immediately
- [x] Update `_fetch_media_state()` to read protection from tags
      not from `ManualOverrides`
- [x] Update UI — protection toggle sends `type` field, all call sites updated
- [ ] Verify: toggling protection in UI immediately writes tag to
      Radarr/Sonarr without waiting for next sync

### P1-4 — Tautulli: reset retention clock on last_watched ✓
- [x] Add `last_watched` field to `SyncLog` entry schema
- [x] Update `SyncService._run()` to write `last_watched` date
      when Tautulli reports a title as watched
- [x] Update retention calculation in `run_deletions()`:
      anchor = `max(date_added, last_watched)`
- [x] Same anchor applied in `media_state.py` and weekly preview
- [x] Verify: watching a title resets the 30-day clock from
      that watch date

### Pre-flight checks before starting
- [ ] Run `git status` — confirm clean working tree
- [ ] Run `git branch` — confirm on feature/flixpatrol-integration
- [ ] Grep CHANGELOG.md for last CHG number — confirm next is CHG-033
- [ ] Read all CLAUDE.md files before writing any code

---

## Completed — Session C (CHG-036)

### P1-5 — Rewrite deletion logic to use tags only ✓
- [x] Remove all title-string matching from `run_deletions()`
- [x] Deletion eligibility = `streamarr` tag present only
- [x] Items whose tag is removed externally are silently excluded
- [x] Document this behaviour in a comment in `run_deletions()`

### P1-6 — Replace grace period with 7-day pre-deletion notification ✓
- [x] Remove grace period tracking from `SyncLog`
- [x] Remove `start_grace_period()`, `get_grace_periods()`,
      `clear_grace_period()` from `app/sync_log.py`
- [x] Remove grace period logic from `run_deletions()`
- [x] Add pre-deletion Pushover notification 7 days before
      deletion date
- [ ] Verify: no grace period state remains in any code path
      (`grep -r "grace"` returns nothing in active paths)

### P1-7 — Restrict evaluation to streamarr-tagged items only ✓
- [x] `run_deletions()` must only process items with `streamarr` tag
- [x] `_fetch_media_state()` must only surface streamarr-tagged items
- [x] Unmanaged library items must never appear in any Streamarr UI

---

## Backlog — Session D (CHG-036)
Do not start until P1 is complete.

### P2-1 — Addition history source display fix
- [ ] `log_add()` in `app/sync_log.py` must store `source` field
- [ ] `SyncService._run()` must pass `item["source"]` to `log_add()`
- [ ] `/api/addition-history` must return `source` field
- [ ] UI must display source per entry (not hardcoded "Trakt")

### P2-2 — media_state read-only from tags
- [ ] `build_media_state()` reads protection from `streamarr-state-protected`
      tag, not from `ManualOverrides` or stored state

### P2-3 — Compute status from tags not stored state
- [ ] Status (managed, protected, eligible) derived from tag presence
      at read time, not from stored values

### P2-4 — Standardise reason generation
- [ ] Single `reason` helper used consistently across all endpoints
- [ ] No duplicated reason-string logic across web.py and media_state.py

---

## Backlog — Session E (CHG-037)
### P2-5 — Simulation / dry-run mode
- [ ] New `simulation_mode` setting (bool, default false)
- [ ] When enabled: fetch + evaluate + log what would happen
- [ ] No writes to Radarr/Sonarr/SyncLog in simulation mode
- [ ] UI indicator when simulation mode is active

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
- [x] CHG-021 — Phase 1: FlixPatrol scraper vendored
- [x] CHG-022 — Phase 2: FlixPatrol settings wiring
- [x] CHG-023 — Fix: lookup errors no longer crash sync
- [x] CHG-024 — Phase 3: Service selector with live preview
- [x] CHG-025 — Phase 5: Per-service movie/TV toggles
- [x] CHG-026 — Phase 6: Caching, refresh, resilient errors
- [x] CHG-027 — Phase 7: Docs and cleanup
- [x] CHG-028 — Dashboard UI improvements
- [x] CHG-029 — Rebrand: Netflix Sync → Streamarr
- [x] CHG-030 — Tag namespace: netflix-sync → streamarr
- [x] CHG-031 — P1 core realignment (multi-source + ownership)
- [x] CHG-032 — P1-0 + P1-1: Multi-source tags + ownership check