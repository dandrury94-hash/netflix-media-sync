# Netflix Media Sync

A **policy-driven media sync service** that automatically adds trending content to Radarr and Sonarr, while protecting watched media using Tautulli.

Built as a Dockerized background worker with a web interface, the system supports safe dry runs, full automation, configurable retention policies, and live monitoring.

---

## Features

- Sync trending content from **Trakt** (by country) and **FlixPatrol** streaming Top 10 (per service)
- Add content to Radarr (movies) and Sonarr (series) automatically
- Protect recently watched media using Tautulli watch history
- Manual protection overrides, persisted across restarts
- Dry-run (read) mode for safe previewing before enabling
- Scheduled removal tracking with urgency indicators
- Live log feed with pause, copy, download, and clear controls
- Test connection buttons for each integration with live validation
- Status icons on Top 10 lists showing per-title Radarr/Sonarr state
- Poster art thumbnails on Top 10 panels sourced from Radarr/Sonarr image metadata — cached in `localStorage` so they appear instantly on page reload
- Optional HTTP Basic Auth
- All config and runtime data persisted in `/config`
- Docker-first deployment with a single bind mount

---

## Key Concepts

### Sync Modes

Each integration (Radarr, Sonarr, Tautulli) is independently configured:

| Mode | Behaviour |
|------|-----------|
| `disabled` | Integration is ignored entirely |
| `read` | Dry-run — shows what would happen, makes no changes |
| `enabled` | Fully active — adds titles, applies protection rules |

### Protection Model

A title is protected if either condition is true:
- It appears in Tautulli watch history within the lookback window
- It has been manually pinned via the dashboard override toggle

Protected titles are never removed from the removal schedule and are surfaced prominently on the dashboard.

### How It Works

- On each sync, enabled sources are fetched, deduplicated by title + type, and the merged list is compared against the Radarr and Sonarr libraries
- New titles are added (or logged in read mode) and tagged `netflix-sync` for retention tracking
- After every sync, titles past their retention date enter a grace period before automatic deletion (when enabled)
- Poster art is fetched from Radarr and Sonarr's image metadata (`remoteUrl` on `coverType: "poster"`) and displayed on the dashboard Top 10 panels. No additional API calls are made — posters are extracted from the same lookup response used for status checks. Results are cached in `localStorage` so posters render immediately on page reload without waiting for the API

### Top 10 Sources

Two sources are available and can be enabled independently in Settings:

