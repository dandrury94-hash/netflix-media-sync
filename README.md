# Netflix Top 10 Sync

A Dockerized service with a built-in web interface for configuring:

- Netflix Top 10 sync settings
- Radarr integration
- Sonarr integration
- Tautulli protection rules
- retention and cleanup timing

> **Important:** Netflix does not provide a public Top 10 API. This service uses a best-effort extraction from the public Netflix Top 10 page. Page structure or access rules may change over time.

---

## Contents

- [Features](#features)
- [How it works](#how-it-works)
- [Repository structure](#repository-structure)
- [Web interface](#web-interface)
- [Configuration settings](#configuration-settings)
- [Docker deployment](#docker-deployment)
- [Docker Compose deployment](#docker-compose-deployment)
- [Unraid deployment](#unraid-deployment)
- [Usage and runtime behavior](#usage-and-runtime-behavior)
- [Troubleshooting](#troubleshooting)
- [Notes and caveats](#notes-and-caveats)

---

## Features

- Daily sync from Netflix Top 10 movies and series
- Adds movies to Radarr and series to Sonarr
- Protects partially or recently watched media using Tautulli
- Built-in web UI for settings, manual sync, and retention configuration
- Config persistence through a mounted JSON settings file

---

## How it works

1. The container fetches Netflix Top 10 content.
2. It determines the top movies and top series.
3. It adds new titles to Radarr and Sonarr via API.
4. It reads Tautulli watch history and active sessions to build a protected media list.
5. When enabled, it can use protected media status as a guardrail before cleanup.

---

## Repository structure

```text
netflix-media-sync/
├── Dockerfile
├── README.md
├── docker-compose.yml
├── entrypoint.sh
├── requirements.txt
└── app/
    ├── config.py
    ├── main.py
    ├── netflix_fetcher.py
    ├── radarr_client.py
    ├── sonarr_client.py
    ├── settings.py
    ├── sync_service.py
    ├── tautulli_client.py
    ├── web.py
    ├── static/
    │   ├── script.js
    │   └── style.css
    └── templates/
        ├── base.html
        ├── index.html
        └── settings.html
```

---

## Web interface

The container exposes a web UI on port `8080` by default.

From the web UI you can:

- configure Radarr, Sonarr, and Tautulli integration settings
- adjust sync interval and retention windows
- enable or disable old-media cleanup
- trigger a manual sync immediately

Open the interface at `http://<host>:8080` after the container is running.

---

## Configuration settings

These values are managed from the web UI Settings page and persisted to `/config/settings.json`.

| Setting key | Description |
| --- | --- |
| `TAUTULLI_URL` | Base Tautulli URL, e.g. `http://tautulli:8181` |
| `TAUTULLI_API_KEY` | Tautulli API key |
| `ROOT_FOLDER_MOVIES` | Root folder path in Radarr |
| `ROOT_FOLDER_SERIES` | Root folder path in Sonarr |
| `RADARR_QUALITY_PROFILE_ID` | Radarr quality profile ID |
| `SONARR_QUALITY_PROFILE_ID` | Sonarr quality profile ID |
| `NETFLIX_TOP_COUNTRIES` | List of region codes used for Netflix Top 10 sync (e.g. `us`, `gb`) |
| `RUN_INTERVAL_SECONDS` | Seconds between sync runs (default `86400`) |
| `DELETE_OLD_MEDIA` | `true` to enable deletion candidate evaluation (default `false`) |
| `TAUTULLI_LOOKBACK_DAYS` | Protect media watched within this many days (default `30`) |
| `WEB_PORT` | Web UI port (default `8080`) |

---

## Docker deployment

### Build the image

```bash
cd netflix-media-sync
docker build -t netflix-media-sync .
```

### Run the container

```bash
docker run -d \
  --name netflix-media-sync \
  -p 8080:8080 \
  -v ./config:/config \
  netflix-media-sync
```

### Windows local app test deployment

If you want to test with Radarr, Sonarr, and Tautulli running locally on Windows, use Docker Desktop and the `host.docker.internal` hostname.

1. Build the image from the repository root:

```powershell
cd netflix-media-sync
docker build -t netflix-media-sync .
```

2. Run the container with the config mount:

```powershell
docker run -d --name netflix-media-sync -p 8080:8080 -v ${PWD}\config:/config netflix-media-sync
```

3. Open `http://localhost:8080` in your browser.
4. In the Settings page, enter the local app URLs using `host.docker.internal`:
   - Radarr: `http://host.docker.internal:7878`
   - Sonarr: `http://host.docker.internal:8989`
   - Tautulli: `http://host.docker.internal:8181`
5. Enter the API keys for each service and save settings.

> Note: `host.docker.internal` resolves from the container back to the Windows host. If your Windows apps are listening on other ports, update the URLs accordingly.

### Notes

- Replace the example URLs with the actual service URLs from your network.
- Use container names or hostnames consistent with your Docker network.
- If Radarr, Sonarr, and Tautulli are in the same network, use their service names.

---

## Docker Compose deployment

The provided `docker-compose.yml` exposes the web UI and mounts the configuration directory. All integration settings are configured from the Settings page once the container starts.

```yaml
version: "3.9"
services:
  netflix-sync:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./config:/config
```

To launch:

```bash
docker-compose up -d
```

---

## Unraid deployment

Unraid can run this container through the Docker tab.

### Option 1: Use Docker Compose (recommended)

1. Copy the repository to an Unraid share or local folder.
2. In Unraid, enable the `docker-compose` plugin if available.
3. Start the stack with `docker-compose up -d` from the project folder.

### Option 2: Create a custom Docker container in Unraid

1. Open the Unraid web UI and go to `Docker` > `Add Container`.
2. Set the image name to `netflix-media-sync` or build from the local `Dockerfile`.
3. Configure the container and volume mappings.
   - Mount `./config` to `/config`.
   - Expose port `8080` for the web UI.
   - Configure Radarr, Sonarr, and Tautulli settings from the Settings page after startup.
4. Configure the network type to `bridge` or `custom` if you have a Docker network for Radarr/Sonarr/Tautulli.
5. Start the container.

### Recommended Unraid notes

- Use `host` networking only if you understand the implications for port exposure.
- Set `Restart Policy` to `Unless stopped`.
- Match config volume mapping and root folder paths to your Radarr and Sonarr configuration.

---

## Usage and runtime behavior

- The service starts and immediately runs one sync cycle.
- It waits `RUN_INTERVAL_SECONDS` seconds between cycles.
- By default, the interval is `86400` seconds (24 hours).
- If `DELETE_OLD_MEDIA=false`, the service gathers protected titles but does not remove media.
- If `DELETE_OLD_MEDIA=true`, the service evaluates protected media before any cleanup actions.
- The web UI allows manual sync and live settings configuration.

## Customization

- To change the interval, update the setting in the UI or `/config/settings.json`.
- To protect a longer watch history window, update the setting in the UI or `/config/settings.json`.
- To update retention rules, use `movie_retention_days` and `series_retention_days` in the web UI.

---

## Troubleshooting

### Common issues

- `Connection refused` from Radarr/Sonarr/Tautulli:
  - Check the URLs and ports.
  - Confirm the container can reach those hosts.
  - Use Docker networking or service names if services are in the same stack.

- Netflix fetch returns empty lists:
  - Netflix may have changed the Top 10 page structure.
  - Inspect or update `app/netflix_fetcher.py` if extraction no longer works.

- Titles are not being added:
  - Verify API keys.
  - Confirm quality profile IDs and root folder paths exist.
  - Review container logs for warnings and errors.

### Logging

Logs are written to standard output. Use `docker logs netflix-media-sync` or `docker-compose logs netflix-sync` to inspect.

---

## Notes and caveats

- The service is an automation helper, not a production-grade Netflix metadata source.
- Netflix Top 10 is scraped from a public page; reliability may vary.
- Deletion is intentionally conservative; enable `DELETE_OLD_MEDIA` only once you have verified behavior.
- Tautulli protection relies on similar title matching across services.

---

## License

This repository is provided without a specific license. Add a license file if you intend to publish it publicly.
