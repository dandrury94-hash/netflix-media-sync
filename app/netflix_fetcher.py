import logging
import time

from app.scraper.core.aggregator import aggregate, group_by_source_and_type
from app.scraper.sources.streaming import FlixPatrolBanError, fetch as flixpatrol_fetch

logger = logging.getLogger(__name__)

# In-memory FlixPatrol cache keyed by country name.
# Each entry: {attempt_ts, fetch_ts, fetched_at, grouped, error, ban_until}
_fp_cache: dict[str, dict] = {}

# Minimum seconds between network fetches regardless of cache staleness.
# Prevents rapid repeated syncs from triggering a scraping ban.
FP_MIN_FETCH_INTERVAL = 3600


def bust_flixpatrol_cache() -> None:
    """Clear FlixPatrol cached data while preserving ban window and rate-limit timing.

    Preserves ban_until and attempt_ts so that a manual cache bust cannot bypass
    an active scraping ban or immediately re-trigger a flood of network requests.
    """
    for entry in _fp_cache.values():
        entry.pop("grouped", None)
        entry.pop("fetch_ts", None)
        entry.pop("fetched_at", None)
        entry.pop("error", None)


def get_flixpatrol_cache_info(country: str, cache_hours: int = 6) -> dict:
    """Return cache metadata for the given country.

    Returns dict with: cached_at (float|None), age_seconds (float|None),
    is_stale (bool), error (str|None), banned (bool), ban_minutes_remaining (int|None).
    """
    entry = _fp_cache.get(country)
    if not entry:
        return {
            "cached_at": None, "age_seconds": None, "is_stale": True,
            "error": None, "banned": False, "ban_minutes_remaining": None,
        }
    now_mono = time.monotonic()
    fetch_ts = entry.get("fetch_ts")
    data_age = (now_mono - fetch_ts) if fetch_ts is not None else None
    is_stale = bool(entry.get("error")) or data_age is None or data_age >= cache_hours * 3600

    ban_until = entry.get("ban_until", 0)
    banned = now_mono < ban_until
    ban_minutes_remaining = max(1, int((ban_until - now_mono) / 60)) if banned else None

    return {
        "cached_at": entry.get("fetched_at"),
        "age_seconds": data_age,
        "is_stale": is_stale,
        "error": entry.get("error"),
        "banned": banned,
        "ban_minutes_remaining": ban_minutes_remaining,
    }


def fetch_flixpatrol_fresh(country: str) -> tuple[dict, str | None]:
    """Fetch FlixPatrol for the given country, always hitting the network unless banned.

    Updates the module-level cache and returns (grouped, error_or_None).
    On failure, returns last known cached grouped data (possibly empty) plus an error string.
    Respects active ban windows set by previous 429/403 responses.
    """
    now_mono = time.monotonic()
    now_wall = time.time()
    entry = _fp_cache.get(country, {})

    ban_until = entry.get("ban_until", 0)
    if now_mono < ban_until:
        minutes_left = max(1, int((ban_until - now_mono) / 60))
        err = f"FlixPatrol scraping blocked — retry in ~{minutes_left} min"
        logger.warning("FlixPatrol: ban window active for '%s', %d min remaining", country, minutes_left)
        return entry.get("grouped", {}), err

    try:
        raw_items = flixpatrol_fetch(country)
    except FlixPatrolBanError as exc:
        err = f"FlixPatrol rate-limited (HTTP {exc.code}) — retry in ~60 min"
        _fp_cache[country] = {
            **entry,
            "attempt_ts": now_mono,
            "error": err,
            "ban_until": now_mono + FP_MIN_FETCH_INTERVAL,
        }
        logger.warning("FlixPatrol ban signal for '%s': HTTP %d", country, exc.code)
        return entry.get("grouped", {}), err

    if raw_items:
        grouped = group_by_source_and_type(aggregate([raw_items]))
        _fp_cache[country] = {
            "attempt_ts": now_mono,
            "fetch_ts": now_mono,
            "fetched_at": now_wall,
            "grouped": grouped,
            "error": None,
            "ban_until": 0,
        }
        return grouped, None
    else:
        err = "FlixPatrol data unavailable — check streaming-scraper repo for updates"
        _fp_cache[country] = {
            **entry,
            "attempt_ts": now_mono,
            "error": err,
        }
        logger.warning("FlixPatrol returned no items for country '%s'", country)
        return _fp_cache[country].get("grouped", {}), err


def fetch_from_sources(
    sources: list[str],
    flixpatrol_country: str = "United Kingdom",
    flixpatrol_services: list[str] | None = None,
    flixpatrol_service_types: dict | None = None,
    flixpatrol_cache_hours: int = 6,
) -> list[dict]:
    """Fetch trending titles from all enabled sources, deduplicated by (title, type).

    Returns a list of dicts: {"title": str, "type": "movie"|"series", "source": str}
    """
    items: list[dict] = []
    seen: dict[tuple[str, str], int] = {}          # (title_lower, type) → index in items
    sources_seen: dict[tuple[str, str], dict] = {}  # (title_lower, type) → {source: None} ordered set
    for source in sources:
        if source == "flixpatrol":
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
    now_mono = time.monotonic()

    # Always surface an active ban — skip network, use whatever data is cached
    if entry and entry.get("ban_until", 0) > now_mono:
        minutes_left = max(1, int((entry["ban_until"] - now_mono) / 60))
        logger.warning(
            "FlixPatrol: ban window active for '%s', %d min remaining — using stale cache",
            country, minutes_left,
        )
        grouped = entry.get("grouped", {})
        if not grouped:
            return []
        # fall through to filter/return logic below

    else:
        use_cache = (
            entry is not None
            and (now_mono - entry.get("attempt_ts", 0)) < cache_hours * 3600
        )

        # Rate-limit floor: prevent re-fetching more often than once per FP_MIN_FETCH_INTERVAL
        # even when cache was manually busted or cache_hours is very small.
        if not use_cache and entry and (now_mono - entry.get("attempt_ts", 0)) < FP_MIN_FETCH_INTERVAL:
            logger.info(
                "FlixPatrol: rate limit floor active for '%s' (%.0f min since last attempt) — using stale cache",
                country, (now_mono - entry["attempt_ts"]) / 60,
            )
            grouped = entry.get("grouped", {})
            if not grouped:
                return []
            use_cache = True  # treat as cache hit for the log below

        if use_cache:
            grouped = entry["grouped"]
            if entry.get("error"):
                logger.warning("FlixPatrol using stale cache for '%s': %s", country, entry["error"])
            else:
                logger.info(
                    "FlixPatrol cache hit for '%s' (data %.0f min old)",
                    country,
                    (now_mono - entry["fetch_ts"]) / 60,
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