| Source | Description |
|--------|-------------|
| **Trakt** | Trending movies and series from [Trakt](https://trakt.tv), optionally filtered by country code. Falls back to global trending when no countries are selected. |
| **FlixPatrol** | Streaming Top 10 lists scraped from [FlixPatrol](https://flixpatrol.com) via the vendored [streaming-scraper](https://github.com/dandrurymobile/streaming-scraper) library. Returns Top 10 Movies and TV Shows per streaming service (Netflix, Disney+, Apple TV+, etc.) for a chosen country. |

Both sources are deduplicated before sync — a title appearing in Trakt and FlixPatrol is only added once.

#### Configuring FlixPatrol

1. Tick **FlixPatrol (streaming Top 10)** in Settings → FlixPatrol
2. Select a **Country** (e.g. United Kingdom)
3. Click **Load services** to fetch the available streaming services for that country, then tick the ones you want
4. Optionally restrict each service to **Movies** only or **TV** only using the per-service type toggles
5. Set **Cache duration hours** — FlixPatrol updates daily, so 6–12 h is recommended
6. Save settings

#### If FlixPatrol scraping breaks

FlixPatrol page structure can change without notice. If the scraper stops returning results, the settings page will show a **Stale** badge and the error message *"FlixPatrol data unavailable — check streaming-scraper repo for updates"*. Check the [streaming-scraper](https://github.com/dandrurymobile/streaming-scraper) repository for selector updates, then rebuild the image.

### Top 10 Status Icons

The dashboard Top 10 panels display a live status icon and poster thumbnail per title (loaded asynchronously):

| Icon | Meaning |
|------|---------|
| ✅ | Available — file is downloaded and in the library |
| ⏳ | Pending — monitored in Radarr/Sonarr but not yet downloaded |
| ➕ | Will Add — not yet in Radarr/Sonarr, would be added on next enabled sync |
| ➖ | Disabled — integration is off, status unknown |

### Removal Schedule

All `netflix-sync` tagged titles in Radarr and Sonarr appear in the removal schedule table, showing:
- Date added (from sync log, falling back to Radarr/Sonarr metadata)
- Calculated removal date based on retention settings
- Protection status
- Days remaining, colour-coded by urgency

---

## Web Interface

Available at `http://<host>:8080` (port configurable).

### Dashboard tab

- **Integration status** — mode and health indicator for each integration
- **Last sync summary** — timestamp and per-mode counts
- **Actions** — manual sync trigger
- **Top 10 Movies / Series** — last sync results from all enabled sources with live status icons
- **Import preview** — titles added or would-be-added this sync
- **Protected titles** — Tautulli and manually overridden titles with override toggles
- **Scheduled removals** — all `netflix-sync` tagged titles with removal timeline

### Logs tab

- Live log feed polling every 3 seconds, 2000-line scrollback
- Colour-coded by level (INFO / WARNING / ERROR / DEBUG)
- Auto-scrolls to bottom unless the user has scrolled up
- Controls: Pause/Resume, Copy to clipboard, Download as `.log`, Clear

### Settings page

- Per-integration configuration (URL, API key, mode, quality profile, root folder)
- **Test Connection** button on each card — validates live connectivity and populates quality profile and root folder dropdowns from the live API
- Trakt Client ID and FlixPatrol source configuration (country, service selector, type toggles, cache duration)
- Sync interval, retention days, web port, and Basic Auth password
- Netflix Top 10 country selection (multi-select, used by Trakt source)

---

## Authentication

Set `web_password` in settings or the `WEB_PASSWORD` environment variable to enable HTTP Basic Auth. Leave empty to disable.

---

## Configuration

All settings are stored in `/config/settings.json` and can be overridden by environment variables.

### Full settings reference

| JSON key | Environment variable | Default | Description |
|----------|---------------------|---------|-------------|
| `radarr_url` | `RADARR_URL` | — | Radarr base URL (e.g. `http://radarr:7878`) |
| `radarr_api_key` | `RADARR_API_KEY` | — | Radarr API key |
| `radarr_mode` | `RADARR_MODE` | `disabled` | `disabled` / `read` / `enabled` |
| `radarr_quality_profile_id` | `RADARR_QUALITY_PROFILE_ID` | `1` | Radarr quality profile ID |
| `root_folder_movies` | `ROOT_FOLDER_MOVIES` | — | Radarr root folder path (e.g. `/movies`). Poster images are sourced from Radarr's image metadata automatically — no extra configuration required. |
| `sonarr_url` | `SONARR_URL` | — | Sonarr base URL (e.g. `http://sonarr:8989`) |
| `sonarr_api_key` | `SONARR_API_KEY` | — | Sonarr API key |
| `sonarr_mode` | `SONARR_MODE` | `disabled` | `disabled` / `read` / `enabled` |
| `sonarr_quality_profile_id` | `SONARR_QUALITY_PROFILE_ID` | `1` | Sonarr quality profile ID |
| `root_folder_series` | `ROOT_FOLDER_SERIES` | — | Sonarr root folder path (e.g. `/tv`). Poster images are sourced from Sonarr's image metadata automatically — no extra configuration required. |
| `tautulli_url` | `TAUTULLI_URL` | — | Tautulli base URL (e.g. `http://tautulli:8181`) |
| `tautulli_api_key` | `TAUTULLI_API_KEY` | — | Tautulli API key |
| `tautulli_mode` | `TAUTULLI_MODE` | `disabled` | `disabled` / `read` / `enabled` |
| `tautulli_lookback_days` | `TAUTULLI_LOOKBACK_DAYS` | `30` | Days of watch history to consider for protection |
| `trakt_client_id` | `TRAKT_CLIENT_ID` | — | Trakt API client ID — obtain from trakt.tv/oauth/applications |
| `netflix_top_countries` | `NETFLIX_TOP_COUNTRIES` | `[]` | List of country codes for Trakt Top 10 (e.g. `["us","gb"]`). Falls back to global trending if empty. |
| `sources` | — | `[]` | Active trending sources — `"trakt"` and/or `"flixpatrol"` |
| `flixpatrol_country` | — | `"United Kingdom"` | Country name for FlixPatrol Top 10 (must match a supported country) |
| `flixpatrol_services` | — | `[]` | FlixPatrol streaming services to include (e.g. `["netflix","disney_plus"]`). Empty = all services |
| `flixpatrol_service_types` | — | `{}` | Per-service type filter — e.g. `{"netflix":["movie"]}`. Missing key means both types included |
| `flixpatrol_cache_hours` | — | `6` | Hours to cache FlixPatrol results before re-fetching. FlixPatrol updates daily; 6–12 h recommended |
| `run_interval_seconds` | `RUN_INTERVAL_SECONDS` | `86400` | Seconds between automatic sync runs |
| `movie_retention_days` | `MOVIE_RETENTION_DAYS` | `30` | Retention window used to calculate removal dates for movies |
| `series_retention_days` | `SERIES_RETENTION_DAYS` | `30` | Retention window used to calculate removal dates for series |
| `web_port` | `WEB_PORT` | `8080` | Web UI port |
| `web_password` | `WEB_PASSWORD` | — | HTTP Basic Auth password. Leave empty to disable auth. |

### Initial setup

1. Copy `config/settings.json.example` to `config/settings.json`
2. Fill in your API keys, or leave empty and use the Settings page on first run
3. Use **Test Connection** in Settings to validate each integration before enabling it

---

## Docker

### docker run

```bash
docker run -d \
  --name netflix-media-sync \
  -p 8080:8080 \
  -v "$(pwd)/config:/config" \
  netflix-media-sync
```

### docker-compose

```yaml
services:
  netflix-media-sync:
    image: netflix-media-sync
    ports:
      - "8080:8080"
    volumes:
      - ./config:/config
    restart: unless-stopped
```

---

## Runtime Behaviour

- Sync runs immediately on startup, then repeats on the configured interval
- A manual sync can be triggered from the dashboard at any time
- The background worker and web server share a single `SyncService` instance with a lock — concurrent runs queue rather than overlap
- All runtime state (`sync_log.json`, `manual_overrides.json`, `app.log`) is written to `/config`

---

## Logging

| Destination | Details |
|-------------|---------|
| Container stdout | Always active via `docker logs` |
| `/config/app.log` | Rotating file, 5 MB max, 3 backups |
| Dashboard → Logs tab | Live feed, 2000-line scrollback, pauseable |

Log format: `YYYY-MM-DD HH:MM:SS [LEVEL] module: message`

---

## Limitations

- Trakt source uses trending data, not real Netflix charts
- FlixPatrol source scrapes a third-party aggregator — if FlixPatrol changes its page structure the scraper will return no results until [streaming-scraper](https://github.com/dandrurymobile/streaming-scraper) is updated and the image rebuilt
- Title matching against Radarr/Sonarr is approximate (search-based)
- Designed for single-instance deployment

---

## Planned

### Additional trending sources

The source fetch layer is already in place. `fetch_from_sources()` accepts a list of named sources, deduplicates by title + type, and feeds the merged result into the normal sync flow. Adding a new source means implementing one function and enabling it in settings — the rest of the pipeline is unchanged.

| Source | Notes |
|--------|-------|
| IMDb charts | IMDb publishes popularity charts (Top 250, Most Popular) with no official API; scraping is feasible |
| Letterboxd | Weekly popular films — no public API but the page is scrapable |
| TMDB trending | Official REST API, free tier, returns trending movies/TV by day or week — low friction to add |
| Plex Discover | Trending on Plex — relevant for self-hosters already using Plex/Tautulli |

Each source would follow the same pattern: a module that returns `list[{"title", "type", "source"}]`, registered in `fetch_from_sources()`, and exposed via a checkbox in Settings once it is working.

---

## Project Structure

```
app/
├── main.py               # Entry point, WSGI server, background worker
├── web.py                # Flask routes and API endpoints
├── sync_service.py       # Core sync logic
├── sync_log.py           # Thread-safe sync result persistence
├── manual_overrides.py   # Thread-safe manual protection persistence
├── settings.py           # Thread-safe settings store
├── config.py             # Constants and path definitions
├── netflix_fetcher.py    # Multi-source fetch orchestration (Trakt + FlixPatrol)
├── radarr_client.py      # Radarr API client
├── sonarr_client.py      # Sonarr API client
├── tautulli_client.py    # Tautulli API client
├── scraper/              # Vendored streaming-scraper library
│   ├── core/             # Aggregator and data models
│   └── sources/          # Per-service scrapers (FlixPatrol)
├── templates/
│   ├── base.html         # Shared layout, topbar, nav
│   ├── index.html        # Dashboard (Dashboard / Logs tabs)
│   └── settings.html     # Settings page
└── static/
    ├── script.js         # Tab switching, sync, overrides, logs, status icons
    ├── style.css         # All UI styles
    └── icon.svg          # App icon (favicon + topbar)
config/
├── settings.json         # Runtime configuration (gitignored)
├── settings.json.example # Checked-in template with empty values
├── sync_log.json         # Last sync results and title history (runtime)
├── manual_overrides.json # Persisted manual protection overrides (runtime)
└── app.log               # Rotating application log (runtime)
```

---

## License

Add one if distributing publicly.
