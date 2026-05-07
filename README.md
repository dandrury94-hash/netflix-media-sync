# Streamarr

A **policy-driven media sync service** that automatically adds trending content to Radarr and Sonarr, tracks retention, and manages scheduled deletions. Built as a Dockerized background worker with a web interface.

---

## Features

- Sync trending content from **Trakt** (by country) and **FlixPatrol** streaming Top 10 (per service)
- Add content to Radarr (movies) and Sonarr (series) automatically
- Scheduled removal tracking with urgency indicators and colour-coded days remaining
- Manual protection via the dashboard — protects a title from automatic deletion indefinitely
- Tautulli integration for retention clock — watched titles have their removal date pushed forward
- 7-day pre-deletion Pushover warning when a title enters the deletion window
- Weekly Saturday Pushover preview of titles due for removal in the next 7 days
- Addition history — titles added in the last 7 days with source attribution
- Removal history — titles automatically deleted, kept for 180 days
- Live log feed with pause, copy, download, and clear controls
- Test connection buttons for each integration with live validation
- Status icons on Top 10 lists showing per-title Radarr/Sonarr state
- Poster art thumbnails on Top 10 panels sourced from Radarr/Sonarr image metadata — cached in `localStorage`
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
| `enabled` | Fully active — adds titles, applies retention rules |

### Protection Model

A title is protected from deletion **only** if it carries the `streamarr-state-protected` tag in Radarr or Sonarr. This tag is applied and removed immediately when the dashboard toggle is used — it is not deferred to the next sync.

Tautulli is **not** a protection source. It is a retention signal: when a title appears in Tautulli watch history, its removal anchor date is reset to the watch date, pushing its retention window forward. A title watched today with a 30-day retention policy will not be eligible for deletion for another 30 days.

`protection_source` is always `"manual"` or `null` — never `"tautulli"`.

### Retention and Deletion

- Each managed title has a removal date calculated as `anchor_date + retention_days`
- `anchor_date` is the later of: the date the title was added (from SyncLog) or the most recent Tautulli watch date
- When `days_remaining <= 7` and the title has not been warned yet, a Pushover notification is sent listing all titles entering the window
- When `days_remaining <= 0` and deletion is enabled, the title is removed from Radarr/Sonarr along with its files
- Deletion only runs on items carrying the `streamarr` tag — items without it are ignored entirely

### How It Works

1. On each sync, enabled sources are fetched, deduplicated by title + type, and the merged list is compared against the Radarr and Sonarr libraries
2. New titles are added (or logged in read mode) and tagged `streamarr`, `streamarr-src-{source}`, and `streamarr-cat-movie` / `streamarr-cat-tv`
3. Tautulli watch history is fetched and stored as `last_watched` dates per title — used to reset retention anchors, not for protection
4. After every sync, `run_deletions()` evaluates all `streamarr`-tagged titles and either sends a warning, deletes, or skips based on days remaining and protection status

### Top 10 Sources

Two sources are available and can be enabled independently in Settings:

