import logging
import re
import urllib.error
import urllib.request

from bs4 import BeautifulSoup

from app.scraper.core.models import MediaItem

logger = logging.getLogger(__name__)


class FlixPatrolBanError(Exception):
    """Raised when FlixPatrol returns a ban/rate-limit signal (HTTP 429 or 403)."""
    def __init__(self, code: int):
        self.code = code
        super().__init__(f"FlixPatrol returned HTTP {code}")

BASE_URL = "https://flixpatrol.com/top10/streaming/{country}/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

# FlixPatrol URL slugs for each country
COUNTRIES = {
    "Argentina":            "argentina",
    "Australia":            "australia",
    "Austria":              "austria",
    "Belgium":              "belgium",
    "Brazil":               "brazil",
    "Bulgaria":             "bulgaria",
    "Canada":               "canada",
    "Chile":                "chile",
    "Colombia":             "colombia",
    "Croatia":              "croatia",
    "Czech Republic":       "czech-republic",
    "Denmark":              "denmark",
    "Ecuador":              "ecuador",
    "Finland":              "finland",
    "France":               "france",
    "Germany":              "germany",
    "Greece":               "greece",
    "Hong Kong":            "hong-kong",
    "Hungary":              "hungary",
    "Iceland":              "iceland",
    "India":                "india",
    "Indonesia":            "indonesia",
    "Ireland":              "ireland",
    "Israel":               "israel",
    "Italy":                "italy",
    "Japan":                "japan",
    "Malaysia":             "malaysia",
    "Mexico":               "mexico",
    "Netherlands":          "netherlands",
    "New Zealand":          "new-zealand",
    "Nigeria":              "nigeria",
    "Norway":               "norway",
    "Philippines":          "philippines",
    "Poland":               "poland",
    "Portugal":             "portugal",
    "Romania":              "romania",
    "Saudi Arabia":         "saudi-arabia",
    "Singapore":            "singapore",
    "Slovakia":             "slovakia",
    "South Africa":         "south-africa",
    "South Korea":          "south-korea",
    "Spain":                "spain",
    "Sweden":               "sweden",
    "Switzerland":          "switzerland",
    "Taiwan":               "taiwan",
    "Thailand":             "thailand",
    "Turkey":               "turkey",
    "Ukraine":              "ukraine",
    "United Arab Emirates": "united-arab-emirates",
    "United Kingdom":       "united-kingdom",
    "United States":        "united-states",
    "Venezuela":            "venezuela",
    "Vietnam":              "vietnam",
    "Worldwide":            "worldwide",
}

SERVICE_ALIASES = {
    "amazon prime": "amazon_prime",
    "apple tv store": "apple_tv_store",
    "apple tv": "apple_tv",
    "google": "google",
    "rakuten tv": "rakuten_tv",
    "amazon": "amazon",
    "disney+": "disney_plus",
    "netflix": "netflix",
    "paramount+": "paramount_plus",
    "hayu": "hayu",
    "now": "now",
    "chili": "chili",
}


def _normalise_service(raw: str) -> str:
    match = re.match(r"^(.+?)\s+TOP 10", raw, re.IGNORECASE)
    if not match:
        return raw.strip().lower()
    name = match.group(1).strip().lower()
    return SERVICE_ALIASES.get(name, name.replace(" ", "_"))


def fetch(country: str = "United Kingdom") -> list[MediaItem]:
    """
    Fetch all streaming Top 10s for a given country.

    Args:
        country: Country name from COUNTRIES dict (default: "United Kingdom")

    Returns:
        list of MediaItem grouped by service and type
    """
    slug = COUNTRIES.get(country)
    if not slug:
        available = ", ".join(sorted(COUNTRIES.keys()))
        logger.warning("[streaming] Unknown country '%s'. Available: %s", country, available)
        return []

    url = BASE_URL.format(country=slug)

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as res:
            html = res.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code in (429, 403):
            raise FlixPatrolBanError(e.code)
        logger.warning("[streaming] HTTP %d fetching %s", e.code, url)
        return []
    except Exception as e:
        logger.warning("[streaming] Failed to fetch %s: %s", url, e)
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []

    for table in soup.select("table"):
        card = table.find_parent("div", class_="card")
        if not card:
            continue

        label = card.get_text(strip=True).lower()

        if label.startswith("top 10 movies"):
            media_type = "movie"
        elif label.startswith("top 10 tv shows"):
            media_type = "series"
        else:
            continue

        content_div = table.find_parent("div", class_="content")
        if not content_div:
            continue
        heading = content_div.find("h2")
        if not heading:
            continue
        service = _normalise_service(heading.get_text(strip=True))

        for row in table.select("tr"):
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            rank_text = cols[0].get_text(strip=True).rstrip(".")
            if not rank_text.isdigit():
                continue

            link = cols[2].find("a")
            if not link:
                continue

            title = link.get_text(strip=True)
            if not title:
                continue

            results.append(MediaItem(
                title=title,
                type=media_type,
                source=service,
                rank=int(rank_text),
            ))

    # Deduplicate within each (source, type) group, then cap to top 10
    # and re-rank cleanly from 1
    seen: set[tuple[str, str, str]] = set()
    groups: dict[tuple[str, str], list[MediaItem]] = {}

    for item in results:
        key = (item.source, item.type, item.title)
        if key in seen:
            continue
        seen.add(key)
        group_key = (item.source, item.type)
        groups.setdefault(group_key, []).append(item)

    clean: list[MediaItem] = []
    for items in groups.values():
        # Sort by original rank, take top 10, re-rank from 1
        top10 = sorted(items, key=lambda x: x.rank)[:10]
        for i, item in enumerate(top10, start=1):
            item.rank = i
        clean.extend(top10)

    return clean
