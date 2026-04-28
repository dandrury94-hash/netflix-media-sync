# Changelog

All changes to this project are recorded here with a unique reference, date, and description.

---

## CHG-018 — 2026-04-28 — UK timestamp format on Last Sync

### Changed
- `SyncLog.set_last_sync()` now stores the timestamp using `strftime("%H:%M %d/%m/%Y")` instead of `.isoformat(timespec="seconds")`, producing e.g. `07:24 28/04/2026`. Timezone is the server's local time (`app/sync_log.py`)
- `index()` route now reformats the `timestamp` field from the stored sync record before passing it to the template. `_fmt_timestamp()` parses ISO 8601 strings (`%Y-%m-%dT%H:%M:%S` and `%Y-%m-%dT%H:%M`) and converts them to `%H:%M %d/%m/%Y`; any already-formatted or unrecognised string is passed through unchanged. This means existing stored ISO timestamps display in UK format immediately without requiring a new sync (`app/web.py`)

---

## CHG-017 — 2026-04-28 — Status & Actions card redesign and inline sync progress

### Changed
- **Status & Actions card** restructured with a four-section flex layout (`display:flex; flex-direction:column; justify-content:space-between`) so the card fills the same height as the adjacent Top 10 cards. Bold dividers (`.card-divider`, `rgba(255,255,255,0.13)`) separate each section; integration items and sync-stat rows use lighter CSS `border-bottom` rules (`rgba(255,255,255,0.06)` / existing `rgba(255,255,255,0.05)`) (`app/templates/index.html`, `app/static/style.css`)
- "Integration status" rendered as a small-caps section label (`.sac-section-label`) above the integration list. "Last Sync" row is a flex row with the timestamp right-aligned (`app/templates/index.html`, `app/static/style.css`)
- Sync progress bar replaced with an **inline button fill**: the button spans the full card width with left-aligned text. During sync, `--sync-pct` CSS custom property drives a `::before` fill that sweeps left-to-right from 0 → 90% (animated) then jumps to 100% on success. `.syncing` class changes button background to `rgba(77,140,255,0.22)` while the `::before` gradient overlays the filled portion. On failure, `.sync-error` adds a `⚠` via `::after` on the right edge, auto-cleared after 3 s (`app/static/script.js`, `app/static/style.css`)
- Separate `#syncProgress` / `#syncProgressBar` divs removed; `.sync-progress*` CSS classes removed (`app/templates/index.html`, `app/static/style.css`)

---

## CHG-016 — 2026-04-28 — Sync progress bar with duration estimate

### Changed
- `SyncService.run_once()` now records wall time around `_run()` using `time.monotonic()` and adds `duration_seconds` (int) to the result dict. `set_last_sync()` is now called in `run_once()` (after duration is known) rather than inside `_run()` (`app/sync_service.py`)
- `POST /api/sync` reads `duration_seconds` from the previous sync via `sync_log.get_last_sync()` before running, and returns `estimated_seconds` (defaulting to 60 if no history exists) alongside the sync result (`app/web.py`)
- Sync button handler rewritten — removes `syncResult` text box entirely. On click: disables button, sets text to "Syncing…", shows progress bar and animates 0 → 90% over `syncEstimatedSeconds` via `setInterval` every 500 ms. On success: jumps to 100%, waits 600 ms, hides bar, restores button, reloads page. On failure: sets error colour for 1500 ms then resets button. `syncEstimatedSeconds` is seeded from `data-estimated` on the button element and updated from each response (`app/static/script.js`)
- `const syncResult` variable removed from `DOMContentLoaded` scope (`app/static/script.js`)

### Added
- `<div id="syncProgress">` / `<div id="syncProgressBar">` injected below the sync button. `data-estimated` attribute on the button seeds the initial animation duration from the last sync's recorded time (`app/templates/index.html`)
- "Runs immediately alongside the scheduled interval." field-help paragraph above the sync button (`app/templates/index.html`)
- `.sync-progress` — 4 px tall, full-width, `rgba(255,255,255,0.08)` track, `overflow: hidden` (`app/static/style.css`)
- `.sync-progress-bar` — gradient fill matching the primary button, `transition: width 0.5s linear` (`app/static/style.css`)
- `.sync-progress-bar--error` — solid `#e05252` fill for failure state (`app/static/style.css`)

### Removed
- `<div id="syncResult">` text status box removed from the Actions card (`app/templates/index.html`)

---

