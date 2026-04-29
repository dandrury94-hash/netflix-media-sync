from dataclasses import dataclass


@dataclass
class MediaItem:
    title: str
    type: str        # "movie" | "series"
    source: str      # "netflix" | "amazon_prime" | etc.
    rank: int
