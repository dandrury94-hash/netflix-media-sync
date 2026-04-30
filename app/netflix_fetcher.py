import logging
import time

import requests

from app.scraper.core.aggregator import aggregate, group_by_source_and_type
from app.scraper.sources.streaming import fetch as flixpatrol_fetch

logger = logging.getLogger(__name__)

TRAKT_API_URL = "https://api.trakt.tv"

# In-memory FlixPatrol cache keyed by country name.
# Each entry: {attempt_ts, fetch_ts, fetched_at, grouped, error}
_fp_cache: dict[str, dict] = {}


def bust_flixpatrol_cache() -> None:
    """Clear the FlixPatrol in-memory result cache."""
    _fp_cache.clear()


def get_flixpatrol_cache_info(country: str, cache_hours: int = 6) -> dict:
    """Return cache metadata for the given country.

    Returns dict with: cached_at (float|None), age_seconds (float|None),
    is_stale (bool), error (str|None).
    """
    entry = _fp_cache.get(country)
    if not entry:
        return {"cached_at": None, "age_seconds": None, "is_stale": True, "error": None}
    fetch_ts = entry.get("fetch_ts")
    data_age = (time.monotonic() - fetch_ts) if fetch_ts is not None else None
    is_stale = bool(entry.get("error")) or data_age is None or data_age >= cache_hours * 3600
    return {
        "cached_at": entry.get("fetched_at"),
        "age_seconds": data_age,
        "is_stale": is_stale,
        "error": entry.get("error"),
    }


def fetch_flixpatrol_fresh(country: str) -> tuple[dict, str | None]:
    """Fetch FlixPatrol for the given country, always hitting the network.

    Updates the module-level cache and returns (grouped, error_or_None).
    On failure, returns last known cached grouped data (possibly empty) plus an error string.
    """
    raw_items = flixpatrol_fetch(country)
    now_mono = time.monotonic()
    now_wall = time.time()

    if raw_items:
        grouped = group_by_source_and_type(aggregate([raw_items]))
        _fp_cache[country] = {
            "attempt_ts": now_mono,
            "fetch_ts": now_mono,
            "fetched_at": now_wall,
            "grouped": grouped,
            "error": None,
        }
        return grouped, None
    else:
        err = "FlixPatrol data unavailable — check streaming-scraper repo for updates"
        entry = _fp_cache.get(country)
        _fp_cache[country] = {
            "attempt_ts": now_mono,
            "fetch_ts": entry.get("fetch_ts") if entry else None,
            "fetched_at": entry.get("fetched_at") if entry else None,
            "grouped": entry.get("grouped", {}) if entry else {},
            "error": err,
        }
        logger.warning("FlixPatrol returned no items for country '%s'", country)
        return _fp_cache[country]["grouped"], err


def fetch_from_sources(
    sources: list[str],
    country_codes: list[str],
    client_id: str,
    flixpatrol_country: str = "United Kingdom",
    flixpatrol_services: list[str] | None = None,
    flixpatrol_service_types: dict | None = None,
    flixpatrol_cache_hours: int = 6,
) -> list[dict]:
    """Fetch trending titles from all enabled sources, deduplicated by (title, type).

    Returns a list of dicts: {"title": str, "type": "movie"|"series", "source": str}

    Args:
        sources:                   List of enabled source names — "trakt" and/or "flixpatrol".
        country_codes:             Trakt country filter codes (e.g. ["gb", "us"]).
        client_id:                 Trakt API client ID (unused when only flixpatrol is active).
        flixpatrol_country:        Full country name for FlixPatrol (e.g. "United Kingdom").
        flixpatrol_services:       Whitelist of FlixPatrol service keys to include
                                   (e.g. ["netflix", "disney_plus"]). Empty list = all services.
        flixpatrol_service_types:  Per-service type filter (e.g. {"netflix": ["movie"]}).
                                   Missing key or empty dict means both types for that service.
        flixpatrol_cache_hours:    How many hours to cache FlixPatrol results before re-fetching.
    """
    items: list[dict] = []
    seen: dict[tuple[str, str], int] = {}          # (title_lower, type) → index in items
    sources_seen: dict[tuple[str, str], dict] = {}  # (title_lower, type) → {source: None} ordered set
    for source in sources:
        if source == "trakt":
            raw = _fetch_trakt_items(country_codes, client_id)
        elif source == "flixpatrol":
            raw = _fetch_flixpatrol_items(
                flixpatrol_country,
                flixpatrol_services or [],
                flixpatrol_service_types or {},
                flixpatrol_cache_hours,
            )
        else:
            logger.warning("Unknown source %r, skipping", source)
            continue
        for item in raw:
            if not item.get("source"):
                logger.warning("Source dict missing or empty 'source' key, skipping: %r", item)
                continue
            key = (item["title"].lower(), item["type"])
            if key in seen:
                sources_seen[key][item["source"]] = None  # idempotent; preserves insertion order
                items[seen[key]]["sources"] = list(sources_seen[key].keys())
            else:
                seen[key] = len(items)
                sources_seen[key] = {item["source"]: None}
                items.append({**item, "sources": [item["source"]]})
    return items


