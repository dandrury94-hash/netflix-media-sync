import datetime

import requests as _requests
from flask import Flask, Response, jsonify, render_template, request

from app.config import LOG_PATH
from app.media_state import build_media_state
from app.netflix_fetcher import bust_flixpatrol_cache, fetch_flixpatrol_fresh, get_flixpatrol_cache_info
from app.removal_history import RemovalHistory
from app.scraper.sources.streaming import COUNTRIES as FLIXPATROL_COUNTRIES
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
                {"WWW-Authenticate": 'Basic realm="Streamarr"'},
            )

    def _fetch_media_state() -> dict:
        radarr_mode = settings.get("radarr_mode", "disabled")
        sonarr_mode = settings.get("sonarr_mode", "disabled")
        radarr_movies: list[dict] = []
        sonarr_tagged: list[dict] = []
        if radarr_mode != "disabled":
            radarr_movies = sync_service.radarr.get_tagged_movies()
        if sonarr_mode != "disabled":
            sonarr_tagged = sync_service.sonarr.get_tagged_series()
        last_sync = sync_log.get_last_sync() or {}
        tautulli_prot = set(last_sync.get("protected", []))
        radarr_prot_id = sync_service.radarr.get_state_protected_tag_id() if radarr_mode != "disabled" else None
        sonarr_prot_id = sync_service.sonarr.get_state_protected_tag_id() if sonarr_mode != "disabled" else None
        manual_prot: set[str] = set()
        if radarr_prot_id is not None:
            manual_prot |= {m["title"] for m in radarr_movies if radarr_prot_id in m.get("tags", [])}
        if sonarr_prot_id is not None:
            manual_prot |= {s["title"] for s in sonarr_tagged if sonarr_prot_id in s.get("tags", [])}
        return build_media_state(
            radarr_movies=radarr_movies,
            sonarr_series=sonarr_tagged,
            sync_entries=sync_log.get_entries(),
            grace_periods=sync_log.get_grace_periods(),
            protected_set=tautulli_prot | manual_prot,
            tautulli_protected=tautulli_prot,
            manual_protected=manual_prot,
            movie_retention_days=int(settings.get("movie_retention_days", 30)),
            series_retention_days=int(settings.get("series_retention_days", 30)),
            grace_period_days=int(settings.get("grace_period_days", 7)),
        )

    def _fmt_timestamp(ts: str) -> str:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
            try:
                return datetime.datetime.strptime(ts, fmt).strftime("%H:%M %d/%m/%Y")
            except ValueError:
                pass
        return ts

    @app.route("/")
    def index():
        last_sync = sync_log.get_last_sync()
        if last_sync and "timestamp" in last_sync:
            last_sync = {**last_sync, "timestamp": _fmt_timestamp(last_sync["timestamp"])}
        return render_template(
            "index.html",
            settings=settings.to_dict(),
            last_sync=last_sync,
        )

    @app.route("/settings")
    def settings_page():
        fp_country = settings.get("flixpatrol_country", "United Kingdom")
        fp_cache_hours = int(settings.get("flixpatrol_cache_hours", 6))
        fp_cache = get_flixpatrol_cache_info(fp_country, fp_cache_hours)
        if fp_cache.get("cached_at"):
            fp_cache["cached_at_fmt"] = datetime.datetime.fromtimestamp(
                fp_cache["cached_at"]
            ).strftime("%H:%M %d/%m/%Y")
        else:
            fp_cache["cached_at_fmt"] = None
        return render_template(
            "settings.html",
            settings=settings.to_dict(),
            country_options=COUNTRY_OPTIONS,
            flixpatrol_countries=sorted(FLIXPATROL_COUNTRIES.keys()),
            flixpatrol_cache=fp_cache,
        )

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
                **{k: v for k, v in request.form.items() if k not in ("netflix_top_countries", "sources", "flixpatrol_services")},
                "netflix_top_countries": request.form.getlist("netflix_top_countries"),
                "sources": request.form.getlist("sources"),
                "flixpatrol_services": request.form.getlist("flixpatrol_services"),
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

        sources_raw = payload.get("sources")
        if isinstance(sources_raw, str):
            sources_raw = [sources_raw.strip()] if sources_raw.strip() else []
        elif isinstance(sources_raw, list):
            sources_raw = [s.strip() for s in sources_raw if isinstance(s, str) and s.strip()]
        else:
            sources_raw = []
        sources = [s for s in sources_raw if s in ("trakt", "flixpatrol")]

        fp_country = payload.get("flixpatrol_country", "").strip()
        if fp_country not in FLIXPATROL_COUNTRIES:
            fp_country = settings.get("flixpatrol_country", "United Kingdom")

        fp_services_raw = payload.get("flixpatrol_services")
        if isinstance(fp_services_raw, str):
            fp_services_raw = [fp_services_raw.strip()] if fp_services_raw.strip() else []
        elif isinstance(fp_services_raw, list):
            fp_services_raw = [s.strip() for s in fp_services_raw if isinstance(s, str) and s.strip()]
        else:
            fp_services_raw = []
        fp_services = fp_services_raw

        fp_service_types_raw = payload.get("flixpatrol_service_types")
        if isinstance(fp_service_types_raw, dict):
            fp_service_types = {
                k: [t for t in v if t in ("movie", "series")]
                for k, v in fp_service_types_raw.items()
                if isinstance(k, str) and isinstance(v, list)
            }
        else:
            fp_service_types = settings.get("flixpatrol_service_types", {})

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
            "sources": sources,
            "pushover_enabled": to_bool(payload.get("pushover_enabled")),
            "pushover_user_key": sensitive("pushover_user_key"),
            "pushover_api_token": sensitive("pushover_api_token"),
            "deletion_enabled": to_bool(payload.get("deletion_enabled")),
            "grace_period_days": safe_int(payload.get("grace_period_days"), 7),
            "flixpatrol_country": fp_country,
            "flixpatrol_services": fp_services,
            "flixpatrol_service_types": fp_service_types,
            "flixpatrol_cache_hours": safe_int(payload.get("flixpatrol_cache_hours"), 6),
        }
        settings.update(normalized)
        return jsonify({"status": "saved"})

    @app.route("/api/sync", methods=["POST"])
    def trigger_sync():
        last = sync_log.get_last_sync() or {}
        estimated_seconds = int(last.get("duration_seconds") or 60)
        result = sync_service.run_once()
        return jsonify({"status": "ok", "result": result, "estimated_seconds": estimated_seconds})

    @app.route("/api/overrides", methods=["POST"])
    def post_overrides():
        payload = request.json or {}
        title = payload.get("title", "").strip()
        media_type = payload.get("type", "").strip()
        if not title:
            return jsonify({"error": "title required"}), 400
        if media_type not in ("movie", "series"):
            return jsonify({"error": "type must be 'movie' or 'series'"}), 400
        protected = bool(payload.get("protected", False))
        if media_type == "movie":
            all_movies = sync_service.radarr.get_all_movies()
            match = next((m for m in all_movies if m.get("title", "").lower() == title.lower()), None)
            if not match:
                return jsonify({"error": f"'{title}' not found in Radarr"}), 404
            ok = sync_service.radarr.set_movie_protection(match["id"], protected)
        else:
            all_series = sync_service.sonarr.get_all_series()
            match = next((s for s in all_series if s.get("title", "").lower() == title.lower()), None)
            if not match:
                return jsonify({"error": f"'{title}' not found in Sonarr"}), 404
            ok = sync_service.sonarr.set_series_protection(match["id"], protected)
        if not ok:
            return jsonify({"error": "Failed to update protection"}), 500
        return jsonify({"status": "ok", "title": title, "type": media_type, "protected": protected})

    @app.route("/api/removal-schedule")
    def removal_schedule():
        state = _fetch_media_state()
        schedule = sorted(state.values(), key=lambda x: x["days_remaining"])
        return jsonify({"schedule": schedule})

    @app.route("/api/removal-history")
    def get_removal_history():
        return jsonify({"history": removal_history.get_recent()})

    @app.route("/api/addition-history")
    def addition_history():
        entries = sync_log.get_entries()
        cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        seen: set[str] = set()
        recent: list[dict] = []
        for e in sorted(entries, key=lambda x: x.get("date_added", ""), reverse=True):
            title = e.get("title", "")
            if e.get("date_added", "") >= cutoff and title and title not in seen:
                seen.add(title)
                recent.append(e)
        return jsonify({"additions": recent})

    @app.route("/api/protection-state")
    def protection_state():
        state = _fetch_media_state()
        protected: list[dict] = []
        unprotected: list[dict] = []
        for entry in state.values():
            if entry["protected"]:
                protected.append({
                    "title": entry["title"],
                    "type": entry["type"],
                    "source": entry["protection_source"],
                    "reason": entry["reason"],
                })
            else:
                unprotected.append({
                    "title": entry["title"],
                    "type": entry["type"],
                    "reason": entry["reason"],
                })
        protected.sort(key=lambda x: x["title"].lower())
        unprotected.sort(key=lambda x: x["title"].lower())
        return jsonify({"protected": protected, "unprotected": unprotected})

    @app.route("/api/top10-status")
    def top10_status():
        last = sync_log.get_last_sync() or {}
        top_movies = last.get("top_movies") or []
        top_series = last.get("top_series") or []

        radarr_mode = settings.get("radarr_mode", "disabled")
        sonarr_mode = settings.get("sonarr_mode", "disabled")

        movie_lib: dict[str, dict] = {}
        series_lib: dict[str, dict] = {}

        if radarr_mode != "disabled" and top_movies:
            try:
                movie_lib = {
                    m["title"].lower(): m
                    for m in sync_service.radarr.get_all_movies()
                    if m.get("title")
                }
            except Exception:
                pass

        if sonarr_mode != "disabled" and top_series:
            try:
                series_lib = {
                    s["title"].lower(): s
                    for s in sync_service.sonarr.get_all_series()
                    if s.get("title")
                }
            except Exception:
                pass

        movie_statuses: dict[str, dict] = {}
        for title in top_movies:
            if radarr_mode == "disabled":
                movie_statuses[title] = {"status": "disabled", "poster": None}
                continue
            rec = movie_lib.get(title.lower())
            if rec and rec.get("id"):
                status = "available" if rec.get("hasFile") else "pending"
                poster = _extract_poster(rec.get("images", []))
            else:
                status = "will_add"
                poster = None
            movie_statuses[title] = {"status": status, "poster": poster}

        series_statuses: dict[str, dict] = {}
        for title in top_series:
            if sonarr_mode == "disabled":
                series_statuses[title] = {"status": "disabled", "poster": None}
                continue
            rec = series_lib.get(title.lower())
            if rec and rec.get("id"):
                ep_count = (rec.get("statistics") or {}).get("episodeFileCount", 0)
                status = "available" if ep_count > 0 else "pending"
                poster = _extract_poster(rec.get("images", []))
            else:
                status = "will_add"
                poster = None
            series_statuses[title] = {"status": status, "poster": poster}

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
                    "title": "Streamarr — Test",
                    "message": "Test notification from Streamarr",
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

    @app.route("/api/flixpatrol/preview")
    def flixpatrol_preview():
        country = request.args.get("country", "").strip()
        if not country or country not in FLIXPATROL_COUNTRIES:
            country = settings.get("flixpatrol_country", "United Kingdom")
        cache_hours = int(settings.get("flixpatrol_cache_hours", 6))
        grouped, error = fetch_flixpatrol_fresh(country)
        cache_info = get_flixpatrol_cache_info(country, cache_hours)
        if error and not grouped:
            return jsonify({
                "error": "FlixPatrol data unavailable — check streaming-scraper repo for updates",
                "country": country,
                "services": [],
                "cache": cache_info,
            })
        services = []
        for service_key, types in sorted(grouped.items()):
            movies = types.get("movie", [])
            series = types.get("series", [])
            services.append({
                "key": service_key,
                "label": service_key.replace("_", " ").title(),
                "movie_count": len(movies),
                "series_count": len(series),
                "sample_movies": [m.title for m in movies[:3]],
                "sample_series": [s.title for s in series[:3]],
            })
        return jsonify({"country": country, "services": services, "cache": cache_info})

    @app.route("/api/flixpatrol/refresh", methods=["POST"])
    def flixpatrol_refresh():
        country = settings.get("flixpatrol_country", "United Kingdom")
        cache_hours = int(settings.get("flixpatrol_cache_hours", 6))
        bust_flixpatrol_cache()
        grouped, error = fetch_flixpatrol_fresh(country)
        cache_info = get_flixpatrol_cache_info(country, cache_hours)
        services = []
        for service_key, types in sorted(grouped.items()):
            services.append({
                "key": service_key,
                "label": service_key.replace("_", " ").title(),
                "movie_count": len(types.get("movie", [])),
                "series_count": len(types.get("series", [])),
            })
        if error and not grouped:
            status = "error"
        elif error:
            status = "stale"
        else:
            status = "ok"
        return jsonify({
            "status": status,
            "error": error,
            "country": country,
            "services": services,
            "cache": cache_info,
        })

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


def _extract_poster(images: list) -> str | None:
    for img in images:
        if img.get("coverType") == "poster":
            return img.get("remoteUrl") or None
    return None