## CHG-015 — 2026-04-28 — Addition history in History tab

### Added
- `GET /api/addition-history` endpoint: reads `SyncLog.get_entries()`, filters to entries with `date_added` within the last 7 days, deduplicates by title (most recent entry kept), and returns `{"additions": [...]}` sorted newest-first. Uses the existing sync log — no new storage or dependencies (`app/web.py`)
- **Recently Added** table at the top of the History tab, showing title, type, date added, and source for each unique title added in the last 7 days. Loaded asynchronously on tab reveal (`app/templates/index.html`, `app/static/script.js`)
- `loadAdditionHistory(tbody)` and `renderAdditionHistory(tbody, additions)` JS functions (`app/static/script.js`)

---

## CHG-014 — 2026-04-28 — Dashboard layout compaction

### Changed
- Integration Status, Last Sync Summary, and Actions cards merged into a single **Status & actions** card, reducing the grid from three narrow cards to one. Content is separated by `.setting-divider` rules (`app/templates/index.html`)
- Dashboard page subtitle updated to reflect the removed Protected Titles section

### Removed
- **Protected Titles** card removed from the Dashboard tab. Full protection management is available via the dedicated Protection tab (`app/templates/index.html`)

---

## CHG-013 — 2026-04-28 — Poster art on Top 10 panels

### Changed
- `GET /api/top10-status` response shape updated: each title value is now an object `{"status": "...", "poster": "<url>|null"}` instead of a plain status string. The `poster` field contains the `remoteUrl` of the first image with `coverType == "poster"` from the Radarr/Sonarr lookup stub, or `null` if none is found. No new API calls are introduced — the poster URL is extracted from the same lookup response already used for status determination (`app/web.py`)
- `loadTop10Status()` updated to read the new object shape: reads `item.status` for icon rendering (behaviour unchanged) and `item.poster` for the new thumbnail. When a poster URL is present, sets `--poster-url` as a CSS custom property on the `<li>` element and adds the class `top10-item--has-poster` (`app/static/script.js`)
- Poster thumbnail repositioned to the **left** of the title; a 1 px faint vertical divider (`::after` pseudo-element, `rgba(255,255,255,0.07)`) separates it from the title and status icon. `padding-left: 44px` ensures text does not overlap (`app/static/style.css`)

### Added
- `.top10-item--has-poster` CSS rule: `position: relative`, `overflow: hidden`, `padding-left: 44px`. `::before` poster thumbnail at left edge, 36×54 px, `opacity: 0.55`. `::after` 1 px divider at `left: 36px`, full height. Missing or broken images fail silently (`app/static/style.css`)
- `_extract_poster(images)` helper function returns the `remoteUrl` of the first poster-type image or `None` (`app/web.py`)
- "How It Works" section added to README covering sync, grace period, and poster art sourcing
- Poster art bullet added to Features list; poster sourcing note added to Radarr and Sonarr rows in the configuration table (`README.md`)

---

## CHG-012 — 2026-04-27 — Protection manager

### Added
- `GET /api/protection-state` endpoint: fetches all `netflix-sync` tagged titles from Radarr and Sonarr in one bulk call each, determines protection status from the last Tautulli sync result and the manual overrides set, and returns `{"protected": [...], "unprotected": [...]}` sorted alphabetically. Failures in either service are caught and skipped without affecting the other (`app/web.py`)
- **Protection tab** in the top navigation bar; clicking it switches to the protection manager panel client-side (`app/templates/base.html`, `app/templates/index.html`, `app/static/script.js`)
- **Protection manager panel** — two-column layout (Protected / Not Protected) loaded asynchronously from `GET /api/protection-state`:
  - Each protected item shows title, type badge, source badge (Tautulli or Manual), and either an **Unprotect** button (manual) or a "Tautulli protected" lock label (Tautulli — unprotection not allowed)
  - Each unprotected item shows title, type badge, and a **Protect** button
  - Protect / Unprotect actions POST to the existing `/api/overrides` endpoint and refresh the panel in-place (`app/static/script.js`)
- `loadProtectionState(container)`, `renderProtectionState(container, data)`, `handleProtectionToggle(btn, title, protect, container)` JS functions (`app/static/script.js`)
- Protection manager CSS: `.protection-manager`, `.prot-col-header`, `.prot-entry`, `.prot-entry-meta`, `.prot-source-badge`, `.prot-lock-label`, `.prot-action-btn` (`app/static/style.css`)

---

