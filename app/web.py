import datetime

from flask import Flask, Response, jsonify, render_template, request

from app.manual_overrides import ManualOverrides
from app.settings import SettingsStore
from app.sync_log import SyncLog
from app.sync_service import SyncService

_SENTINEL = "__REDACTED__"
_SENSITIVE_KEYS = {"radarr_api_key", "sonarr_api_key", "tautulli_api_key", "trakt_client_id", "web_password"}

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


def create_app(
    settings: SettingsStore,
    sync_service: SyncService,
    sync_log: SyncLog,
    manual_overrides: ManualOverrides,
) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.before_request
    def check_auth():
        password = settings.get("web_password", "")
        if not password:
            return
        auth = request.authorization
        if not auth or auth.password != password:
            return Response(
                "Authentication required",
                401,
                {"WWW-Authenticate": 'Basic realm="Netflix Sync"'},
            )

    @app.route("/")
    def index():
        last_sync = sync_log.get_last_sync()
        manual = manual_overrides.to_set()
        tautulli_protected = set(last_sync.get("protected", [])) if last_sync else set()
        all_protected = sorted(tautulli_protected | manual)
        return render_template(
            "index.html",
            settings=settings.to_dict(),
            last_sync=last_sync,
            protected_titles=all_protected,
            tautulli_protected=tautulli_protected,
            manual_protected=manual,
        )

    @app.route("/settings")
    def settings_page():
        return render_template("settings.html", settings=settings.to_dict(), country_options=COUNTRY_OPTIONS)

    @app.route("/api/settings", methods=["GET"])
    def get_settings():
        data = settings.to_dict()
        for key in _SENSITIVE_KEYS:
            if data.get(key):
                data[key] = _SENTINEL
        return jsonify(data)

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

        def sensitive(key):
            v = payload.get(key, "").strip()
            return settings.get(key, "") if v == _SENTINEL else v

        countries = payload.get("netflix_top_countries")
        if isinstance(countries, str):
            countries = [c.strip().lower() for c in countries.split(",") if c.strip()]
        elif isinstance(countries, list):
            countries = [c.strip().lower() for c in countries if isinstance(c, str) and c.strip()]
        else:
            countries = []

        normalized = {
            "radarr_url": payload.get("radarr_url", "").strip(),
            "radarr_api_key": sensitive("radarr_api_key"),
            "sonarr_url": payload.get("sonarr_url", "").strip(),
            "sonarr_api_key": sensitive("sonarr_api_key"),
            "tautulli_url": payload.get("tautulli_url", "").strip(),
            "tautulli_api_key": sensitive("tautulli_api_key"),
            "radarr_mode": payload.get("radarr_mode", "disabled").strip(),
            "sonarr_mode": payload.get("sonarr_mode", "disabled").strip(),
            "tautulli_mode": payload.get("tautulli_mode", "disabled").strip(),
            "trakt_client_id": sensitive("trakt_client_id"),
            "root_folder_movies": payload.get("root_folder_movies", "").strip(),
            "root_folder_series": payload.get("root_folder_series", "").strip(),
            "radarr_quality_profile_id": safe_int(payload.get("radarr_quality_profile_id"), 1),
            "sonarr_quality_profile_id": safe_int(payload.get("sonarr_quality_profile_id"), 1),
            "run_interval_seconds": safe_int(payload.get("run_interval_seconds"), 86400),
            "tautulli_lookback_days": safe_int(payload.get("tautulli_lookback_days"), 30),
            "movie_retention_days": safe_int(payload.get("movie_retention_days"), 30),
            "series_retention_days": safe_int(payload.get("series_retention_days"), 30),
            "web_port": safe_int(payload.get("web_port"), 8080),
            "web_password": sensitive("web_password"),
            "netflix_top_countries": countries,
        }
        settings.update(normalized)
        return jsonify({"status": "saved"})

    @app.route("/api/sync", methods=["POST"])
    def trigger_sync():
        result = sync_service.run_once()
        return jsonify({"status": "ok", "result": result})

    @app.route("/api/overrides", methods=["POST"])
    def post_overrides():
        payload = request.json or {}
        title = payload.get("title", "").strip()
        if not title:
            return jsonify({"error": "title required"}), 400
        protected = bool(payload.get("protected", False))
        manual_overrides.set_override(title, protected)
        return jsonify({"status": "ok", "title": title, "protected": protected})

    @app.route("/api/removal-schedule")
    def removal_schedule():
        radarr_mode = settings.get("radarr_mode", "disabled")
        sonarr_mode = settings.get("sonarr_mode", "disabled")
        movie_retention = int(settings.get("movie_retention_days", 30))
        series_retention = int(settings.get("series_retention_days", 30))

        last_sync = sync_log.get_last_sync() or {}
        tautulli_protected = set(last_sync.get("protected", []))
        all_protected = tautulli_protected | manual_overrides.to_set()

        today = datetime.date.today()
        schedule = []

        if radarr_mode != "disabled":
            for movie in sync_service.radarr.get_tagged_movies("netflix-sync"):
                title = movie.get("title", "")
                date_added = _resolve_date(sync_log.get_date_added(title), movie.get("added"), today)
                removal_date = date_added + datetime.timedelta(days=movie_retention)
                schedule.append({
                    "title": title,
                    "type": "movie",
                    "date_added": date_added.isoformat(),
                    "removal_date": removal_date.isoformat(),
                    "protected": title in all_protected,
                    "days_remaining": (removal_date - today).days,
                })

        if sonarr_mode != "disabled":
            for series in sync_service.sonarr.get_tagged_series("netflix-sync"):
                title = series.get("title", "")
                date_added = _resolve_date(sync_log.get_date_added(title), series.get("added"), today)
                removal_date = date_added + datetime.timedelta(days=series_retention)
                schedule.append({
                    "title": title,
                    "type": "series",
                    "date_added": date_added.isoformat(),
                    "removal_date": removal_date.isoformat(),
                    "protected": title in all_protected,
                    "days_remaining": (removal_date - today).days,
                })

        schedule.sort(key=lambda x: x["days_remaining"])
        return jsonify({"schedule": schedule})

    return app


def _resolve_date(
    log_date: str | None,
    api_added: str | None,
    fallback: datetime.date,
) -> datetime.date:
    if log_date:
        try:
            return datetime.date.fromisoformat(log_date)
        except ValueError:
            pass
    if api_added:
        try:
            return datetime.datetime.fromisoformat(
                api_added.replace("Z", "+00:00")
            ).date()
        except ValueError:
            pass
    return fallback
