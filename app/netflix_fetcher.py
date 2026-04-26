import logging
import re

import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)

NETFLIX_TOP_10_URL = "https://top10.netflix.com/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def build_netflix_top_url_for_country(country_code: str) -> str:
    country_code = country_code.strip().lower()
    if not country_code:
        return NETFLIX_TOP_10_URL
    return f"https://top10.netflix.com/{country_code}"


def fetch_netflix_top_10_for_countries(country_codes: list[str]) -> tuple[list[str], list[str]]:
    movies: list[str] = []
    series: list[str] = []
    seen_movies: set[str] = set()
    seen_series: set[str] = set()

    for country_code in country_codes:
        netflix_url = build_netflix_top_url_for_country(country_code)
        fetched_movies, fetched_series = fetch_netflix_top_10(netflix_url)
        logger.info("Fetched top titles for country %s via %s", country_code, netflix_url)

        for title in fetched_movies:
            if title not in seen_movies:
                seen_movies.add(title)
                movies.append(title)

        for title in fetched_series:
            if title not in seen_series:
                seen_series.add(title)
                series.append(title)

    return movies, series


def _extract_titles(html: str, expected_type: str) -> list[str]:
    pattern = re.compile(
        r'"title"\s*:\s*"(?P<title>[^"]+)".*?"type"\s*:\s*"(?P<type>[^"]+)"',
        re.DOTALL,
    )
    titles = []
    for match in pattern.finditer(html):
        title = match.group("title").strip()
        item_type = match.group("type").strip().lower()
        if expected_type == "movie" and item_type in {"movie", "film"}:
            titles.append(title)
        elif expected_type == "series" and item_type in {"tvshow", "show", "series"}:
            titles.append(title)
        if len(titles) >= 10:
            break
    return titles


def _extract_titles_from_html(html: str, expected_type: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    selector = "article" if expected_type == "movie" else "article"
    titles = []

    for card in soup.select(selector):
        heading = card.select_one("h3")
        if heading:
            text = heading.get_text(strip=True)
            if text and text not in titles:
                titles.append(text)
                if len(titles) >= 10:
                    break

    if len(titles) >= 10:
        return titles
    return []


def fetch_netflix_top_10(netflix_url: str = NETFLIX_TOP_10_URL) -> tuple[list[str], list[str]]:
    logger.info("Fetching Netflix top 10 page from %s", netflix_url)
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(netflix_url, headers=headers, timeout=20)
        response.raise_for_status()
        html = response.text

        movies = _extract_titles(html, "movie")
        series = _extract_titles(html, "series")

        if len(movies) < 10 or len(series) < 10:
            logger.info("Falling back to HTML extraction for Netflix top 10")
            movies = movies or _extract_titles_from_html(html, "movie")
            series = series or _extract_titles_from_html(html, "series")

        return movies[:10], series[:10]
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Failed to fetch Netflix top 10: %s", exc)
        return [], []