## CHG-011 — 2026-04-27 — Pushover notifications, automatic deletion, and removal history

### Added
- **Pushover notifications** (`app/pushover_client.py`):
  - `PushoverClient` class wrapping the Pushover API (`https://api.pushover.net/1/messages.json`)
  - `is_enabled()` — returns `True` only when `pushover_enabled`, `pushover_user_key`, and `pushover_api_token` are all set
  - `send(title, message, priority)` — never raises; logs a warning on delivery failure
  - Notifications sent for: titles added during sync, per-title deletion, and sync errors (priority 1)
  - `POST /api/test/pushover` endpoint for in-UI delivery test (`app/web.py`)
  - Pushover card in Settings with enable checkbox, user key, API token, and test button (`app/templates/settings.html`)
- **Automatic deletion with grace period** (`app/sync_service.py`):
  - `SyncService.run_deletions()` — runs after every sync when `deletion_enabled` is `True`
  - Only processes titles tagged `netflix-sync` in Radarr / Sonarr; protected titles are never deleted
  - Two-phase flow: title first enters a grace period (`sync_log.start_grace_period`), then is deleted once `grace_period_days` have elapsed
  - `grace_period_days` and `deletion_enabled` settings added to `DEFAULT_SETTINGS` and `ENV_VAR_TO_SETTING` (`app/config.py`)
  - Deletion checkbox and grace-period input added to the Retention & sync settings card with a `⚠️` warning (`app/templates/settings.html`)
- **Grace period tracking** (`app/sync_log.py`):
  - `grace_periods` dict added to persisted state; migrated in on load if absent
  - `start_grace_period(title, media_type)` — idempotent; only records start date on first call
  - `get_grace_periods()` — returns the full dict
  - `clear_grace_period(title)` — removes the entry after successful deletion
- **Removal history** (`app/removal_history.py`):
  - `RemovalHistory` class persisting deletions to `/config/removal_history.json`
  - `log_removal(title, media_type, reason, was_watched)` — appends an entry and saves
  - `get_recent(days)` — returns entries within the given window (default 180 days)
  - `_save()` prunes entries older than 180 days before writing
  - `GET /api/removal-history` endpoint (`app/web.py`)
- **History tab** (`app/templates/index.html`, `app/templates/base.html`, `app/static/script.js`):
  - History tab added to the top navigation bar alongside Dashboard and Logs
  - 5-column table (Title, Type, Date removed, Reason, Watched) loaded asynchronously
  - `loadRemovalHistory(tbody)` and `renderHistory(tbody, history)` functions in `script.js`
- **Scheduled removals table expanded** (`app/templates/index.html`, `app/static/script.js`):
  - Two new columns: **Grace expires** and **Days to delete**
  - `Days to delete` colour-coded: red (≤ 2 days), yellow (≤ 5 days), green (> 5 days)
  - "Due" label shown when `days_until_deletion` ≤ 0
- **Weekly deletion preview** (`app/main.py`):
  - `run_weekly_preview()` daemon thread wakes on the next Saturday at 05:00
  - Scans tagged titles with upcoming removal dates within 7 days and sends a Pushover summary
  - Silently skips if Pushover is not enabled
- **Module-level `_resolve_date()` helper** (`app/sync_service.py`) — resolves a title's add date from the sync log, the Radarr/Sonarr API `added` field, or a fallback date, in that priority order

### Changed
- `SyncService.__init__` now accepts `removal_history: RemovalHistory` and instantiates `PushoverClient` (`app/sync_service.py`)
- `create_app` now accepts `removal_history` parameter and passes it to the removal-history endpoint (`app/web.py`)
- `main()` instantiates `RemovalHistory` and passes it to both `SyncService` and `create_app` (`app/main.py`)
- Settings form `post_settings` adds a `to_bool()` helper for checkbox fields (`deletion_enabled`, `pushover_enabled`) (`app/web.py`)
- `_SENSITIVE_KEYS` extended with `pushover_user_key` and `pushover_api_token` (`app/web.py`)
- Scheduled removals table colspan updated from 6 to 8 for empty-state rows (`app/static/script.js`)
- `.setting-checkbox` and `.setting-divider` styles added for the new settings form layout (`app/static/style.css`)

---

## CHG-010 — 2026-04-27 — Bug fixes from CHG-009

