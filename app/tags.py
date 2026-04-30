TAG_ROOT       = "streamarr"
TAG_SRC_PREFIX = "streamarr-src-"
TAG_CAT_MOVIE  = "streamarr-cat-movie"
TAG_CAT_TV     = "streamarr-cat-tv"


def tag_root() -> str:
    return TAG_ROOT


def tag_source(source: str) -> str:
    return f"{TAG_SRC_PREFIX}{source}"


def tag_category(media_type: str) -> str:
    return TAG_CAT_MOVIE if media_type == "movie" else TAG_CAT_TV


def all_tags_for(sources: str | list[str], media_type: str) -> list[str]:
    if isinstance(sources, str):
        sources = [sources]
    return [TAG_ROOT] + [tag_source(s) for s in sources] + [tag_category(media_type)]
