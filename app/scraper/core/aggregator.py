from app.scraper.core.models import MediaItem


def aggregate(sources: list[list[MediaItem]]) -> list[MediaItem]:
    """
    Merge results from multiple fetch() calls into a flat list.
    Does NOT deduplicate across sources — a title on both Netflix and Amazon
    is kept as two separate entries so the UI can show per-service availability.
    Deduplication within a single source is handled by each scraper.
    """
    results: list[MediaItem] = []
    for items in sources:
        results.extend(items)
    return results


def group_by_source_and_type(items: list[MediaItem]) -> dict[str, dict[str, list[MediaItem]]]:
    """
    Group a flat list of MediaItems into a nested dict by service and type.

    Returns:
        {
            "netflix":      {"movie": [...], "series": [...]},
            "disney_plus":  {"movie": [...], "series": [...]},
            ...
        }

    The movie lists map to Radarr imports, series lists to Sonarr imports.
    Import COUNTRIES from app.scraper.sources.streaming to populate a country dropdown.
    """
    result: dict[str, dict[str, list[MediaItem]]] = {}
    for item in items:
        result.setdefault(item.source, {}).setdefault(item.type, []).append(item)
    return result
