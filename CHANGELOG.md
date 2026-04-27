# Changelog

All changes to this project are recorded here with a unique reference, date, and description.

---

## CHG-007 — 2026-04-27 — Test connection buttons

### Additions
- Test connection button added to each integration card in Settings (Radarr, Sonarr, Tautulli) (`app/templates/settings.html`)
- `POST /api/test/radarr` and `POST /api/test/sonarr` — verify connectivity using the URL and API key submitted from the form; on success return available quality profiles (`/api/v3/qualityprofile`) and root folders (`/api/v3/rootfolder`) (`app/web.py`)
- `POST /api/test/tautulli` — calls `/api/v2?cmd=get_server_info`; on success returns the Plex server name (`app/web.py`)
- After a successful Radarr / Sonarr test, the quality profile ID number input and root folder text input are replaced in-place with populated dropdowns; form submission continues to work because the dropdowns carry the same `name` attributes (`app/static/script.js`)
- `✅ Connected` shown on success; `❌ <reason>` shown on failure with specific messages for connection refused, timeout, 401/403, and other HTTP errors (`app/static/script.js`, `app/static/style.css`)
- Sentinel `__REDACTED__` is resolved to the stored key server-side so Test Connection works even when the API key field has not been re-entered (`app/web.py`)

### Infrastructure
- `import requests as _requests` added to `web.py`; shared helpers `_resolve_test_key`, `_exc_msg`, and `_test_arr` avoid duplication across the three endpoints (`app/web.py`)

---

## CHG-006 — 2026-04-27 — Live log feed

### Infrastructure
- `RotatingFileHandler` added to the root logger at startup; writes to `/config/app.log`, max 5 MB per file, 3 backups; all existing `logging` calls are captured automatically without changes to any other module (`app/main.py`)
- Both the file handler and the existing stdout handler now share the same `datefmt="%Y-%m-%d %H:%M:%S"` format: `YYYY-MM-DD HH:MM:SS [LEVEL] logger_name: message` (`app/main.py`)
- `LOG_PATH` constant added (`app/config.py`); defaults to `/config/app.log`, overridable via `LOG_PATH` env var

### Additions
- `GET /api/logs` — returns the last 100 lines of `/config/app.log` as `{"lines": [...]}` (`app/web.py`)
- `POST /api/logs/clear` — truncates `/config/app.log` to zero bytes while keeping the file in place (`app/web.py`)
- `_tail_file(path, n)` helper reads last N lines of any file, returns `[]` when the file does not yet exist (`app/web.py`)
- Live log panel on dashboard: polls `/api/logs` every 3 seconds, colour-coded by level (green INFO / yellow WARNING / red ERROR / grey DEBUG), auto-scrolls to bottom unless user has scrolled up (`app/templates/index.html`, `app/static/script.js`, `app/static/style.css`)
- Pause / Resume button stops polling and updates a Live / Paused badge; Download button exports current lines as a dated `.log` file; Clear button truncates the file via `/api/logs/clear` and empties the panel (`app/static/script.js`, `app/templates/index.html`)
- Log output uses monospace font, selectable text, `pre-wrap` line wrapping — contents can be selected and copied directly (`app/static/style.css`)

---

## CHG-005 — 2026-04-27 — Dashboard features

### Additions
- Integration status panel on dashboard showing Radarr, Sonarr, and Tautulli mode with colour-coded dot indicator and badge (🔴 Disabled / 🟡 Read / 🟢 Enabled) (`app/templates/index.html`, `app/static/style.css`)
- Trakt Top 10 movies and Top 10 series panels populated from last sync result (`app/templates/index.html`)
- Import preview panel: shows added titles (enabled mode) or would-add titles (read mode) and already-in-library titles per Radarr and Sonarr; hidden when both integrations are disabled (`app/templates/index.html`)
- `netflix-sync` tag applied to every movie and series added in enabled mode; tag is created automatically if it does not exist; falls back to no tag rather than failing the add (`app/radarr_client.py`, `app/sonarr_client.py`)
- `get_tagged_movies` / `get_tagged_series` methods to retrieve all Radarr/Sonarr titles carrying the `netflix-sync` tag (`app/radarr_client.py`, `app/sonarr_client.py`)
- Tautulli protection list on dashboard with manual override checkboxes; checking a title pins it permanently; unchecking removes the override (`app/templates/index.html`, `app/static/script.js`)
- Manual overrides persisted to `/config/manual_overrides.json` via new `ManualOverrides` class (`app/manual_overrides.py`, `app/config.py`)
- `POST /api/overrides` endpoint to set or clear a manual override (`app/web.py`)
- Scheduled removal table loaded via AJAX on page load; shows all `netflix-sync` tagged titles with date added, scheduled removal date, protected status, and days remaining; rows colour-coded by urgency (`app/templates/index.html`, `app/static/script.js`, `app/web.py`)
- `GET /api/removal-schedule` endpoint; queries Radarr and Sonarr live, resolves date-added from sync log, computes removal date from retention settings, and checks combined Tautulli + manual protection (`app/web.py`)
- Last sync summary card on dashboard: timestamp and per-mode counts for added / would-add movies and series, and protected title count (`app/templates/index.html`)
- Sync log written to `/config/sync_log.json` on every successful add and after every sync run; records title, type, date added, source, and full last-sync result including top 10 lists (`app/sync_log.py`, `app/sync_service.py`, `app/config.py`)
- After a manual sync trigger the page reloads automatically so all dashboard panels reflect fresh data (`app/static/script.js`)