### Fixed
- `SyncService._run()`: `radarr_cache` and `sonarr_cache` were only assigned inside `if mode != "disabled"` blocks but referenced in the `enabled` / `read` branches below, causing a potential `NameError` when either integration is disabled. Both are now initialised to `{}` before the conditional blocks (`app/sync_service.py`)
- Topnav Dashboard and Logs links had no active class applied on initial page load — active state was only set by the click handler. On `DOMContentLoaded`, the Dashboard link now receives the `active` class when the page is the index route. The hardcoded Jinja active-class expression and the empty `class=""` attribute have been removed from both tab-target links in the template, as active state is managed entirely by JS for those links (`app/static/script.js`, `app/templates/base.html`)

---

## CHG-009 — 2026-04-27 — Sync performance, status accuracy, and Logs nav

### Fixed
- `/api/top10-status` now fetches the real library record (`GET /api/v3/movie/{id}` / `GET /api/v3/series/{id}`) when a title is found in Radarr/Sonarr, instead of relying on the search-stub response which does not return accurate `hasFile` / `episodeFileCount` data (`app/web.py`, `app/radarr_client.py`, `app/sonarr_client.py`)

### Added
- `RadarrClient.get_all_movies()` — fetches full library in one call; returns `[]` and logs a warning on failure (`app/radarr_client.py`)
- `RadarrClient.get_movie_by_id(movie_id)` — fetches a single library record by Radarr ID (`app/radarr_client.py`)
- `SonarrClient.get_all_series()` — fetches full library in one call; returns `[]` and logs a warning on failure (`app/sonarr_client.py`)
- `SonarrClient.get_series_by_id(series_id)` — fetches a single library record by Sonarr ID (`app/sonarr_client.py`)
- **Logs** added to the main top navigation bar as a peer of Dashboard and Settings; clicking it switches the panel client-side without a page reload (`app/templates/base.html`, `app/templates/index.html`, `app/static/script.js`)

### Changed
- `RadarrClient.add_movie` and `SonarrClient.add_series` accept an optional `library_cache` dict (normalised lowercase title → record); if the title is found with a non-zero id the method returns `False` immediately without a network call (`app/radarr_client.py`, `app/sonarr_client.py`)
- `SyncService._run()` calls `get_all_movies()` / `get_all_series()` once per sync run (when the mode is not `disabled`) and passes the resulting cache into all `add_movie` / `add_series` calls, eliminating up to 20 sequential existence-check requests per sync (`app/sync_service.py`)
- Read-mode existence check in `_run()` now uses the bulk cache directly instead of calling `lookup_movie` / `lookup_series` per title (`app/sync_service.py`)
- In-page tab switcher (Dashboard / Logs buttons) removed from the dashboard page; Logs is now in the topnav (`app/templates/index.html`)
- `run_worker` in `main.py` already reads `run_interval_seconds` after each sync run; added inline comment making this explicit (`app/main.py`)

---

## CHG-008 — 2026-04-27 — Dashboard improvements

### Added
- Tab navigation bar on dashboard with **Dashboard** and **Logs** tabs; all log content moved to the Logs tab, freeing the main grid from the log panel (`app/templates/index.html`, `app/static/script.js`, `app/static/style.css`)
- Log output dynamically fills available screen height via `calc(100vh - 370px)` with a 300 px minimum (`app/static/style.css`)
- Status icons for Trakt Top 10 Movies and Series panels:
  - ⏳ Pending (monitored, no file)
  - ✅ Available (file downloaded)
  - ➕ Will Add (not in library)
  - ➖ Disabled (integration off)
  - Loaded asynchronously with tooltip labels (`app/static/script.js`, `app/templates/index.html`)
- `GET /api/top10-status` endpoint querying Radarr/Sonarr for per-title status; skips individual failures (`app/web.py`)

### Changed
- Increased log scrollback buffer from 100 to 2000 lines (`app/web.py`)

---

## CHG-007 — 2026-04-27 — Test connection buttons

### Added
- Test connection buttons for Radarr, Sonarr, and Tautulli in Settings (`app/templates/settings.html`)
- `POST /api/test/radarr` and `/api/test/sonarr` endpoints:
  - Validate URL + API key
  - Return quality profiles and root folders on success (`app/web.py`)
- `POST /api/test/tautulli` endpoint returning Plex server name (`app/web.py`)
- Dynamic UI replacement of quality profile/root folder inputs with populated dropdowns (`app/static/script.js`)
- Clear connection feedback:
  - `✅ Connected`
  - `❌ <reason>` with specific error handling (`app/static/script.js`, `app/static/style.css`)
