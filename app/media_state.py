import datetime
from typing import TypedDict


class MediaStateEntry(TypedDict):
    title: str
    type: str
    radarr_id: int | None
    sonarr_id: int | None
    in_library: bool
    has_file: bool
    protected: bool
    protection_source: str | None      # "tautulli" | "manual" | "both" | None
    eligible_for_deletion: bool
    days_remaining: int
    date_added: str
    removal_date: str
    status: str                         # "available" | "pending"
    reason: str


def build_media_state(
    radarr_movies: list[dict],
    sonarr_series: list[dict],
    sync_entries: list[dict],
    protected_set: set[str],
    tautulli_protected: set[str],
    manual_protected: set[str],
    movie_retention_days: int,
    series_retention_days: int,
    last_watched: dict[str, str] | None = None,
) -> dict[str, MediaStateEntry]:
    """
    Build an in-memory state map for all streamarr tagged titles.
    Keyed by lowercase title. No API calls are made here.
    """
    today = datetime.date.today()

    earliest_added: dict[str, str] = {}
    for entry in sync_entries:
        t = entry.get("title", "")
        d = entry.get("date_added", "")
        if t and d:
            if t not in earliest_added or d < earliest_added[t]:
                earliest_added[t] = d

    def _resolve_date(log_date: str | None, api_added: str | None) -> datetime.date:
        if log_date:
            try:
                return datetime.date.fromisoformat(log_date)
            except ValueError:
                pass
        if api_added:
            try:
                return datetime.datetime.fromisoformat(
                    api_added.replace("Z", "+00:00")
                ).date()
            except ValueError:
                pass
        return today

    _SRC_LABELS = {"tautulli": "Tautulli", "manual": "Manual", "both": "Tautulli & Manual"}

    state: dict[str, MediaStateEntry] = {}

    def _add(
        title: str,
        media_type: str,
        record_id: int | None,
        has_file: bool,
        api_added: str | None,
        retention_days: int,
    ) -> None:
        date_added = _resolve_date(earliest_added.get(title), api_added)
        anchor_date = date_added
        lw = (last_watched or {}).get(title)
        if lw:
            try:
                anchor_date = max(date_added, datetime.date.fromisoformat(lw))
            except ValueError:
                pass
        removal_date = anchor_date + datetime.timedelta(days=retention_days)
        days_remaining = (removal_date - today).days

        in_tautulli = title in tautulli_protected
        in_manual = title in manual_protected
        is_protected = title in protected_set
        if in_tautulli and in_manual:
            protection_source: str | None = "both"
        elif in_tautulli:
            protection_source = "tautulli"
        elif in_manual:
            protection_source = "manual"
        else:
            protection_source = None

        eligible = days_remaining <= 0 and not is_protected

        status = "available" if has_file else "pending"

        if is_protected:
            src = _SRC_LABELS.get(protection_source or "", "")
            reason = f"Protected — {src}" if src else "Protected"
        elif eligible:
            reason = "Eligible for deletion"
        elif days_remaining <= 7:
            reason = f"Removal in {days_remaining}d"
        elif days_remaining <= 30:
            reason = f"Removal on {removal_date.strftime('%d/%m/%Y')}"
        else:
            reason = ""

        state[title.lower()] = {
            "title": title,
            "type": media_type,
            "radarr_id": record_id if media_type == "movie" else None,
            "sonarr_id": record_id if media_type == "series" else None,
            "in_library": True,
            "has_file": has_file,
            "protected": is_protected,
            "protection_source": protection_source,
            "eligible_for_deletion": eligible,
            "days_remaining": days_remaining,
            "date_added": date_added.isoformat(),
            "removal_date": removal_date.isoformat(),
            "status": status,
            "reason": reason,
        }

    for movie in radarr_movies:
        title = movie.get("title", "")
        if title:
            _add(
                title=title,
                media_type="movie",
                record_id=movie.get("id"),
                has_file=bool(movie.get("hasFile")),
                api_added=movie.get("added"),
                retention_days=movie_retention_days,
            )

    for series in sonarr_series:
        title = series.get("title", "")
        if title:
            ep_count = (series.get("statistics") or {}).get("episodeFileCount", 0)
            _add(
                title=title,
                media_type="series",
                record_id=series.get("id"),
                has_file=ep_count > 0,
                api_added=series.get("added"),
                retention_days=series_retention_days,
            )

    return state