### Infrastructure
- New `SyncLog` class with thread-safe read/write to `/config/sync_log.json` (`app/sync_log.py`)
- New `ManualOverrides` class with thread-safe read/write to `/config/manual_overrides.json` (`app/manual_overrides.py`)
- `SyncService` now accepts a `SyncLog` instance; logs each add and saves last-sync state including `top_movies` and `top_series` (`app/sync_service.py`)
- `create_app` now accepts `SyncLog` and `ManualOverrides`; dashboard route passes last-sync data and protection sets to the template (`app/web.py`, `app/main.py`)

---

## CHG-004 — 2026-04-27 — sync_service review fixes

### Correctness
- Fixed `radarr_mode` and `sonarr_mode` documented values from `read_only` to `read` to match the actual values used in code and the settings template (`README.md`)
- Added missing `tautulli_mode` row to the configuration settings table (`README.md`)

### Code quality
- Narrowed `protected_titles` type annotation from `list[str] | set[str]` to `list[str]` by wrapping the Tautulli result in `list()` (`app/sync_service.py`)

---

## CHG-003 — 2026-04-27 — Redact sensitive fields in the settings UI

### Security
- API key and password fields now use `type="password"` and render a `__REDACTED__` sentinel instead of the real value when a key is already stored (`app/templates/settings.html`)
- On save, if a sensitive field is submitted with the sentinel value, the existing stored value is preserved rather than overwritten; submitting an empty string still clears the key (`app/web.py`)
- `GET /api/settings` now redacts all sensitive fields in the JSON response (`app/web.py`)

### Additions
- Added missing `web_password` input to the settings form (`app/templates/settings.html`)

---

## CHG-002 — 2026-04-27 — README review fixes

### Fixes
- Changed "Daily sync" to "Scheduled sync" in the Features section; the interval is configurable, not fixed at 24 hours
- Removed "retention windows" from the web UI description; retention settings have no runtime effect on media
- Replaced `./config` bind-mount syntax in `docker run` example with `$(pwd)/config` for compatibility with Docker versions before 23.0
- Added missing `---` section separator before the Customization subsection

### Additions
- Added `CHANGELOG.md` to the repository structure tree
- Expanded configuration table to list all settings with JSON key names, environment variable names, and descriptions; previously only a partial subset of ENV_VAR-named keys was shown
- Added note on obtaining a Trakt Client ID from trakt.tv/oauth/applications, which is required for the sync to function

---

## CHG-001 — 2026-04-27 — Code review fixes

### Security
- Added `config/settings.json` to `.gitignore` to prevent credentials from being committed
- Created `config/settings.json.example` with empty placeholder values as the checked-in template
- Moved Radarr and Sonarr API keys from URL query parameters to `X-Api-Key` request headers (`app/radarr_client.py`, `app/sonarr_client.py`)
- Added optional HTTP Basic Auth to the web UI via a `web_password` setting; unauthenticated requests receive a 401 when a password is configured (`app/web.py`, `app/config.py`)

### Bug fixes
- Removed a broken `else` branch in `SyncService._run` that called the non-existent function `fetch_netflix_top_10`, which would have raised `NameError` whenever `netflix_top_countries` was empty (`app/sync_service.py`)
- Fixed `tvdbId` fallback in `SonarrClient.add_series` that incorrectly fell back to `details.get("id")` (a Sonarr internal ID, not a TVDB ID) (`app/sonarr_client.py`)

### Performance
- Replaced full-library fetch + linear scan in `RadarrClient` and `SonarrClient` existence checks with a single lookup call; a non-zero `id` in the result indicates the title is already present (`app/radarr_client.py`, `app/sonarr_client.py`)

### Thread safety
- Added `threading.RLock` to `SettingsStore` wrapping all dict reads and file writes (`app/settings.py`)
- Added `threading.Lock` to `SyncService.run_once` so concurrent calls from the background worker and the web `/api/sync` endpoint queue rather than run simultaneously (`app/sync_service.py`)
- Background worker now receives the shared `SyncService` instance instead of constructing its own, ensuring both threads share the same lock (`app/main.py`)

### Correctness
- Replaced deprecated `datetime.datetime.utcnow()` and `datetime.datetime.utcfromtimestamp()` with timezone-aware equivalents (`app/tautulli_client.py`)
- `SettingsStore._load_from_file` now logs a warning instead of silently swallowing JSON parse and IO errors (`app/settings.py`)
- Removed redundant double `os.getenv` check in `SettingsStore._apply_environment_overrides` (`app/settings.py`)
- Removed unused `CONFIG_PATH` alias; `app/settings.py` now imports `SETTINGS_PATH` directly (`app/config.py`)

### Additions
- `fetch_netflix_top_10_for_countries` now fetches Trakt trending per country code, passing `?country=<code>` to the API and deduplicating results across multiple codes (`app/netflix_fetcher.py`)
- Replaced Flask development server with `waitress` WSGI server (`app/main.py`, `requirements.txt`)
- Added missing `.field-help` CSS class referenced in `settings.html` (`app/static/style.css`)

### Documentation
- Updated `README.md`: corrected data source from "Netflix" to "Trakt", removed unimplemented deletion feature references, documented `WEB_PASSWORD` / Basic Auth, added `settings.json.example` setup step
- Removed deprecated `version: "3.9"` key from `docker-compose.yml`