def _fetch_trakt_items(country_codes: list[str], client_id: str) -> list[dict]:
    movies, series = fetch_netflix_top_10_for_countries(country_codes, client_id)
    return (
        [{"title": t, "type": "movie", "source": "trakt"} for t in movies]
        + [{"title": t, "type": "series", "source": "trakt"} for t in series]
    )


def _fetch_flixpatrol_items(
    country: str,
    services: list[str],
    service_types: dict,
    cache_hours: int = 6,
) -> list[dict]:
    """Return FlixPatrol titles for the given country, using cache when fresh.

    Args:
        country:       Full country name matching COUNTRIES keys (e.g. "United Kingdom").
        services:      If non-empty, only titles from these service keys are returned.
                       If empty, all services are included.
        service_types: Per-service type allowlist (e.g. {"netflix": ["movie"]}).
                       A missing key means both types are included for that service.
        cache_hours:   Hours before the cache entry is considered stale and re-fetched.

    Returns:
        list of dicts compatible with fetch_from_sources output format.
    """
    entry = _fp_cache.get(country)
    use_cache = (
        entry is not None
        and (time.monotonic() - entry.get("attempt_ts", 0)) < cache_hours * 3600
    )

    if use_cache:
        grouped = entry["grouped"]
        if entry.get("error"):
            logger.warning("FlixPatrol using stale cache for '%s': %s", country, entry["error"])
        else:
            logger.info(
                "FlixPatrol cache hit for '%s' (data %.0f min old)",
                country,
                (time.monotonic() - entry["fetch_ts"]) / 60,
            )
    else:
        grouped, error = fetch_flixpatrol_fresh(country)
        if not grouped:
            logger.warning("FlixPatrol unavailable for '%s' and no cache available", country)
            return []
        if error:
            logger.warning("FlixPatrol fetch failed for '%s', using stale data", country)

    # Apply service filter if configured
    if services:
        grouped = {k: v for k, v in grouped.items() if k in services}

    results: list[dict] = []
    for service_key, types in grouped.items():
        allowed = service_types.get(service_key)
        include_movies = allowed is None or "movie" in allowed
        include_series = allowed is None or "series" in allowed
        if include_movies:
            for movie in types.get("movie", []):
                results.append({"title": movie.title, "type": "movie", "source": service_key})
        if include_series:
            for series in types.get("series", []):
                results.append({"title": series.title, "type": "series", "source": service_key})

    logger.info(
        "FlixPatrol fetched %d items from %s (country: %s, services filter: %s, type filter: %s)",
        len(results),
        list(grouped.keys()),
        country,
        services or "all",
        service_types or "all",
    )
    return results


def fetch_netflix_top_10_for_countries(country_codes: list[str], client_id: str) -> tuple[list[str], list[str]]:
    """Fetch trending titles from Trakt, optionally filtered by country code.

    Trakt's trending endpoints accept a ``country`` query parameter. When
    multiple country codes are provided the results are fetched per-country and
    deduplicated, preserving the order of first appearance.
    """
    codes = country_codes if country_codes else [None]

    movies = _dedup_fetch(codes, client_id, "movie")
    series = _dedup_fetch(codes, client_id, "show")

    logger.info(
        "Fetched %d movies and %d series from Trakt (countries: %s)",
        len(movies),
        len(series),
        country_codes or ["global"],
    )
    return movies, series


def _dedup_fetch(codes: list[str | None], client_id: str, media_type: str) -> list[str]:
    url = f"{TRAKT_API_URL}/movies/trending" if media_type == "movie" else f"{TRAKT_API_URL}/shows/trending"
    seen: set[str] = set()
    ordered: list[str] = []
    for code in codes:
        for title in _fetch_trakt_titles(url, client_id, media_type, country=code):
            if title not in seen:
                seen.add(title)
                ordered.append(title)
    return ordered[:10]


def _fetch_trakt_titles(url: str, client_id: str, media_type: str, country: str | None = None) -> list[str]:
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": client_id,
    }
    params: dict = {"limit": 10}
    if country:
        params["country"] = country
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        titles = []
        for item in data:
            media = item.get(media_type, {})
            title = media.get("title")
            if title:
                titles.append(title)
        return titles[:10]
    except Exception as exc:
        logger.warning("Failed to fetch Trakt titles from %s (country=%s): %s", url, country, exc)
        return []
