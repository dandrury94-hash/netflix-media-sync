from unittest.mock import patch
from app.netflix_fetcher import fetch_from_sources


def _fp(items):
    return patch("app.netflix_fetcher._fetch_flixpatrol_items", return_value=items)


def test_all_items_have_non_empty_sources_list():
    """Every item returned by fetch_from_sources must carry a non-empty sources list."""
    mock_items = [
        {"title": "Movie A", "type": "movie", "source": "netflix"},
        {"title": "Show B", "type": "series", "source": "disney_plus"},
    ]
    with _fp(mock_items):
        result = fetch_from_sources(sources=["flixpatrol"])

    for item in result:
        assert isinstance(item.get("sources"), list), f"sources missing on {item['title']!r}"
        assert len(item["sources"]) > 0, f"sources is empty on {item['title']!r}"


def test_distinct_titles_each_get_their_own_source():
    """Items that do not overlap keep a single-element sources list from their own source."""
    fp_items = [
        {"title": "Only On Netflix", "type": "movie", "source": "netflix"},
        {"title": "Only On Disney", "type": "movie", "source": "disney_plus"},
    ]
    with _fp(fp_items):
        result = fetch_from_sources(sources=["flixpatrol"])

    by_title = {i["title"]: i for i in result}
    assert by_title["Only On Netflix"]["sources"] == ["netflix"]
    assert by_title["Only On Disney"]["sources"] == ["disney_plus"]
