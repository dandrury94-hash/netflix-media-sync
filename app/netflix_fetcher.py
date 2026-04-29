import logging

import requests

logger = logging.getLogger(__name__)

TRAKT_API_URL = "https://api.trakt.tv"


def fetch_from_sources(sources: list[str], country_codes: list[str], client_id: str) -> list[dict]:
    """Fetch trending titles from all enabled sources, deduplicated by (title, type).

    Returns a list of dicts: {"title": str, "type": "movie"|"series", "source": str}
    """
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for source in sources:
        if source == "trakt":
            raw = _fetch_trakt_items(country_codes, client_id)
        elif source == "netflix":
            raw = []
        else:
            logger.warning("Unknown source %r, skipping", source)
            continue
        for item in raw:
            key = (item["title"].lower(), item["type"])
            if key not in seen:
                seen.add(key)
                items.append(item)
    return items


def _fetch_trakt_items(country_codes: list[str], client_id: str) -> list[dict]:
    movies, series = fetch_netflix_top_10_for_countries(country_codes, client_id)
    return (
        [{"title": t, "type": "movie", "source": "trakt"} for t in movies]
        + [{"title": t, "type": "series", "source": "trakt"} for t in series]
    )


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