- Support for `__REDACTED__` sentinel resolving to stored API key (`app/web.py`)

### Changed
- Improved UX for integration setup via inline validation and dynamic field updates

### Infrastructure
- Added shared helpers `_resolve_test_key`, `_exc_msg`, `_test_arr`
- Added `import requests as _requests` alias (`app/web.py`)

---

## CHG-006 — 2026-04-27 — Live log feed

### Added
- `GET /api/logs` endpoint returning last 100 log lines (`app/web.py`)
- `POST /api/logs/clear` endpoint to truncate log file (`app/web.py`)
- `_tail_file(path, n)` helper for efficient log reading (`app/web.py`)
- Live log panel with:
  - Polling every 3 seconds
  - Colour-coded levels
  - Auto-scroll behavior (`app/templates/index.html`, `app/static/script.js`, `app/static/style.css`)
- Log controls:
  - Pause/Resume with status badge
  - Download logs as `.log`
  - Clear logs (`app/static/script.js`)
- Monospace, selectable, wrapped log output (`app/static/style.css`)

### Infrastructure
- Added `RotatingFileHandler`:
  - `/config/app.log`
  - 5 MB max, 3 backups (`app/main.py`)
- Unified logging format across handlers (`app/main.py`)
- Added `LOG_PATH` config with env override (`app/config.py`)

---

## CHG-005 — 2026-04-27 — Dashboard features

### Added
- Integration status panel (Radarr, Sonarr, Tautulli) with colour indicators (`app/templates/index.html`, `app/static/style.css`)
- Trakt Top 10 movies and series panels (`app/templates/index.html`)
- Import preview panel (added / would-add / already-in-library states)
- `netflix-sync` tagging system for Radarr/Sonarr:
  - Auto-created if missing
  - Graceful fallback (`app/radarr_client.py`, `app/sonarr_client.py`)
- `get_tagged_movies` / `get_tagged_series` retrieval methods
- Tautulli protection list with manual override controls
- Manual override persistence via `/config/manual_overrides.json`
- `POST /api/overrides` endpoint
- Scheduled removal table with:
  - Date added
  - Removal date
  - Protection status
  - Urgency colour coding
- `GET /api/removal-schedule` endpoint
- Last sync summary card
- Sync log stored in `/config/sync_log.json`
- Auto-refresh after manual sync

### Infrastructure
- `SyncLog` class (thread-safe)
- `ManualOverrides` class (thread-safe)
- `SyncService` integration with logging and last-sync state
- App wiring updates (`create_app`, routes)

---

## CHG-004 — 2026-04-27 — sync_service review fixes

### Fixed
- Corrected `radarr_mode` and `sonarr_mode` values (`read_only` → `read`)
- Added missing `tautulli_mode` documentation entry

### Changed
- Simplified `protected_titles` type annotation

---

## CHG-003 — 2026-04-27 — Redact sensitive fields in settings UI

### Security
- API key/password fields now use `type="password"` with `__REDACTED__` sentinel
- Sentinel preserves stored values unless explicitly changed
- Sensitive fields redacted in `GET /api/settings`

### Added
- Added missing `web_password` input field

---

## CHG-002 — 2026-04-27 — README review fixes

### Fixed
- Corrected "Daily sync" → "Scheduled sync"
- Removed inaccurate retention behavior claims
- Fixed Docker bind mount example
- Added missing section separator

### Added
- Added `CHANGELOG.md` to repo structure
- Expanded configuration table
- Added Trakt Client ID setup instructions

---

## CHG-001 — 2026-04-27 — Code review fixes

### Security
- Ignored `config/settings.json`
- Added `settings.json.example`
- Moved API keys to headers
- Added optional Basic Auth for web UI

### Fixed
- Removed broken `fetch_netflix_top_10` call
- Fixed incorrect `tvdbId` fallback

### Performance
- Replaced full-library scans with direct lookup calls

### Thread Safety
- Added locks to `SettingsStore` and `SyncService`
- Shared `SyncService` instance across threads

### Changed
- Replaced deprecated datetime usage
- Improved error logging in settings loader
- Removed redundant environment checks
- Cleaned unused config alias

### Added
- Country-based Trakt fetch with deduplication
- Switched to `waitress` WSGI server
- Added missing CSS class

### Documentation
- Corrected README data source (Netflix → Trakt)
- Removed unimplemented features
- Documented Basic Auth and setup steps
- Cleaned docker-compose config