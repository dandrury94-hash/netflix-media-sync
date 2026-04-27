import logging
import requests

logger = logging.getLogger(__name__)

TRAKT_API_URL = "https://api.trakt.tv"


def fetch_netflix_top_10_for_countries(country_codes: list[str], client_id: str) -> tuple[list[str], list[str]]:
    movies = fetch_trakt_trending_movies(client_id)
    series = fetch_trakt_trending_series(client_id)
    logger.info("Fetched %d movies and %d series from Trakt", len(movies), len(series))
    return movies, series


def fetch_trakt_trending_movies(client_id: str) -> list[str]:
    url = f"{TRAKT_API_URL}/movies/trending"
    return _fetch_trakt_titles(url, client_id, "movie")


def fetch_trakt_trending_series(client_id: str) -> list[str]:
    url = f"{TRAKT_API_URL}/shows/trending"
    return _fetch_trakt_titles(url, client_id, "show")


def _fetch_trakt_titles(url: str, client_id: str, media_type: str) -> list[str]:
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": client_id,
    }
    try:
        response = requests.get(url, headers=headers, params={"limit": 10}, timeout=20)
        response.raise_for_status()
        data = response.json()
        titles = []
        for item in data:
            media = item.get(media_type, {})
            title = media.get("title")
            if title:
                titles.append(title)
        logger.info("Trakt returned titles: %s", titles)
        return titles[:10]
    except Exception as exc:
        logger.warning("Failed to fetch Trakt titles from %s: %s", url, exc)
        return []