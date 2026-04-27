# Netflix Media Sync

A Dockerized service with a built-in web interface for configuring:

- Trending content sync via the [Trakt](https://trakt.tv) API
- Radarr integration
- Sonarr integration
- Tautulli watch-history protection rules

> **Data source:** Content is fetched from the Trakt trending API, not directly from Netflix. The country selector passes a country code to Trakt — whether Trakt applies regional filtering depends on their API behaviour at the time.

> **Credentials:** Copy `config/settings.json.example` to `config/settings.json` and fill in your values. The `config/settings.json` file is excluded from version control via `.gitignore` — never commit it.

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

- Daily sync from Trakt trending movies and series (with optional country filter)
- Adds movies to Radarr and series to Sonarr
- Protects partially or recently watched media using Tautulli
- Built-in web UI for settings and manual sync
- Optional HTTP Basic Auth to protect the web UI
- Config persistence through a mounted JSON settings file

---

## How it works

1. The container fetches trending content from the Trakt API.
2. It determines the top movies and top series (up to 10 each).
3. It adds new titles to Radarr and Sonarr via their APIs.
4. It reads Tautulli watch history and active sessions to build a protected media list.
5. Tautulli-protected titles are reported in logs; no automatic deletion is performed.

---

## Repository structure

```text
netflix-media-sync/
├── Dockerfile
├── README.md
├── docker-compose.yml
├── entrypoint.sh
├── requirements.txt
├── config/
│   └── settings.json.example
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
- trigger a manual sync immediately

Open the interface at `http://<host>:8080` after the container is running.

### Protecting the web UI

Set `web_password` in `settings.json` (or the `WEB_PASSWORD` environment variable) to enable HTTP Basic Auth. Leave it empty to disable auth (suitable for private networks). The username field is ignored — only the password is checked.

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
| `RUN_INTERVAL_SECONDS` | Seconds between sync runs (default `86400`) |
| `TAUTULLI_LOOKBACK_DAYS` | Protect media watched within this many days (default `30`) |
| `WEB_PORT` | Web UI port (default `8080`) |
| `WEB_PASSWORD` | Password for HTTP Basic Auth on the web UI (empty = no auth) |

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

2. Copy the example settings file and fill in your values:

```powershell
Copy-Item config\settings.json.example config\settings.json
```

3. Run the container with the config mount:

```powershell
docker run -d --name netflix-media-sync -p 8080:8080 -v ${PWD}\config:/config netflix-media-sync
```

4. Open `http://localhost:8080` in your browser.
5. In the Settings page, enter the local app URLs using `host.docker.internal`:
   - Radarr: `http://host.docker.internal:7878`
   - Sonarr: `http://host.docker.internal:8989`
   - Tautulli: `http://host.docker.internal:8181`
6. Enter the API keys for each service and save settings.

> Note: `host.docker.internal` resolves from the container back to the Windows host. If your Windows apps are listening on other ports, update the URLs accordingly.

### Notes

- Replace the example URLs with the actual service URLs from your network.
- Use container names or hostnames consistent with your Docker network.
- If Radarr, Sonarr, and Tautulli are in the same network, use their service names.

---

## Docker Compose deployment

The provided `docker-compose.yml` exposes the web UI and mounts the configuration directory. All integration settings are configured from the Settings page once the container starts.

```yaml
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
2. Copy `config/settings.json.example` to `config/settings.json` and fill in your values.
3. In Unraid, enable the `docker-compose` plugin if available.
4. Start the stack with `docker-compose up -d` from the project folder.

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
- It waits `RUN_INTERVAL_SECONDS` seconds between cycles (default 24 hours).
- The web UI allows manual sync and live settings configuration.
- Tautulli-protected titles are logged but no media is automatically removed.

## Customization

- To change the interval, update the setting in the UI or `/config/settings.json`.
- To protect a longer watch history window, update `tautulli_lookback_days` in the UI.

---

## Troubleshooting

### Common issues

- `Connection refused` from Radarr/Sonarr/Tautulli:
  - Check the URLs and ports.
  - Confirm the container can reach those hosts.
  - Use Docker networking or service names if services are in the same stack.

- Trakt fetch returns empty lists:
  - Verify your Trakt Client ID is correct in Settings.
  - Check container logs for HTTP errors from the Trakt API.

- Titles are not being added:
  - Verify API keys.
  - Confirm quality profile IDs and root folder paths exist.
  - Review container logs for warnings and errors.
  - Ensure Radarr/Sonarr mode is set to `Enabled` (not `Read only` or `Disabled`).

### Logging

Logs are written to standard output. Use `docker logs netflix-media-sync` or `docker-compose logs netflix-sync` to inspect.

---

## Notes and caveats

- The service fetches from Trakt trending, not a Netflix API.
- The Tautulli integration is read-only by default; it logs protected titles but does not trigger any deletion.
- Tautulli title matching is approximate (string comparison across services).

---

## License

This repository is provided without a specific license. Add a license file if you intend to publish it publicly.