| Source | Description |
|--------|-------------|
| **Trakt** | Trending movies and series from [Trakt](https://trakt.tv), optionally filtered by country code. Falls back to global trending when no countries are selected. |
| **FlixPatrol** | Streaming Top 10 lists scraped from [FlixPatrol](https://flixpatrol.com) via the vendored [streaming-scraper](https://github.com/dandrurymobile/streaming-scraper) library. Returns Top 10 Movies and TV Shows per streaming service (Netflix, Disney+, Apple TV+, etc.) for a chosen country. |

Both sources are deduplicated before sync — a title appearing in both is only added once, and its `sources` list records both (e.g. `["trakt", "flixpatrol"]`).

#### Configuring FlixPatrol

1. Tick **FlixPatrol (streaming Top 10)** in Settings → FlixPatrol
2. Select a **Country** (e.g. United Kingdom)
3. Click **Load services** to fetch available streaming services for that country, then tick the ones you want
4. Optionally restrict each service to **Movies** only or **TV** only using the per-service type toggles
5. Set **Cache duration hours** — FlixPatrol updates daily, so 6–12 h is recommended
6. Save settings

#### If FlixPatrol scraping breaks

FlixPatrol page structure can change without notice. If the scraper stops returning results, the settings page will show a **Stale** badge and the error *"FlixPatrol data unavailable — check streaming-scraper repo for updates"*. Check the [streaming-scraper](https://github.com/dandrurymobile/streaming-scraper) repository for selector updates, then rebuild the image.

### Top 10 Status Icons

The dashboard Top 10 panels display a live status icon and poster thumbnail per title:

| Icon | Meaning |
|------|---------|
| ✅ | Available — file is downloaded and in the library |
| ⏳ | Pending — monitored in Radarr/Sonarr but not yet downloaded |
| ➕ | Will Add — not yet in Radarr/Sonarr, would be added on next enabled sync |
| ➖ | Disabled — integration is off, status unknown |

### Removal Schedule

All `streamarr`-tagged titles appear in the removal schedule table, showing:
- Date added (from sync log, falling back to Radarr/Sonarr metadata)
- Calculated removal date based on retention settings and last watched date
- Protection status and source
- Days remaining, colour-coded by urgency

---

## Web Interface

Available at `http://<host>:8080` (port configurable).

### Dashboard tab

- **Status & Actions** — integration mode indicators, last sync summary, manual sync trigger
- **Top 10** — last sync results per source with live status icons and poster thumbnails
- **Scheduled Removals** — all `streamarr`-tagged titles with removal timeline and status

### History tab

- **Recently Added** — titles added to Radarr/Sonarr by this service in the last 7 days, with source attribution (e.g. Trakt, FlixPatrol, Trakt + FlixPatrol)
- **Removal History** — titles automatically deleted, records kept for 180 days

### Protection tab

- **Protection Manager** — all `streamarr`-tagged titles; toggle protection on/off per title
- Protected titles carry the `streamarr-state-protected` tag in Radarr/Sonarr — the tag is applied immediately on toggle, not deferred to the next sync

### Logs tab

- Live log feed polling every 3 seconds, 2000-line scrollback
- Colour-coded by level (INFO / WARNING / ERROR / DEBUG)
- Auto-scrolls to bottom unless the user has scrolled up
- Controls: Pause/Resume, Copy to clipboard, Download as `.log`, Clear

### Settings page

- Per-integration configuration (URL, API key, mode, quality profile, root folder)
- **Test Connection** button on each card — validates live connectivity and populates quality profile and root folder dropdowns from the live API
- Trakt Client ID and country selection; FlixPatrol source configuration (country, service selector, type toggles, cache duration)
- Sync interval, retention days (movies and series independently), deletion toggle
- Pushover notification configuration (user key, API token, test button)
- Web port and Basic Auth password

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
| `root_folder_movies` | `ROOT_FOLDER_MOVIES` | — | Radarr root folder path (e.g. `/movies`) |
| `sonarr_url` | `SONARR_URL` | — | Sonarr base URL (e.g. `http://sonarr:8989`) |
| `sonarr_api_key` | `SONARR_API_KEY` | — | Sonarr API key |
| `sonarr_mode` | `SONARR_MODE` | `disabled` | `disabled` / `read` / `enabled` |
| `sonarr_quality_profile_id` | `SONARR_QUALITY_PROFILE_ID` | `1` | Sonarr quality profile ID |
| `root_folder_series` | `ROOT_FOLDER_SERIES` | — | Sonarr root folder path (e.g. `/tv`) |
| `tautulli_url` | `TAUTULLI_URL` | — | Tautulli base URL (e.g. `http://tautulli:8181`) |
| `tautulli_api_key` | `TAUTULLI_API_KEY` | — | Tautulli API key |
| `tautulli_mode` | `TAUTULLI_MODE` | `disabled` | `disabled` / `read` / `enabled` |
| `tautulli_lookback_days` | `TAUTULLI_LOOKBACK_DAYS` | `30` | Days of watch history to fetch for retention anchor reset |
| `trakt_client_id` | `TRAKT_CLIENT_ID` | — | Trakt API client ID — obtain from trakt.tv/oauth/applications |
| `netflix_top_countries` | — | `[]` | Country codes for Trakt Top 10 (e.g. `["us","gb"]`). Falls back to global trending if empty |
| `sources` | — | `["trakt"]` | Active trending sources — `"trakt"` and/or `"flixpatrol"` |
| `flixpatrol_country` | — | `"United Kingdom"` | Country name for FlixPatrol Top 10 |
| `flixpatrol_services` | — | `[]` | FlixPatrol streaming services to include (e.g. `["netflix","disney_plus"]`). Empty = all |
| `flixpatrol_service_types` | — | `{}` | Per-service type filter — e.g. `{"netflix":["movie"]}`. Missing key = both types |
| `flixpatrol_cache_hours` | — | `6` | Hours to cache FlixPatrol results. 6–12 h recommended |
| `run_interval_seconds` | `RUN_INTERVAL_SECONDS` | `86400` | Seconds between automatic sync runs |
| `movie_retention_days` | — | `30` | Retention window for movies |
| `series_retention_days` | — | `30` | Retention window for series |
| `deletion_enabled` | `DELETION_ENABLED` | `false` | Enable automatic deletion of titles past their retention date |
| `pushover_enabled` | — | `false` | Enable Pushover notifications |
| `pushover_user_key` | `PUSHOVER_USER_KEY` | — | Pushover user key |
| `pushover_api_token` | `PUSHOVER_API_TOKEN` | — | Pushover application API token |
| `web_port` | `WEB_PORT` | `8080` | Web UI port |
| `web_password` | `WEB_PASSWORD` | — | HTTP Basic Auth password. Leave empty to disable |

---

## Docker

### docker run

```bash
docker run -d \
  --name streamarr \
  -p 8080:8080 \
  -v "$(pwd)/config:/config" \
  streamarr
```

### docker-compose

```yaml
services:
  streamarr:
    image: streamarr
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
- A weekly preview notification fires every Saturday at 05:00 listing titles due for removal in the next 7 days (requires Pushover enabled)
- Pre-deletion warnings are sent once per title when it enters the 7-day window; the notification is not repeated on subsequent syncs

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
- Title matching against Radarr/Sonarr is search-based — unusual titles or regional naming differences may fail to match
- Designed for single-instance deployment

---

## Planned

### Additional trending sources

The source fetch layer is already in place. `fetch_from_sources()` accepts a list of named sources, deduplicates by title + type, and feeds the merged result into the normal sync flow. Adding a new source means implementing one function and enabling it in settings.

| Source | Notes |
|--------|-------|
| IMDb charts | IMDb publishes popularity charts (Top 250, Most Popular) with no official API; scraping is feasible |
| Letterboxd | Weekly popular films — no public API but the page is scrapable |
| TMDB trending | Official REST API, free tier, returns trending movies/TV by day or week |
| Plex Discover | Trending on Plex — relevant for self-hosters already using Plex/Tautulli |

---

## Project Structure

```
app/
├── main.py               # Entry point, WSGI server, background worker threads
├── web.py                # Flask routes and API endpoints
├── sync_service.py       # Core sync and deletion logic
├── sync_log.py           # Thread-safe sync result and addition history persistence
├── media_state.py        # In-memory media state builder (protection, retention, reason)
├── removal_history.py    # Thread-safe removal history persistence
├── settings.py           # Thread-safe settings store
├── config.py             # Constants and path definitions
├── tags.py               # Tag name constants and helper functions
├── netflix_fetcher.py    # Multi-source fetch orchestration (Trakt + FlixPatrol)
├── radarr_client.py      # Radarr API client
├── sonarr_client.py      # Sonarr API client
├── tautulli_client.py    # Tautulli API client
├── pushover_client.py    # Pushover notification client
├── scraper/              # Vendored streaming-scraper library
│   ├── core/             # Aggregator and data models
│   └── sources/          # Per-service scrapers (FlixPatrol)
├── templates/
│   ├── base.html         # Shared layout, topbar, nav
│   ├── index.html        # Dashboard (Dashboard / History / Protection / Logs tabs)
│   └── settings.html     # Settings page
└── static/
    ├── script.js         # Tab switching, sync, protection toggles, logs, status icons
    ├── style.css         # All UI styles
    └── icon.svg          # App icon (favicon + topbar)
config/
├── settings.json         # Runtime configuration (gitignored)
├── settings.json.example # Checked-in template with empty values
├── sync_log.json         # Sync results, addition history, last_watched, pre_deletion_notified (runtime)
├── removal_history.json  # Automatic deletion records, 180-day rolling window (runtime)
└── app.log               # Rotating application log (runtime)
```

---

## License

Add one if distributing publicly.
