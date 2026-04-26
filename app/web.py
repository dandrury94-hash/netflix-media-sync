from flask import Flask, jsonify, redirect, render_template, request, url_for
from app.settings import SettingsStore
from app.sync_service import SyncService

COUNTRY_OPTIONS = [
    ("us", "United States"),
    ("gb", "United Kingdom"),
    ("ca", "Canada"),
    ("de", "Germany"),
    ("fr", "France"),
    ("jp", "Japan"),
    ("br", "Brazil"),
    ("au", "Australia"),
    ("es", "Spain"),
    ("it", "Italy"),
    ("nl", "Netherlands"),
    ("se", "Sweden"),
    ("mx", "Mexico"),
    ("in", "India"),
]


def create_app(settings: SettingsStore, sync_service: SyncService) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.route("/")
    def index():
        return render_template("index.html", settings=settings.to_dict())

    @app.route("/settings")
    def settings_page():
        return render_template("settings.html", settings=settings.to_dict(), country_options=COUNTRY_OPTIONS)

    @app.route("/api/settings", methods=["GET"])
    def get_settings():
        return jsonify(settings.to_dict())

    @app.route("/api/settings", methods=["POST"])
    def post_settings():
        if request.is_json:
            payload = request.json or {}
        else:
            payload = {
                **{k: v for k, v in request.form.items() if k != "netflix_top_countries"},
                "netflix_top_countries": request.form.getlist("netflix_top_countries"),
            }

        def safe_int(value, default):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def safe_bool(value):
            return str(value).strip().lower() == "true"

        countries = payload.get("netflix_top_countries")
        if isinstance(countries, str):
            countries = [country.strip().lower() for country in countries.split(",") if country.strip()]
        elif isinstance(countries, list):
            countries = [country.strip().lower() for country in countries if isinstance(country, str) and country.strip()]
        else:
            countries = []

        normalized = {
            "radarr_url": payload.get("radarr_url", "").strip(),
            "radarr_api_key": payload.get("radarr_api_key", "").strip(),
            "sonarr_url": payload.get("sonarr_url", "").strip(),
            "sonarr_api_key": payload.get("sonarr_api_key", "").strip(),
            "tautulli_url": payload.get("tautulli_url", "").strip(),
            "tautulli_api_key": payload.get("tautulli_api_key", "").strip(),
            "root_folder_movies": payload.get("root_folder_movies", "").strip(),
            "root_folder_series": payload.get("root_folder_series", "").strip(),
            "radarr_quality_profile_id": safe_int(payload.get("radarr_quality_profile_id"), 1),
            "sonarr_quality_profile_id": safe_int(payload.get("sonarr_quality_profile_id"), 1),
            "run_interval_seconds": safe_int(payload.get("run_interval_seconds"), 86400),
            "delete_old_media": safe_bool(payload.get("delete_old_media", "false")),
            "tautulli_lookback_days": safe_int(payload.get("tautulli_lookback_days"), 30),
            "movie_retention_days": safe_int(payload.get("movie_retention_days"), 30),
            "series_retention_days": safe_int(payload.get("series_retention_days"), 30),
            "web_port": safe_int(payload.get("web_port"), 8080),
            "netflix_top_countries": countries,
        }
        settings.update(normalized)
        return jsonify({"status": "saved", "settings": settings.to_dict()})

    @app.route("/api/sync", methods=["POST"])
    def trigger_sync():
        result = sync_service.run_once()
        return jsonify({"status": "ok", "result": result})

    return app
