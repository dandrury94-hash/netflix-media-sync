import os
from pathlib import Path

SETTINGS_PATH = Path(os.getenv("SETTINGS_PATH", "/config/settings.json"))
SYNC_LOG_PATH = Path(os.getenv("SYNC_LOG_PATH", "/config/sync_log.json"))
REMOVAL_HISTORY_PATH = Path(os.getenv("REMOVAL_HISTORY_PATH", "/config/removal_history.json"))
LOG_PATH = Path(os.getenv("LOG_PATH", "/config/app.log"))

DEFAULT_SETTINGS = {
    "radarr_mode": "disabled",
    "sonarr_mode": "disabled",
    "tautulli_mode": "disabled",
    "trakt_client_id": "",
    "radarr_url": "http://radarr:7878",
    "radarr_api_key": "",
    "sonarr_url": "http://sonarr:8989",
    "sonarr_api_key": "",
    "tautulli_url": "http://tautulli:8181",
    "tautulli_api_key": "",
    "root_folder_movies": "/movies",
    "root_folder_series": "/tv",
    "radarr_quality_profile_id": 1,
    "sonarr_quality_profile_id": 1,
    "run_interval_seconds": 86400,
    "tautulli_lookback_days": 30,
    "movie_retention_days": 30,
    "series_retention_days": 30,
    "web_port": 8080,
    "web_password": "",
    "netflix_top_url": "https://top10.netflix.com/",
    "netflix_top_countries": ["us"],
    "pushover_enabled": False,
    "pushover_user_key": "",
    "pushover_api_token": "",
    "deletion_enabled": False,
    "grace_period_days": 7,
    "sources": ["trakt"],
    "flixpatrol_country": "United Kingdom",
    "flixpatrol_services": [],
    "flixpatrol_service_types": {},
    "flixpatrol_cache_hours": 6,
}

ENV_VAR_TO_SETTING = {
    "TAUTULLI_URL": "tautulli_url",
    "TAUTULLI_API_KEY": "tautulli_api_key",
    "ROOT_FOLDER_MOVIES": "root_folder_movies",
    "ROOT_FOLDER_SERIES": "root_folder_series",
    "RADARR_QUALITY_PROFILE_ID": "radarr_quality_profile_id",
    "SONARR_QUALITY_PROFILE_ID": "sonarr_quality_profile_id",
    "RUN_INTERVAL_SECONDS": "run_interval_seconds",
    "TAUTULLI_LOOKBACK_DAYS": "tautulli_lookback_days",
    "WEB_PORT": "web_port",
    "WEB_PASSWORD": "web_password",
    "PUSHOVER_USER_KEY": "pushover_user_key",
    "PUSHOVER_API_TOKEN": "pushover_api_token",
    "DELETION_ENABLED": "deletion_enabled",
    "GRACE_PERIOD_DAYS": "grace_period_days",
}
