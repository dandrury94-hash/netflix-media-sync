# tasks/todo.md — Streamarr

Current work tracking. Updated as tasks are completed.

---

## Current Session
None in progress.

---

## Up Next — Session E (CHG-038)

### Pre-flight checks before starting
- [ ] Run `git status` — confirm clean working tree
- [ ] Run `git branch` — confirm on feature/flixpatrol-integration
- [ ] Grep CHANGELOG.md for last CHG number — confirm next is CHG-038
- [ ] Read all CLAUDE.md files before writing any code

### CHG-037 follow-up — `run_weekly_preview` tautulli_protected regression

**Context:** P2-2 removed Tautulli from the protection model in `web.py` and
`media_state.py` but `run_weekly_preview` in `app/main.py` was not updated.
Lines 79, 90, and 116 still reference `tautulli_protected` to suppress weekly
preview notifications — contradicting the new model where Tautulli is a
retention signal only, not a protection source.

- [ ] Remove `tautulli_protected = set(last_sync.get("protected", []))` (line 79)
- [ ] Remove `title in tautulli_protected or` from both skip conditions
      (lines 90 and 116) — keep only the `manually_protected` check
- [ ] No other changes to `run_weekly_preview`

This fix should be committed as part of CHG-038 before the dismissal work.

### P3-0 — Top 10 item dismissal

**Context:** User wants a red X on each Top 10 dashboard item. Clicking it
permanently dismisses the title: future syncs skip it (never added), and if it
is already in the library the media is deleted after a 15-minute grace window.
Dismissed titles remain dismissed until manually undone — they continue to
appear in the Top 10 list but greyed out, even if re-listed by the source.

**Design decisions (confirmed):**
- Permanent until manually undone. Re-listing from source keeps it greyed out.
- Background daemon thread (60s poll) fires the deletion — does not wait for
  next scheduled sync.
- Dedicated `dismissed.json` store (same pattern as `removal_history.json`).
  CLAUDE.md files and `config.py` updated to reflect the new store.

---

#### New file — `app/dismissed.py`

New `DismissedTitles` class. Persistent JSON at path from `config.DISMISSED_PATH`.

Storage format per entry:
```json
{
  "The Devil Wears Prada": {
    "type": "movie",
    "dismissed_at": "2026-05-06T16:41:00",
    "in_library": true
  }
}
```

- `dismiss(title, type, in_library: bool)` — adds entry; `dismissed_at` = now
- `undismiss(title)` — removes entry unconditionally
- `get_all() -> dict[str, dict]` — returns full store
- `is_dismissed(title) -> bool`
- `get_pending_deletion() -> list[dict]` — returns entries where
  `in_library=True` and `(now - dismissed_at) >= 15 minutes`
- `mark_deleted(title)` — sets `in_library=False` to prevent re-deletion
  attempts after the file/series has been removed

Thread-safe (`threading.Lock`). Same `_load`/`_save` pattern as `SyncLog`.

#### `app/config.py`

- [ ] Add `DISMISSED_PATH = Path(os.getenv("DISMISSED_PATH", "/config/dismissed.json"))`

#### `app/sync_service.py`

- [ ] Accept `dismissed: DismissedTitles` in `__init__`; store as `self.dismissed`
- [ ] In `_run()` movie loop: skip `item` if `self.dismissed.is_dismissed(item["title"])`
- [ ] In `_run()` series loop: same skip
- [ ] New method `run_dismissal_deletions() -> dict`:
  - Calls `self.dismissed.get_pending_deletion()` to get titles due for removal
  - For movies: look up in `radarr.get_all_movies()`, call `radarr.delete_movie(id)` if found
  - For series: look up in `sonarr.get_all_series()`, call `sonarr.delete_series(id)` if found
  - On success: `self.removal_history.log_removal(title, type, reason="dismissed", was_watched=...)`
  - On success: `self.dismissed.mark_deleted(title)`
  - On success: send Pushover notification
  - Calls `self.dismissed.mark_deleted(title)` whether deletion succeeded or not,
    to prevent infinite retry on items that were already manually removed
  - Returns `{"dismissed_deleted_movies": [...], "dismissed_deleted_series": [...]}`

#### `main.py`

- [ ] Import `DismissedTitles`; construct and pass to `SyncService`
- [ ] After service starts, launch a daemon thread that calls
  `sync_service.run_dismissal_deletions()` every 60 seconds:
  ```python
  def _dismissal_loop(svc):
      while True:
          time.sleep(60)
          try:
              svc.run_dismissal_deletions()
          except Exception:
              logger.exception("Dismissal deletion loop error")

  threading.Thread(target=_dismissal_loop, args=(sync_service,), daemon=True).start()
  ```

#### `app/web.py`

- [ ] Import `DismissedTitles`; accept it in `create_app()`
- [ ] `POST /api/dismiss` — payload `{title, type, in_library: bool}`:
  - Validates `title` non-empty, `type` in ("movie", "series"), `in_library` is bool
  - Calls `dismissed.dismiss(title, type, in_library)`
  - Returns `{"status": "ok", "title": title, "in_library": in_library,
    "undo_until": (dismissed_at + 15 min).isoformat()}`
- [ ] `DELETE /api/dismiss` — payload `{title}`:
  - Calls `dismissed.undismiss(title)`
  - Returns `{"status": "ok", "title": title}`
- [ ] `GET /api/top10-status` — extend each entry to include:
  - `"dismissed": bool` — whether title is in dismissed store
  - `"undo_until": str | null` — ISO timestamp 15 min after `dismissed_at`,
    only present if dismissed; frontend uses this to show/hide the undo button

#### `app/static/script.js`

- [ ] `renderTop10Item(title, statusData)` — existing inline `<li>` rendering
  extracted or updated to support dismissed state:
  - If `statusData.dismissed`: add `dismissed` CSS class to `<li>`,
    render red-strike or grey text
  - Render a red `×` dismiss button on every non-dismissed item
  - If `statusData.dismissed && Date.now() < Date.parse(statusData.undo_until)`:
    render an "Undo" button alongside the greyed title
- [ ] On `×` click: `POST /api/dismiss` with `{title, type, in_library}` where
  `in_library = status !== "will_add" && status !== "disabled"`;
  on success refresh the top10 status for that card
- [ ] On "Undo" click: `DELETE /api/dismiss` with `{title}`;
  on success refresh the top10 status for that card
- [ ] `top10-status` polling already runs on page load — no new polling needed;
  dismiss/undo actions trigger an immediate re-fetch of `/api/top10-status`

**Constraint:** `in_library` is determined by the frontend from the existing
`top10-status` response (`status !== "will_add" && status !== "disabled"`)
and passed to `POST /api/dismiss`. The backend stores it as provided — no
additional Radarr/Sonarr lookup at dismiss time.

**Constraint:** `run_dismissal_deletions()` always calls `mark_deleted()` after
attempting deletion, regardless of outcome — prevents infinite retry if the
item was already removed from Radarr/Sonarr externally.

**Constraint:** Do not remove dismissed entries from the store after deletion.
The entry must persist so the title stays greyed out and is not re-added by
future syncs.

#### `app/CLAUDE.md` + `CLAUDE.md`

- [ ] Add `dismissed.json` to the persistence layer description
- [ ] Note that `DismissedTitles` is the third persistence store alongside
  `SyncLog` and `RemovalHistory`

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

## Backlog — Session F (CHG-039)
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
