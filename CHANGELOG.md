# Changelog

All changes to this project are recorded here with a unique reference, date, and description.

---

## CHG-001 — 2026-04-27 — Code review fixes

**Security**
- Added `config/settings.json` to `.gitignore` to prevent credentials from being committed
- Created `config/settings.json.example` with empty placeholder values as the checked-in template
- Moved Radarr and Sonarr API keys from URL query parameters to `X-Api-Key` request headers (`app/radarr_client.py`, `app/sonarr_client.py`)
- Added optional HTTP Basic Auth to the web UI via a `web_password` setting; unauthenticated requests receive a 401 when a password is configured (`app/web.py`, `app/config.py`)

**Bug fixes**
- Removed a broken `else` branch in `SyncService._run` that called the non-existent function `fetch_netflix_top_10`, which would have raised `NameError` whenever `netflix_top_countries` was empty (`app/sync_service.py`)
- Fixed `tvdbId` fallback in `SonarrClient.add_series` that incorrectly fell back to `details.get("id")` (a Sonarr internal ID, not a TVDB ID) (`app/sonarr_client.py`)

**Performance**
- Replaced full-library fetch + linear scan in `RadarrClient` and `SonarrClient` existence checks with a single lookup call; a non-zero `id` in the result indicates the title is already present (`app/radarr_client.py`, `app/sonarr_client.py`)

**Thread safety**
- Added `threading.RLock` to `SettingsStore` wrapping all dict reads and file writes (`app/settings.py`)
- Added `threading.Lock` to `SyncService.run_once` so concurrent calls from the background worker and the web `/api/sync` endpoint queue rather than run simultaneously (`app/sync_service.py`)
- Background worker now receives the shared `SyncService` instance instead of constructing its own, ensuring both threads share the same lock (`app/main.py`)

**Correctness**
- Replaced deprecated `datetime.datetime.utcnow()` and `datetime.datetime.utcfromtimestamp()` with timezone-aware equivalents (`app/tautulli_client.py`)
- `SettingsStore._load_from_file` now logs a warning instead of silently swallowing JSON parse and IO errors (`app/settings.py`)
- Removed redundant double `os.getenv` check in `SettingsStore._apply_environment_overrides` (`app/settings.py`)
- Removed unused `CONFIG_PATH` alias; `app/settings.py` now imports `SETTINGS_PATH` directly (`app/config.py`)

**Country filtering**
- `fetch_netflix_top_10_for_countries` now fetches Trakt trending per country code, passing `?country=<code>` to the API and deduplicating results across multiple codes (`app/netflix_fetcher.py`)

**Infrastructure**
- Replaced Flask development server with `waitress` WSGI server (`app/main.py`, `requirements.txt`)
- Removed deprecated `version: "3.9"` key from `docker-compose.yml`

**UI / styles**
- Added missing `.field-help` CSS class referenced in `settings.html` (`app/static/style.css`)

**Documentation**
- Updated `README.md`: corrected data source from "Netflix" to "Trakt", removed unimplemented deletion feature references, documented `WEB_PASSWORD` / Basic Auth, added `settings.json.example` setup step
