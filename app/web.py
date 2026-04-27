import datetime

import requests as _requests
from flask import Flask, Response, jsonify, render_template, request

from app.config import LOG_PATH
from app.manual_overrides import ManualOverrides
from app.removal_history import RemovalHistory
from app.settings import SettingsStore
from app.sync_log import SyncLog
from app.sync_service import SyncService

_SENTINEL = "__REDACTED__"
_SENSITIVE_KEYS = {
    "radarr_api_key",
    "sonarr_api_key",
    "tautulli_api_key",
    "trakt_client_id",
    "web_password",
    "pushover_user_key",
    "pushover_api_token",
}

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
    removal_history: RemovalHistory,
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

        def to_bool(value):
            return value in (True, "true", "on", "1", 1)

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
            "pushover_enabled": to_bool(payload.get("pushover_enabled")),
            "pushover_user_key": sensitive("pushover_user_key"),
            "pushover_api_token": sensitive("pushover_api_token"),
            "deletion_enabled": to_bool(payload.get("deletion_enabled")),
            "grace_period_days": safe_int(payload.get("grace_period_days"), 7),
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
        grace_period_days = int(settings.get("grace_period_days", 7))

        last_sync = sync_log.get_last_sync() or {}
        tautulli_protected = set(last_sync.get("protected", []))
        all_protected = tautulli_protected | manual_overrides.to_set()
        grace_periods = sync_log.get_grace_periods()

        today = datetime.date.today()
        schedule = []

        if radarr_mode != "disabled":
            for movie in sync_service.radarr.get_tagged_movies("netflix-sync"):
                title = movie.get("title", "")
                date_added = _resolve_date(sync_log.get_date_added(title), movie.get("added"), today)
                removal_date = date_added + datetime.timedelta(days=movie_retention)
                grace_info = grace_periods.get(title, {})
                in_grace, grace_expires_iso, days_until_deletion = _grace_fields(
                    grace_info, removal_date, grace_period_days, today
                )
                schedule.append({
                    "title": title,
                    "type": "movie",
                    "date_added": date_added.isoformat(),
                    "removal_date": removal_date.isoformat(),
                    "protected": title in all_protected,
                    "days_remaining": (removal_date - today).days,
                    "in_grace": in_grace,
                    "grace_expires": grace_expires_iso,
                    "days_until_deletion": days_until_deletion,
                })

        if sonarr_mode != "disabled":
            for series in sync_service.sonarr.get_tagged_series("netflix-sync"):
                title = series.get("title", "")
                date_added = _resolve_date(sync_log.get_date_added(title), series.get("added"), today)
                removal_date = date_added + datetime.timedelta(days=series_retention)
                grace_info = grace_periods.get(title, {})
                in_grace, grace_expires_iso, days_until_deletion = _grace_fields(
                    grace_info, removal_date, grace_period_days, today
                )
                schedule.append({
                    "title": title,
                    "type": "series",
                    "date_added": date_added.isoformat(),
                    "removal_date": removal_date.isoformat(),
                    "protected": title in all_protected,
                    "days_remaining": (removal_date - today).days,
                    "in_grace": in_grace,
                    "grace_expires": grace_expires_iso,
                    "days_until_deletion": days_until_deletion,
                })

        schedule.sort(key=lambda x: x["days_remaining"])
        return jsonify({"schedule": schedule})

    @app.route("/api/removal-history")
    def get_removal_history():
        return jsonify({"history": removal_history.get_recent()})

    @app.route("/api/top10-status")
    def top10_status():
        last = sync_log.get_last_sync() or {}
        top_movies = last.get("top_movies") or []
        top_series = last.get("top_series") or []

        radarr_mode = settings.get("radarr_mode", "disabled")
        sonarr_mode = settings.get("sonarr_mode", "disabled")

        movie_statuses: dict[str, str] = {}
        series_statuses: dict[str, str] = {}

        for title in top_movies:
            if radarr_mode == "disabled":
                movie_statuses[title] = "disabled"
                continue
            try:
                stub = sync_service.radarr.lookup_movie(title)
                if stub and stub.get("id"):
                    record = sync_service.radarr.get_movie_by_id(stub["id"])
                    movie_statuses[title] = "available" if (record or {}).get("hasFile") else "pending"
                else:
                    movie_statuses[title] = "will_add"
            except Exception:
                pass

        for title in top_series:
            if sonarr_mode == "disabled":
                series_statuses[title] = "disabled"
                continue
            try:
                stub = sync_service.sonarr.lookup_series(title)
                if stub and stub.get("id"):
                    record = sync_service.sonarr.get_series_by_id(stub["id"])
                    ep_count = ((record or {}).get("statistics") or {}).get("episodeFileCount", 0)
                    series_statuses[title] = "available" if ep_count > 0 else "pending"
                else:
                    series_statuses[title] = "will_add"
            except Exception:
                pass

        return jsonify({"movies": movie_statuses, "series": series_statuses})

    @app.route("/api/test/radarr", methods=["POST"])
    def test_radarr():
        payload = request.json or {}
        url = payload.get("url", "").rstrip("/")
        api_key = _resolve_test_key(payload.get("api_key", ""), settings.get("radarr_api_key", ""))
        return _test_arr(url, api_key)

    @app.route("/api/test/sonarr", methods=["POST"])
    def test_sonarr():
        payload = request.json or {}
        url = payload.get("url", "").rstrip("/")
        api_key = _resolve_test_key(payload.get("api_key", ""), settings.get("sonarr_api_key", ""))
        return _test_arr(url, api_key)

    @app.route("/api/test/tautulli", methods=["POST"])
    def test_tautulli():
        payload = request.json or {}
        url = payload.get("url", "").rstrip("/")
        api_key = _resolve_test_key(payload.get("api_key", ""), settings.get("tautulli_api_key", ""))
        if not url:
            return jsonify({"status": "error", "message": "URL is required"})
        if not api_key:
            return jsonify({"status": "error", "message": "API key is required"})
        try:
            r = _requests.get(
                f"{url}/api/v2",
                params={"apikey": api_key, "cmd": "get_server_info"},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("response", {}).get("result") == "success":
                name = data["response"]["data"].get("pms_name", "Plex")
                return jsonify({"status": "ok", "message": f"Connected — {name}"})
            msg = data.get("response", {}).get("message", "Unexpected response")
            return jsonify({"status": "error", "message": msg})
        except Exception as exc:
            return jsonify({"status": "error", "message": _exc_msg(exc)})

    @app.route("/api/test/pushover", methods=["POST"])
    def test_pushover():
        payload = request.json or {}
        user_key = _resolve_test_key(payload.get("user_key", ""), settings.get("pushover_user_key", ""))
        api_token = _resolve_test_key(payload.get("api_token", ""), settings.get("pushover_api_token", ""))
        if not user_key:
            return jsonify({"status": "error", "message": "User key is required"})
        if not api_token:
            return jsonify({"status": "error", "message": "API token is required"})
        try:
            r = _requests.post(
                "https://api.pushover.net/1/messages.json",
                data={
                    "token": api_token,
                    "user": user_key,
                    "title": "Netflix Sync — Test",
                    "message": "Test notification from Netflix Media Sync",
                    "priority": 0,
                },
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("status") == 1:
                return jsonify({"status": "ok", "message": "Notification sent"})
            errors = ", ".join(data.get("errors", ["Unknown error"]))
            return jsonify({"status": "error", "message": errors})
        except Exception as exc:
            return jsonify({"status": "error", "message": _exc_msg(exc)})

    @app.route("/api/logs")
    def get_logs():
        return jsonify({"lines": _tail_file(LOG_PATH, 2000)})

    @app.route("/api/logs/clear", methods=["POST"])
    def clear_logs():
        try:
            open(LOG_PATH, "w").close()
        except OSError as exc:
            return jsonify({"error": str(exc)}), 500
        return jsonify({"status": "cleared"})

    return app


def _resolve_test_key(submitted: str, stored: str) -> str:
    v = submitted.strip()
    return stored if v == _SENTINEL else v


def _exc_msg(exc: Exception) -> str:
    if isinstance(exc, _requests.exceptions.ConnectionError):
        return "Connection refused — check URL and port"
    if isinstance(exc, _requests.exceptions.Timeout):
        return "Request timed out"
    if isinstance(exc, _requests.exceptions.HTTPError):
        code = exc.response.status_code
        if code == 401:
            return "Invalid API key (401)"
        if code == 403:
            return "Forbidden — check API key permissions (403)"
        return f"HTTP {code}"
    return str(exc)


def _test_arr(url: str, api_key: str):
    if not url:
        return jsonify({"status": "error", "message": "URL is required"})
    if not api_key:
        return jsonify({"status": "error", "message": "API key is required"})
    try:
        hdrs = {"X-Api-Key": api_key}
        r = _requests.get(f"{url}/api/v3/qualityprofile", headers=hdrs, timeout=10)
        r.raise_for_status()
        profiles = [{"id": p["id"], "name": p["name"]} for p in r.json()]
        r = _requests.get(f"{url}/api/v3/rootfolder", headers=hdrs, timeout=10)
        r.raise_for_status()
        folders = [f["path"] for f in r.json()]
        return jsonify({
            "status": "ok",
            "message": "Connected",
            "quality_profiles": profiles,
            "root_folders": folders,
        })
    except Exception as exc:
        return jsonify({"status": "error", "message": _exc_msg(exc)})


def _tail_file(path, n: int = 100) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return [line.rstrip("\n") for line in lines[-n:]]
    except FileNotFoundError:
        return []


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


def _grace_fields(
    grace_info: dict,
    removal_date: datetime.date,
    grace_period_days: int,
    today: datetime.date,
) -> tuple[bool, str | None, int | None]:
    started = grace_info.get("started")
    if not started:
        return False, None, None
    try:
        grace_start = datetime.date.fromisoformat(started)
    except ValueError:
        return False, None, None
    grace_expires = grace_start + datetime.timedelta(days=grace_period_days)
    days_until_deletion = (grace_expires - today).days
    return True, grace_expires.isoformat(), days_until_deletion
