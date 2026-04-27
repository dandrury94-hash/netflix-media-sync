# Changelog

All changes to this project are recorded here with a unique reference, date, and description.

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