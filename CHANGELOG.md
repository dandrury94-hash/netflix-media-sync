# Changelog

All changes to this project are recorded here with a unique reference, date, and description.

---

## CHG-046 — 2026-05-07 — T-017/T-019: Dismiss sync + Tautulli accuracy + active watches

### Fixes
- **T-017** — Cross-card dismiss sync: already working via existing
  `loadTop10Status()` call in dismiss/undo handlers — confirmed resolved,
  no code change required
- **T-019 Part 1** — `app/sync_service.py`: `set_last_watched()` now only
  called for Tautulli-watched titles that are present in the Radarr or
  Sonarr library cache; unmanaged titles are skipped with a debug log;
  filtered count logged as `updated last_watched for N/M titles`

### Additions
- **T-019 Part 2** — `app/web.py`: `/api/active-watches` endpoint returns
  `last_watched` entries filtered to streamarr-tagged titles only (uses
  `get_tagged_movies()` / `get_tagged_series()`)
- **`app/templates/index.html`** — "Active watches — retention extended"
  card added to Protection tab below Protection Manager; loads via async
  JS call on tab render
- **`app/static/script.js`** — `loadActiveWatches()` and
  `renderActiveWatches()` functions; renders a table of title / type /
  last watched date
- **`app/static/style.css`** — `.prot-subtitle` muted inline label style
- **`app/templates/base.html`** — CSS version bumped to `?v=046`

---

## CHG-045 — 2026-05-07 — Rank tracking: NEW badge persists for 48 hours

### Fixes
- **`app/static/script.js`** — `NEW` badge now shows for any title whose
  `first_seen` is within the last 2 days, rather than only on the sync
  immediately after first appearance; trend arrows (`↑`/`↓`) are suppressed
  while a title is still showing `NEW` to avoid conflicting signals

---

## CHG-044 — 2026-05-07 — P3-1: Rank tracking over time

### Additions
- **`app/rank_tracker.py`** — new `RankTracker` store: tracks `rank`,
  `previous_rank`, and `first_seen` per title per source per media type;
  persisted to `config/rank_tracker.json`; titles that leave the list are
  removed immediately (no dropped-off retention)
- **`app/config.py`** — `RANK_TRACKER_PATH` added
- **`app/main.py`** — `RankTracker` instantiated and passed to `SyncService`
- **`app/sync_service.py`** — `RankTracker` injected; `_run()` calls
  `rank_tracker.update()` for each source/type after `top_by_source` is built;
  `rank_data` bundled into the `last_sync` result dict
- **`app/templates/index.html`** — rank data attributes (`data-rank`,
  `data-prev-rank`, `data-first-seen`) embedded on each `<li>` from
  `last_sync.rank_data`; no extra API call required
- **`app/static/script.js`** — `_applyRankIndicators()`: reads data attributes
  on page load and prepends trend badges (`NEW` amber / `↑` green / `↓` dim)
  and appends a days-in-list label (`Xd`) where applicable; runs once on
  DOMContentLoaded, independent of the status/poster API fetch
- **`app/static/style.css`** — `.rank-badge`, `.rank-badge--new`,
  `.rank-badge--up`, `.rank-badge--down`, `.rank-days` styles
- **`app/templates/base.html`** — CSS version bumped to `?v=044`
- **`.gitignore`** — `config/rank_tracker.json` added

---

## CHG-043 — 2026-05-07 — T-015: ID-based library matching (title mismatch fix)

### Fixes
- **`app/sync_service.py`** — library presence checks in sim/read modes and dismissal
  deletions now fall back to TMDB ID / TVDb ID matching when the title cache misses,
  preventing false `would_add` entries for titles already in the library under a
  slightly different name (e.g. `"Run, Fatboy, Run"` vs `"Run Fatboy Run"`)

### Changes
- **`app/sync_service.py`** — `_lookup_in_library()` private helper added: checks
  title cache first; on miss calls `lookup_movie()` / `lookup_series()` to resolve
  the external ID, then checks a secondary `tmdbId` / `tvdbId` keyed cache; logs
  `[id-match]` warning when neither resolves (treats item as genuinely new)
- **`app/sync_service.py`** — `_run()`: bulk fetches now build both a title-keyed
  and ID-keyed cache from the same `get_all_movies()` / `get_all_series()` response
  (no additional API calls); `_lookup_in_library()` used in all four
  sim/read code paths (radarr sim, radarr read, sonarr sim, sonarr read)
- **`app/sync_service.py`** — `run_dismissal_deletions()`: same dual-cache pattern
  applied so title-mismatched dismissed items are correctly found and deleted
- **`DECISIONS.md`** — D16 added: when to branch vs. commit to master

---

## CHG-042 — 2026-05-07 — P2-5: Simulation / dry-run mode

### Additions
- **`app/config.py`** — `simulation_mode: False` added to `DEFAULT_SETTINGS`
- **`app/sync_service.py`** — simulation mode guard throughout:
  - `_run()`: when `simulation_mode` is true and `radarr_mode`/`sonarr_mode` is
    `"enabled"`, evaluates the title list against the library cache and populates
    `would_add_movies` / `would_add_series` without calling `add_movie()`,
    `add_series()`, or `sync_log.log_add()`; Tautulli `set_last_watched()` is also
    skipped; Pushover add notification is suppressed; `"simulation": true` included
    in result dict
  - `run_deletions()`: adds `would_delete_movies` / `would_delete_series` lists;
    skips `delete_movie()`, `delete_series()`, `log_removal()`,
    `mark_pre_deletion_notified()`, `clear_pre_deletion_notified()`, and all
    Pushover sends when simulation mode is active; logs `[sim]` lines instead
  - `run_dismissal_deletions()`: returns early with empty result in simulation mode
- **`app/web.py`** — `post_settings()`: `simulation_mode` added to normalized dict
- **`app/templates/settings.html`** — simulation mode checkbox in Retention & sync section
- **`app/templates/index.html`** — amber banner shown at top of Dashboard tab when
  simulation mode is active; sync stat labels switch to "to add (sim)" when
  `radarr_mode`/`sonarr_mode` is `enabled` and simulation mode is on
- **`app/static/style.css`** — `.sim-mode-banner` (amber border, dark amber bg) and
  `.sim-badge` (inline amber label tag) styles
- **`app/templates/base.html`** — CSS version bumped to `?v=042`

---

## CHG-041 — 2026-05-07 — T-016: Default poster placeholder for unresolved titles

### Additions
- **`app/static/style.css`** — `.top10-item--no-poster` and `::before` rule: same
  36×54px absolutely-positioned slot as `--has-poster`, dim background with subtle
  border and "TBA" text; applied whenever `poster` is null
- **`app/static/script.js`** — `_applyTop10Data()`: poster/placeholder logic moved
  before the `dismissed` early return so dismissed items also show their poster or
  placeholder; uses `classList.toggle` to mutually flip `--has-poster` /
  `--no-poster` on every refresh; `--poster-url` CSS variable cleared when null
- **`app/templates/base.html`** — CSS version bumped to `?v=041`

---

## CHG-040 — 2026-05-07 — Repo hygiene

### Fixes
- **`.gitignore`** — removed stale `config/manual_overrides.json` entry (module
  deleted in CHG-034; runtime file also deleted from disk)

### Additions
- **`requirements-dev.txt`** — new file; `pytest>=8.0` for local test runs;
  kept separate from `requirements.txt` so it is not installed in the Docker image
- **`conftest.py`** — project root conftest; enables `from app.xxx import ...`
  in tests without installation
- **`tests/test_netflix_fetcher.py`** — three smoke tests covering `fetch_from_sources()`:
  all items carry a non-empty `sources` list; shared titles are deduplicated with
  both sources merged; distinct titles each retain their own single-source list

### Confirmed clean
- `config/manual_overrides.json` — deleted (no code references remain)
- `__pycache__/` — already in `.gitignore` (T-013)
- `streamarrtree.txt` — does not exist in repo (T-014)

---

## CHG-039 — 2026-05-07 — Poster lookup fallback for unresolved Top 10 titles

### Fixes
- **`app/web.py`** — `top10_status()`: titles not found in the Radarr/Sonarr library
  now fall back to `lookup_movie(title)` / `lookup_series(title)` to fetch a poster
  from the Radarr/Sonarr TMDB/TVDb index; poster is extracted from the lookup result's
  `images` array using the existing `_extract_poster()` helper; status remains
  `will_add`; lookup is bounded to at most 10 titles per service so it is not an
  unbounded N+1 pattern; titles with no TMDB/TVDb entry (promotional content, very
  new releases) correctly return `null` poster

### Backlog additions
- **`tasks/todo.md`** — T-016: default placeholder poster for unresolved titles
- **`tasks/todo.md`** — T-015: ID-based title matching (Radarr/Sonarr) to replace
  exact lowercase title lookups; fixes status misclassification for library items
  whose titles differ slightly from the Top 10 source title

---

## CHG-038 — 2026-05-07 — CHG-037 regression fix + P3-0: Top 10 item dismissal

### Fixes
- **`app/main.py`** — `run_weekly_preview`: removed stale `tautulli_protected` variable
  (`last_sync.get("protected", [])`) and removed `title in tautulli_protected` from both
  the Radarr and Sonarr skip conditions; protection check now uses only `manually_protected`
  (the `streamarr-state-protected` tag), consistent with the P2-2 model
- **`app/tags.py`** — `tag_source()`: replaces `_` with `-` in source names before building
  the tag label; Radarr rejects tag labels containing underscores (`^[a-z0-9-]+$`); e.g.
  `amazon_prime` → `streamarr-src-amazon-prime`
- **`app/web.py`** — `undo_until` timestamps now carry a `Z` suffix (`isoformat() + "Z"`) in
  both `POST /api/dismiss` and `_dismissed_fields()`; without `Z`, JavaScript's `Date.parse()`
  treats the naive ISO string as local time — users ahead of UTC saw the undo window as already
  expired immediately after dismissing

### Additions
- **`app/dismissed.py`** — new `DismissedTitles` class; persistent JSON store at
  `DISMISSED_PATH` (`/config/dismissed.json`); thread-safe (`threading.Lock`); methods:
  `dismiss(title, type, in_library)`, `undismiss(title)`, `get_all()`, `is_dismissed(title)`,
  `get_pending_deletion()` (entries where `in_library=True` and ≥15 min have elapsed),
  `mark_deleted(title)` (sets `in_library=False` to prevent re-deletion); entries are never
  removed after deletion — they persist so dismissed titles are never re-added by future syncs
- **`app/config.py`** — `DISMISSED_PATH` added
- **`app/sync_service.py`** — `__init__` accepts `dismissed: DismissedTitles`; both enabled-mode
  add loops (`movie_items`, `series_items`) skip titles where `self.dismissed.is_dismissed()` is
  true; new `run_dismissal_deletions()` method: fetches pending-deletion entries, looks up items
  in Radarr/Sonarr by title, calls `delete_movie`/`delete_series`, logs removal, sends Pushover,
  always calls `mark_deleted()` regardless of outcome to prevent infinite retry
- **`app/main.py`** — imports `DismissedTitles`; constructs instance and passes to `SyncService`
  and `create_app`; launches a daemon thread (`_dismissal_loop`) that calls
  `run_dismissal_deletions()` every 60 seconds
- **`app/web.py`** — imports `DismissedTitles`; `create_app` accepts `dismissed` parameter;
  `POST /api/dismiss`: validates `title`, `type`, `in_library` (bool), calls `dismissed.dismiss()`,
  returns `{status, title, in_library, undo_until}`; `DELETE /api/dismiss`: calls
  `dismissed.undismiss(title)`; `GET /api/top10-status`: each entry now includes `type`
  (`"movie"` or `"series"`), `dismissed` (bool), and `undo_until` (UTC ISO string or null —
  present only if dismissed and within the 15-min undo window)
- **`app/static/script.js`** — `_applyTop10Data()` extended: dismissed items receive
  `top10-item--dismissed` CSS class (greyed out, title struck through); dismissed items within
  the 15-min undo window show a `↩` undo button that calls `DELETE /api/dismiss` then re-fetches
  status; non-dismissed items show a red `×` dismiss button prepended to the list item (leftmost
  position) that calls `POST /api/dismiss` (passing
  `in_library = status !== "will_add" && status !== "disabled"`) then re-fetches status
- **`app/static/style.css`** — `.top10-dismiss` (red `×`, `order: -1` to appear before
  counter/poster), `.top10-title` (`flex: 1` to keep status icon right-aligned),
  `.top10-item--dismissed` (opacity 0.4, title strikethrough), `.top10-undo` (blue `↩` arrow,
  `margin-left: auto`, fully opaque on greyed row)
- **`app/templates/base.html`** — CSS link versioned (`?v=038b`) to force cache invalidation
- **`app/CLAUDE.md`** — persistence layer documented: three stores (`SyncLog`, `RemovalHistory`,
  `DismissedTitles`) with paths and retention rules

---

## CHG-037 — 2026-05-06 — P2-1 + P2-2: Multi-source addition history, Tautulli removed from protection model

### Changes
- **`app/sync_log.py`** — `log_add()` signature changed: `source: str = "trakt"` → `sources: list[str]`; stored field renamed from `"source"` to `"sources"` (list); existing single-source entries are migrated on read at the API layer
- **`app/sync_service.py`** — `_run()`: both `log_add()` call sites now pass `item["sources"]` (the full list from `fetch_from_sources`) instead of the hardcoded `"trakt"` default
- **`app/web.py`** — `addition_history()`: normalises entries on the fly — if an old entry has only `"source"` (str), it is returned as `sources: [source]`; new entries carry `sources` list directly; `_fetch_media_state()`: removed `tautulli_prot` / `last_sync.get("protected", [])` from protection evaluation; removed `protected_set` and `tautulli_protected` arguments from `build_media_state()` call
- **`app/media_state.py`** — `build_media_state()`: removed `protected_set` and `tautulli_protected` parameters; protection is now derived solely from `manual_protected`; removed `"tautulli"`, `"both"` branches from `_add()` and corresponding `_SRC_LABELS` entries; `MediaStateEntry.protection_source` type narrowed to `"manual" | None`
- **`app/static/script.js`** — `renderAdditionHistory()`: added `fmtSource()` helper that maps `"flixpatrol"` → `"FlixPatrol"` and title-cases others; source cell now joins the `sources` array with `" + "` (e.g. `"Trakt + FlixPatrol"`); falls back to `item.source` for old entries
- **`app/templates/index.html`** — removed stale "Tautulli-protected titles cannot be unprotected here" note from protection tab
- **`app/CLAUDE.md`** — updated Protection section to reflect new model: `streamarr-state-protected` tag only; Tautulli = retention signal only; `protection_source` valid values: `"manual"` | `None`

## CHG-036 — 2026-05-06 — P1-5 + P1-6 + P1-7: Tag-only deletion, grace period removal, pre-deletion warnings

### Changes
- **`app/sync_service.py`** — `run_deletions()`: removed `tautulli_protected` title-string matching from the deletion gate — protection is now fully tag-based (manual override tag) combined with `last_watched` anchor dates; removed all grace period state (`start_grace_period`, `get_grace_periods`, `clear_grace_period`); when a title enters the 7-day window before its removal date, a Pushover warning is sent once per title (tracked in `pre_deletion_notified`); when `days_remaining <= 0`, deletion proceeds immediately with no grace delay; `was_watched` now derived from `last_watched_all` presence rather than Tautulli title comparison; return value no longer includes `grace_started`
- **`app/sync_log.py`** — removed `grace_periods` dict and the three associated methods (`start_grace_period`, `get_grace_periods`, `clear_grace_period`); added `pre_deletion_notified: dict[str, str]` (title → date notified) with `mark_pre_deletion_notified(title)`, `get_pre_deletion_notified() -> dict`, and `clear_pre_deletion_notified(title)`; `_load()` now migrates old JSON by removing the stale `grace_periods` key
- **`app/media_state.py`** — `build_media_state()` no longer accepts `grace_periods` or `grace_period_days` parameters; `MediaStateEntry` no longer includes `grace_started`, `grace_expires`, `days_until_deletion`, or `in_grace` fields; `eligible_for_deletion` is now `days_remaining <= 0 and not is_protected`; `reason` field no longer has grace-period conditions
- **`app/web.py`** — `_fetch_media_state()` call to `build_media_state()` drops `grace_periods` and `grace_period_days` arguments; `post_settings()` normalized dict no longer saves `grace_period_days`
- **`app/config.py`** — removed `grace_period_days` from `DEFAULT_SETTINGS` and `GRACE_PERIOD_DAYS` from `ENV_VAR_TO_SETTING`
- **`app/templates/settings.html`** — removed grace period days input field; updated deletion help text to describe 7-day Pushover warning instead
- **`app/templates/index.html`** — removed "Grace expires" and "Days to delete" columns from scheduled removals table; colspan updated to 7
- **`app/static/script.js`** — removed `graceCell` and `deleteCell` from `renderSchedule()`; table row reduced from 9 to 7 columns; all `colspan="9"` updated to `colspan="7"`

### Infrastructure
- P1-7 confirmed satisfied: `run_deletions()` and `_fetch_media_state()` both source exclusively from `get_tagged_movies()` / `get_tagged_series()` — unmanaged library items are never evaluated or surfaced in any Streamarr UI

---


## CHG-035 — 2026-05-06 — P1-4: Reset retention clock on last_watched

### Fixes
- **`app/tautulli_client.py`** — `fetch_protected_titles()` was always returning an empty set; `get_history` response nests history records under `response.data.data` (not `response.data`), and `get_activity` nests sessions under `response.data.sessions` (not `response.sessions`); both lookups now unwrap the inner `data` dict first — Tautulli protection was silently non-functional before this fix

### Changes
- **`app/sync_log.py`** — added `"last_watched": {}` to the in-memory data structure and load fallback; `set_last_watched(title, date_iso)` writes or updates the most-recent watch date for a title (only saves if the new date is equal to or later than the stored one); `get_last_watched_all() -> dict[str, str]` returns a snapshot of all stored watch dates for bulk pre-fetch
- **`app/sync_service.py`** — `_run()`: after fetching Tautulli protected titles, records today's date as `last_watched` for each returned title via `sync_log.set_last_watched()`; `run_deletions()`: pre-fetches `last_watched_all` once before both loops; per-item retention anchor is `max(date_added, last_watched)` — watching a title resets the deletion clock from that watch date rather than the original add date
- **`app/media_state.py`** — `build_media_state()` accepts optional `last_watched: dict[str, str]`; `_add()` resolves the same `max(date_added, last_watched)` anchor so the UI removal date matches the actual deletion logic
- **`app/web.py`** — `_fetch_media_state()` passes `last_watched=sync_log.get_last_watched_all()` to `build_media_state()`
- **`app/main.py`** — `run_weekly_preview()` applies the same `anchor_date` logic so weekly Pushover notifications reflect watch-adjusted removal dates

---


## CHG-034 — 2026-05-06 — P1-2 + P1-3: Protection via Radarr/Sonarr tag

### Additions
- **`app/radarr_client.py`** — `get_state_protected_tag_id() -> int | None`: fetches the Radarr tag list and returns the ID for `streamarr-state-protected`, or `None` if not yet created; `set_movie_protection(movie_id, protected)`: GETs the full movie record, adds or removes the `streamarr-state-protected` tag ID, then PUTs the updated record back — returns `True` on success
- **`app/sonarr_client.py`** — identical additions: `get_state_protected_tag_id()` and `set_series_protection(series_id, protected)`

### Changes
- **`app/tags.py`** — added `TAG_STATE_PROTECTED = "streamarr-state-protected"` constant and `tag_state_protected() -> str` helper
- **`app/web.py`** — `POST /api/overrides` now requires `type` field (`"movie"` or `"series"`); on receipt it bulk-fetches the relevant library, finds the item by title, and immediately writes the `streamarr-state-protected` tag to Radarr or Sonarr — no JSON file involved; `_fetch_media_state()` derives `manual_prot` by resolving the `streamarr-state-protected` tag ID once then filtering the already-fetched item lists; `ManualOverrides` parameter removed from `create_app()`; index route no longer passes `protected_titles`/`tautulli_protected`/`manual_protected` to the template (all loaded async via API)
- **`app/sync_service.py`** — `run_deletions()` resolves `streamarr-state-protected` tag ID once per service before each deletion loop; per-item protection check reads from the item's `tags` array rather than a JSON file; `ManualOverrides` removed from `__init__` signature and import
- **`app/main.py`** — `run_weekly_preview()` signature updated to remove `manual_overrides` parameter; protection check reads from item tags same as `run_deletions()`; `ManualOverrides` instantiation and passing removed from `main()`; `create_app()` call updated to match new signature
- **`app/static/script.js`** — all five `/api/overrides` call sites updated to include `type` in the JSON payload; `handleProtectionToggle()` accepts `type` as new third argument; `_makeEntry()` stores `dataset.title` and `dataset.type` on each checkbox; batch protect/unprotect use `cb.dataset.title` / `cb.dataset.type` instead of `cb.value`; removal schedule action buttons include `data-type` attribute; dead `.override-checkbox` listener removed

### Removals
- **`app/manual_overrides.py`** — deleted; protection state now lives exclusively in Radarr/Sonarr as the `streamarr-state-protected` tag
- **`app/config.py`** — `MANUAL_OVERRIDES_PATH` removed

---


## CHG-033 — 2026-05-06 — Workflow scaffolding: tasks/ directory

### Additions
- **`tasks/todo.md`** — task planning and progress tracker; one block per session or feature; format mirrors §14 of CLAUDE.md (plan → verify → track → review)
- **`tasks/lessons.md`** — lessons log capturing corrections and the rules derived from them; pre-populated with three lessons from recent sessions: never tag pre-existing library items, wait for user confirmation before committing, and use dict insertion order for deterministic source lists

---


## CHG-032 — 2026-04-30 — P1-0 + P1-1: Multi-source tags and ownership check

### Changes
- **`app/netflix_fetcher.py`** — `fetch_from_sources()` deduplication rewritten: `seen` is now a `dict[key → index]` instead of a set; when a `(title, type)` pair is seen again from a later source, its source key is appended to the existing entry's `"sources"` list rather than dropped. Each returned dict now carries both `"source"` (first/primary source, kept for backwards compatibility with `top_by_source` grouping) and `"sources"` (full list of all sources that listed this title). Defensive guard added: items with a missing or empty `"source"` key are logged as a warning and skipped, preventing a silent `streamarr-src-` tag from being produced
- **`app/tags.py`** — `all_tags_for(sources, media_type)` signature changed from `source: str` to `sources: str | list[str]`; a bare string is promoted to a single-element list automatically; returns one `streamarr-src-{s}` tag per source so a title appearing on Netflix and Disney+ receives both `streamarr-src-netflix` and `streamarr-src-disney_plus` alongside the root `streamarr` and category tags
- **`app/sync_service.py`** — enabled-mode add loops now pass `item["sources"]` (the full source list) instead of `item["source"]` to `all_tags_for()` so all source attribution tags are applied per title
- **`app/radarr_client.py`** — added `_put()` HTTP helper mirroring `_post()`; added `_resolve_tag_ids(tag_names, title)` which calls `ensure_tag()` per name and collects the resulting IDs; `add_movie()` skips any title that already exists in the library (cache hit with id, or lookup result with id) — Streamarr only owns items it adds; items already present before Streamarr are never touched and never become deletion candidates; new items are added via POST with all applicable tags
- **`app/sonarr_client.py`** — identical approach: `_put()` and `_resolve_tag_ids()` added; `add_series()` skips existing library items without modifying them

### Fixes
- **`app/netflix_fetcher.py`** — `sources` list is now deduplicated and order-preserving: a parallel `sources_seen` dict (keyed by the same `(title_lower, type)` tuple) uses Python dict insertion order to guarantee that the first-seen source remains first and any subsequent occurrence of the same source is silently dropped via idempotent dict assignment; this ensures identical input always produces identical tag sets across runs

---


## CHG-031 — 2026-04-30 — P1-2: Deletion ownership comment

### Changes
- **`app/sync_service.py`** — comment added before the `get_tagged_movies()` loop in `run_deletions()` documenting that deletion eligibility is determined solely by the presence of the `streamarr` tag: items whose tag is removed externally in Radarr or Sonarr are automatically excluded from deletion — Streamarr no longer considers them managed and will not attempt to delete them

---


## CHG-030 — 2026-04-30 — Tag namespace: netflix-sync → streamarr

### Additions
- **`app/tags.py`** — new module defining the Streamarr tag namespace: constants `TAG_ROOT = "streamarr"`, `TAG_SRC_PREFIX = "streamarr-src-"`, `TAG_CAT_MOVIE = "streamarr-cat-movie"`, `TAG_CAT_TV = "streamarr-cat-tv"`, and four helpers: `tag_root()`, `tag_source(source)` (e.g. `"netflix"` → `"streamarr-src-netflix"`), `tag_category(media_type)` (`"movie"` → `TAG_CAT_MOVIE`, anything else → `TAG_CAT_TV`), and `all_tags_for(source, media_type)` returning all three tags for an item

### Changes
- **`app/radarr_client.py`** — removed `_TAG_NAME = "netflix-sync"` constant; added `from app import tags as _tags`; `get_tagged_movies()` parameter removed — now looks up `_tags.TAG_ROOT` internally; `add_movie()` gains `tags: list[str] | None = None` parameter and calls `self.ensure_tag()` once per name in the list (falls back to `[TAG_ROOT]` if omitted)
- **`app/sonarr_client.py`** — same changes as `radarr_client.py`: removed `_TAG_NAME`; added `_tags` import; `get_tagged_series()` parameter removed; `add_series()` gains `tags: list[str] | None = None` and calls `ensure_tag()` per name
- **`app/sync_service.py`** — added `from app import tags as _tags`; `_run()` now builds `movie_items` / `series_items` lists (full dicts, not just titles) so the source key is available at add time; `add_movie()` and `add_series()` calls now pass `tags=_tags.all_tags_for(item["source"], "movie"|"series")`; `run_deletions()` calls `get_tagged_movies()` and `get_tagged_series()` without arguments (tag resolved inside the clients)
- **`app/main.py`** — weekly preview loop: `get_tagged_movies("netflix-sync")` and `get_tagged_series("netflix-sync")` → `get_tagged_movies()` / `get_tagged_series()`
- **`app/web.py`** — `_fetch_media_state()`: same two call-site updates as `main.py`
- **`app/media_state.py`** — docstring updated: "netflix-sync tagged" → "streamarr tagged"
- **`app/CLAUDE.md`** — deletion safety rule updated: "Only netflix-sync tagged items may be deleted" → "Only streamarr tagged items may be deleted"
- **`README.md`** — three tag references updated from `netflix-sync` to the new `streamarr` / `streamarr-src-{source}` / `streamarr-cat-*` vocabulary

### Removed
- `_TAG_NAME = "netflix-sync"` constant removed from `app/radarr_client.py` and `app/sonarr_client.py`
- `tag_name: str` parameter removed from `get_tagged_movies()` and `get_tagged_series()` — tag is now resolved inside the clients from `tags.TAG_ROOT`

---


## CHG-029 — 2026-04-30 — Rebrand: Netflix Sync → Streamarr

### Changes
- **`CLAUDE.md`** — heading changed from "Netflix Media Sync" to "Streamarr"
- **`README.md`** — top-level heading changed to "Streamarr"; `docker run` example: `--name` flag and image name changed to `streamarr`; `docker-compose` example: service key and image name changed to `streamarr`
- **`docker-compose.yml`** — service key renamed from `netflix-sync` to `streamarr`
- **`app/templates/base.html`** — `<title>` fallback changed from `'Netflix Sync'` to `'Streamarr'`; brand `<strong>` label changed from `Netflix Sync` to `Streamarr`
- **`app/web.py`** — HTTP Basic Auth realm changed from `"Netflix Sync"` to `"Streamarr"`; Pushover test notification title changed from `"Netflix Sync — Test"` to `"Streamarr — Test"`; test notification message changed from `"Test notification from Netflix Media Sync"` to `"Test notification from Streamarr"`
- **`app/sync_service.py`** — Pushover notification titles changed: `"Netflix Sync — Error"` → `"Streamarr — Error"`, `"Netflix Sync — Added"` → `"Streamarr — Added"`, `"Netflix Sync — Deleted"` (×2) → `"Streamarr — Deleted"`
- **`app/main.py`** — startup log message changed from `"Starting Netflix Sync service"` to `"Starting Streamarr service"`; weekly preview Pushover title changed from `"Netflix Sync — Weekly Preview"` to `"Streamarr — Weekly Preview"`
- **`app/static/script.js`** — log download filename changed from `netflix-sync-{date}.log` to `streamarr-{date}.log`; Scheduled Removals empty-state message changed from `No <code>netflix-sync</code> tagged titles found` to `No <code>streamarr</code> tagged titles found`; Protection Manager empty-state message updated to reference `streamarr` tag
- **`app/templates/index.html`** — Scheduled Removals field-help and Protection Manager field-help updated from `netflix-sync` to `streamarr`
- **`app/templates/settings.html`** — deletion warning updated: `Only titles tagged <code>netflix-sync</code> are affected` → `Only titles tagged <code>streamarr</code> are affected`

---


## CHG-028 — 2026-04-30 — Dashboard UI: scheduled removals table and poster caching

### Additions
- **Scrollable Scheduled Removals table** — wrapped in `.removal-scroll` container (`max-height: 440px`, `overflow-y: auto`); thead is sticky so headers stay visible while scrolling
- **Actions column** in Scheduled Removals — each row now has a Protect / Unprotect button (green accent for Protect). Tautulli-protected items show a read-only "Tautulli" label instead. Clicking immediately shows "Saving…" feedback, then reloads both the schedule table and the Protection Manager panel on success
- **Top 10 poster caching** — poster URLs and status icons are now saved to `localStorage` after the first API call and applied synchronously on every subsequent page load, eliminating the delay before posters appear

### Changes
- **Removed entry-reason sub-row** from the Scheduled Removals title cell — the removal date was already shown in its own column, causing it to appear twice per row
- **Protection panel refresh on toggle** — toggling protect/unprotect from the Scheduled Removals table now also refreshes the Protection Manager panel so switching tabs immediately reflects the change

---


## CHG-027 — 2026-04-29 — Phase 7: Docs and cleanup after FlixPatrol integration

### Additions
- **FlixPatrol section in `README.md`** — documents FlixPatrol as a Top 10 source, explains configuration (country, service selector, per-service movie/TV toggles, cache duration), links to the upstream [streaming-scraper](https://github.com/dandrurymobile/streaming-scraper) repo, and notes what to do if scraping breaks

### Changes
- **`requirements.txt`** — pinned `beautifulsoup4` from `>=4.12.2` to `==4.14.3` (the version vendored into the scraper and confirmed working)
- **`README.md`** — updated Features list, How It Works, settings reference table, Settings page description, Project Structure, and Limitations to reflect FlixPatrol as a live source alongside Trakt; removed the "Netflix Top 10 (scraper)" planned entry as it is now implemented

---


## CHG-026 — 2026-04-29 — Phase 6: FlixPatrol caching, refresh button, and resilient error handling

### Additions
- **In-memory FlixPatrol cache** in `app/netflix_fetcher.py` — module-level `_fp_cache` dict keyed by country name. Each entry stores `attempt_ts` (monotonic time of last fetch attempt), `fetch_ts` (monotonic time of last *successful* fetch), `fetched_at` (wall-clock time for display), `grouped` (aggregated service data), and `error` (error string or `None`). Cache is process-scoped and survives across sync cycles
- **`bust_flixpatrol_cache()`** in `app/netflix_fetcher.py` — clears the entire cache; called by the refresh endpoint before re-fetching
- **`get_flixpatrol_cache_info(country, cache_hours)`** in `app/netflix_fetcher.py` — returns `{cached_at, age_seconds, is_stale, error}` for the given country. `is_stale` is `True` when `error` is set or data age exceeds `cache_hours`
- **`fetch_flixpatrol_fresh(country)`** in `app/netflix_fetcher.py` — always hits the network, updates the cache, and returns `(grouped, error_or_None)`. On failure, returns last known stale grouped data with an error string; error message: *"FlixPatrol data unavailable — check streaming-scraper repo for updates"*
- **`flixpatrol_cache_hours`** setting added to `DEFAULT_SETTINGS` in `app/config.py` — integer, default `6`
- **`POST /api/flixpatrol/refresh`** endpoint in `app/web.py` — busts the cache, re-fetches using the configured country, and returns `{status, error, country, services, cache}`. Status is `"ok"`, `"stale"` (fetch failed but stale data returned), or `"error"` (no data at all)
- **"Refresh now" button** (`#fpRefreshBtn`) in the FlixPatrol settings card (`app/templates/settings.html`) — sits alongside the existing "Load services" button
- **Cache status area** (`#fpCacheStatus`) in `app/templates/settings.html` — shows last fetched time (server-rendered at page load) and a yellow "Stale" badge when `is_stale` is true. Error message shown below in amber when last fetch failed
- **`flixpatrol_cache_hours` number input** in `app/templates/settings.html` — configures the cache duration (1–48 h)
- **`updateFpCacheStatus(cache)`** function in `app/static/script.js` — re-renders `#fpCacheStatus` from a cache info dict returned by any API response. Formats wall-clock timestamp using `Date.toLocaleTimeString/toLocaleDateString`
- **`.fp-stale-badge`**, **`.fp-stale-msg`**, **`.fp-cache-status`** CSS classes in `app/static/style.css` — amber badge for stale indicator; amber text for error message

### Changes
- **`_fetch_flixpatrol_items()`** in `app/netflix_fetcher.py` — now accepts `cache_hours: int = 6` parameter. Checks `attempt_ts` against `cache_hours * 3600` before deciding to use cache or call `fetch_flixpatrol_fresh()`. Logs cache hit with data age; logs stale-cache usage on error
- **`fetch_from_sources()`** in `app/netflix_fetcher.py` — new `flixpatrol_cache_hours: int = 6` keyword argument passed through to `_fetch_flixpatrol_items()`
- **`SyncService._run()`** in `app/sync_service.py` — reads `flixpatrol_cache_hours` from settings (defaults to `6`), passes to `fetch_from_sources()`
- **`flixpatrol_preview` endpoint** in `app/web.py` — now calls `fetch_flixpatrol_fresh()` (always fresh, updates cache) instead of calling the scraper directly. Response includes a `"cache"` key with `{cached_at, age_seconds, is_stale, error}`
- **`settings_page()` route** in `app/web.py` — calls `get_flixpatrol_cache_info()` and formats `cached_at` as `%H:%M %d/%m/%Y`; passes `flixpatrol_cache` dict to template
- **`post_settings()` in `app/web.py`** — `flixpatrol_cache_hours` added to `normalized` dict and persisted
- **`fpLoadBtn` click handler** in `app/static/script.js` — calls `updateFpCacheStatus(data.cache)` after a successful load to reflect fresh cache state in the UI
- **Refresh button handler** in `app/static/script.js` — disables both Load and Refresh buttons during the request; updates cache status and shows success / stale / error feedback via `setTestResult`

---


## CHG-025 — 2026-04-29 — Phase 5: Per-service movie/TV type toggles

### Additions
- **`flixpatrol_service_types`** setting added to `DEFAULT_SETTINGS` in `app/config.py` — dict mapping service key to allowed types list (e.g. `{"netflix": ["movie"], "disney_plus": ["movie", "series"]}`). Default `{}` means both types for all services
- **Per-service Movies / TV checkboxes** in the FlixPatrol service grid — each service row now shows two type checkboxes beneath the service enable label. Unchecked services dim the type toggles (CSS `:has()` rule). Rendered by the updated `renderFlixPatrolServices()` in `app/static/script.js`
- **`.fp-service-row`**, **`.fp-type-toggles`**, **`.fp-type-label`** CSS classes in `app/static/style.css` — wrap each grid item in a column-flex container; type toggles sit below the service label with `padding-left` aligned to the service name; disabled-service opacity via `:not(:has(.fp-service-cb:checked)) .fp-type-toggles { opacity: 0.45 }`

### Changes
- **`_fetch_flixpatrol_items()`** in `app/netflix_fetcher.py` — accepts new `service_types: dict` parameter. For each service, checks `service_types.get(key)`: `None` → both types; list → only listed types included. Log line extended with type-filter info
- **`fetch_from_sources()`** in `app/netflix_fetcher.py` — new `flixpatrol_service_types: dict | None = None` keyword argument passed through to `_fetch_flixpatrol_items()`
- **`SyncService._run()`** in `app/sync_service.py` — reads `flixpatrol_service_types` from settings (validates it is a dict, falls back to `{}`), passes to `fetch_from_sources()`
- **`post_settings()`** in `app/web.py` — parses `flixpatrol_service_types` from JSON payload: validates it is a dict, whitelists type values to `"movie"` / `"series"`, preserves stored value if payload key is absent
- **`renderFlixPatrolServices(services, checkedKeys, serviceTypes)`** in `app/static/script.js` — third parameter `serviceTypes = {}`. Wraps each service in a `.fp-service-row` div; appends a `.fp-type-toggles` div with two `.fp-type-label` / `.fp-type-cb` checkboxes (`data-service`, `data-type` attributes). Default checked state: both types unless `serviceTypes[key]` specifies a subset
- **Form submit handler** in `app/static/script.js` — collects `flixpatrol_service_types` dict from `.fp-type-cb` checkboxes (scoped to `.fp-service-row` for reliable sibling lookup) and adds to payload
- **Page-load restoration** in `app/static/script.js` — replaces DOM-query approach; reads `data-saved-services` and `data-saved-service-types` JSON attributes from `#fpServiceList` (embedded by Jinja) and passes `savedServiceTypes` as third arg to `renderFlixPatrolServices()`
- **"Load services" click handler** in `app/static/script.js` — captures current type selections before re-render, merges with persisted base (persisted → overridden by current UI), passes merged dict to `renderFlixPatrolServices()`
- **`#fpServiceList` div** in `app/templates/settings.html` — gains `data-saved-services` and `data-saved-service-types` attributes rendered by Jinja (`| tojson`)
- **`.fp-service-grid`** min column width bumped from `180px` to `200px` in `app/static/style.css` to accommodate type toggles

## Phase 4 — Country selector (shipped within Phase 2 / CHG-022 and Phase 3 / CHG-024)

The `flixpatrol_country` setting, `FLIXPATROL_COUNTRIES` import, country dropdown, and country validation in `post_settings()` were all delivered as part of Phase 2 and Phase 3. No separate CHG entry.

---

## CHG-024 — 2026-04-29 — Phase 3: FlixPatrol service selector with live preview

### Additions
- **`GET /api/flixpatrol/preview`** endpoint in `app/web.py` — accepts an optional `?country=` query param (falls back to `flixpatrol_country` setting). Calls `flixpatrol_fetch()`, groups results via `group_by_source_and_type()`, and returns a JSON array of service objects: `key`, `label`, `movie_count`, `series_count`, `sample_movies` (top 3), `sample_series` (top 3). No Radarr/Sonarr interaction
- **FlixPatrol settings card** in `app/templates/settings.html` — replaces the static Phase 2 placeholder. Contains: enable checkbox, country dropdown, "Load services" button, dynamic service grid rendered by JS, and select-all/none toggles. Service checkboxes use `name="flixpatrol_services"` and are persisted via the existing settings save flow
- **`renderFlixPatrolServices(services, checkedKeys)`** in `app/static/script.js` — renders the service grid from preview API response. On page load, previously saved service keys are rendered as minimal checkboxes (no counts) so selections survive a page reload without requiring a re-fetch. On "Load services" click, live data replaces them with movie/series counts
- **FlixPatrol service selector CSS** in `app/static/style.css` — `.fp-preview-row`, `.fp-service-grid`, `.fp-service-item`, `.fp-service-cb`, `.fp-service-meta`, `.fp-service-name`, `.fp-service-counts`, `.fp-count-badge--movie`, `.fp-count-badge--series`, `.fp-toggle-row`

### Changes
- `settings_page()` in `app/web.py` now passes `flixpatrol_countries=sorted(FLIXPATROL_COUNTRIES.keys())` to the template (imported from `app/scraper/sources/streaming`)
- `post_settings()` in `app/web.py`: `"flixpatrol"` added to sources whitelist (replacing `"netflix"` stub); `flixpatrol_country` and `flixpatrol_services` normalised and persisted; `flixpatrol_services` excluded from scalar form loop
- Form submit handler in `app/static/script.js`: `flixpatrol_services` collected with `getAll()` and skipped in scalar loop


## CHG-023 — 2026-04-29 — Fix: lookup failures no longer crash the sync run

### Fixes
- `lookup_movie()` in `app/radarr_client.py` — wrapped the `_get()` call in a try/except. A transient Radarr error (e.g. 503 Service Unavailable) now logs a warning and returns `None`, which `add_movie()` already handles by skipping that title. Previously the exception propagated up through `SyncService._run()` and aborted the entire sync mid-run, leaving the remaining titles unprocessed
- `lookup_series()` in `app/sonarr_client.py` — identical fix applied for consistency. Same failure mode, same fix


## CHG-022 — 2026-04-29 — Phase 2: FlixPatrol settings wiring and UI card

### Additions
- **FlixPatrol settings card** in `app/templates/settings.html` — contains: source enable checkbox (`sources = flixpatrol`), country dropdown populated from `FLIXPATROL_COUNTRIES` (57 countries + Worldwide, sorted alphabetically), and a field-help note that per-service filtering is coming in Phase 3
- **`flixpatrol_countries`** template variable passed from `settings_page()` in `app/web.py` — `sorted(FLIXPATROL_COUNTRIES.keys())` from `app/scraper/sources/streaming.py`

### Changes
- `settings_page()` in `app/web.py` now imports `COUNTRIES as FLIXPATROL_COUNTRIES` from `app/scraper/sources/streaming` and passes `flixpatrol_countries` to the template (`app/web.py`)
- `post_settings()` in `app/web.py`:
  - `"flixpatrol"` added to the sources whitelist (previously only `"trakt"` was accepted; `"netflix"` stub removed)
  - `flixpatrol_country` normalised as a scalar string; validated against `FLIXPATROL_COUNTRIES` keys — falls back to the stored value if an unknown country is submitted
  - `flixpatrol_services` handled as a multi-value list (same pattern as `sources` and `netflix_top_countries`); excluded from the scalar `formData.entries()` loop
  - Both new keys written to `normalized` dict and persisted via `settings.update()`
- Form submit handler in `app/static/script.js`:
  - `payload.flixpatrol_services = formData.getAll("flixpatrol_services")` added alongside the existing `sources` and `netflix_top_countries` multi-value collection
  - `flixpatrol_services` skipped in the scalar `formData.entries()` loop to prevent double-submission


## CHG-021 — 2026-04-29 — Phase 1: FlixPatrol scraper integration (streaming-scraper vendored)

### Additions
- **`app/scraper/`** — new package vendored from https://github.com/dandrury94-hash/streaming-scraper (Option A: files copied directly, no submodule or pip install dependency)
  - `app/scraper/core/models.py` — `MediaItem` dataclass (`title`, `type`, `source`, `rank`)
  - `app/scraper/core/aggregator.py` — `aggregate(sources)` and `group_by_source_and_type(items)` utilities
  - `app/scraper/sources/streaming.py` — `fetch(country)` scraper and `COUNTRIES` dict (57 countries + Worldwide). Fetches `https://flixpatrol.com/top10/streaming/{country}/`, parses service blocks via BeautifulSoup, deduplicates within each `(source, type)` group, caps to top 10, and re-ranks from 1. Uses `urllib.request` — no new dependencies beyond `beautifulsoup4` which was already present
  - `app/scraper/__init__.py`, `app/scraper/core/__init__.py`, `app/scraper/sources/__init__.py` — package markers
- **`_fetch_flixpatrol_items(country, services)`** private helper in `app/netflix_fetcher.py` — calls `flixpatrol_fetch()`, runs result through `aggregate()` and `group_by_source_and_type()`, applies optional service key whitelist, and converts `MediaItem` objects to the existing `{"title", "type", "source"}` dict format consumed by `SyncService._run()`
- **`"flixpatrol"` source** added as a valid option in `fetch_from_sources()` (`app/netflix_fetcher.py`). Trakt path is entirely unchanged
- **`flixpatrol_country`** setting added to `DEFAULT_SETTINGS` in `app/config.py` — string, default `"United Kingdom"`. Full country name matching the `COUNTRIES` dict in `app/scraper/sources/streaming.py`
- **`flixpatrol_services`** setting added to `DEFAULT_SETTINGS` in `app/config.py` — list of service keys (e.g. `["netflix", "disney_plus"]`). Empty list (default) means all available services are included

### Changes
- `fetch_from_sources()` signature extended with two new keyword arguments: `flixpatrol_country` (default `"United Kingdom"`) and `flixpatrol_services` (default `[]`). Existing call sites with positional args are unaffected (`app/netflix_fetcher.py`)
- `SyncService._run()` now reads `flixpatrol_country` and `flixpatrol_services` from settings and passes them to `fetch_from_sources()`. No other sync logic changed (`app/sync_service.py`)
- Import paths in vendored scraper files changed from `core.models` / `core.aggregator` to `app.scraper.core.models` / `app.scraper.core.aggregator` to resolve correctly within the NMS package structure

### Infrastructure
- `beautifulsoup4>=4.12.2` already present in `requirements.txt` — no new dependencies added
- FlixPatrol source is opt-in: it activates only when `"flixpatrol"` is added to the `sources` list in settings. Default remains `["trakt"]`, so existing deployments are unaffected until explicitly configured


## CHG-020 — 2026-04-28 — Multi-source trending fetch

### Added
- `fetch_from_sources(sources, country_codes, client_id)` in `app/netflix_fetcher.py` — iterates a list of enabled source names, delegates to the appropriate fetcher, and deduplicates results by `(title.lower(), type)`. Returns a list of dicts: `{"title": str, "type": "movie"|"series", "source": str}`
- `_fetch_trakt_items(country_codes, client_id)` private helper — wraps the existing `fetch_netflix_top_10_for_countries()` call and converts its `(movies, series)` tuple into the unified dict format with `source: "trakt"`
- `"sources": ["trakt"]` added to `DEFAULT_SETTINGS` (`app/config.py`); persisted to `settings.json`
- **Enabled sources** checkbox group in the Trakt settings card — currently exposes Trakt only; Netflix is handled in the backend but not surfaced in the UI until implemented (`app/templates/settings.html`)

### Changed
- `SyncService._run()` now reads `sources` from settings and calls `fetch_from_sources()` instead of `fetch_netflix_top_10_for_countries()` directly. `netflix_movies` and `netflix_series` lists are extracted from the merged result. Timing log line renamed from `trakt_fetch` to `source_fetch` (`app/sync_service.py`)
- `POST /api/settings` handles `sources` as a multi-value list (same pattern as `netflix_top_countries`): values are whitelisted to `["trakt", "netflix"]` (`app/web.py`)
- Settings form JS handler collects `sources` with `formData.getAll("sources")` and skips the key in the scalar loop, matching the existing `netflix_top_countries` pattern (`app/static/script.js`)

---

## CHG-019 — 2026-04-28 — Centralised media state, bulk-fetch top10, and protection manager improvements

### Added
- **`app/media_state.py`** — new module with `MediaStateEntry` TypedDict (`title`, `type`, `radarr_id`, `sonarr_id`, `in_library`, `has_file`, `protected`, `protection_source`, `eligible_for_deletion`, `grace_started`, `grace_expires`, `days_until_deletion`, `in_grace`, `days_remaining`, `date_added`, `removal_date`, `status`, `reason`) and `build_media_state()` function. Accepts tagged movie/series records, sync log state, grace periods, protected sets, and retention settings; returns a `dict[str, MediaStateEntry]` keyed by lowercase title. All computation is in-memory — no API calls
- `_fetch_media_state()` closure in `create_app()`: calls `get_tagged_movies("netflix-sync")` and `get_tagged_series("netflix-sync")`, reads sync log state, and delegates to `build_media_state()`. Shared by `/api/removal-schedule` and `/api/protection-state` (`app/web.py`)
- Search input above the Protection Manager columns — live client-side filter on keyup, case-insensitive title match (`app/static/script.js`, `app/static/style.css`)
- Select-all checkboxes in each column header; **Unprotect Selected** and **Protect Selected** batch buttons that POST to `/api/overrides` sequentially then refresh the panel. Tautulli-protected and "both"-protected items have their checkboxes disabled (`app/static/script.js`)
- `.entry-reason` — small muted text line displayed below title in the Scheduled Removals table and in each Protection Manager entry (`app/static/style.css`)
- `.prot-search`, `.prot-search-wrap`, `.prot-sel-all`, `.prot-entry-cb`, `.prot-batch-btn`, `.prot-batch-btn--protect`, `.prot-count`, `.prot-count--protected`, `.prot-count--unprotected`, `.prot-action-btn--protect` styles (`app/static/style.css`)
- Per-phase `[timing]` log lines in `SyncService._run()` using `time.monotonic()`: `trakt_fetch`, `tautulli_fetch`, `radarr_bulk_fetch`, `radarr_add_loop`, `sonarr_bulk_fetch`, `sonarr_add_loop`. Deletion run logged as `[timing] deletion_run: Xs` in `run_once()` (`app/sync_service.py`)

### Changed
- `/api/removal-schedule` refactored to call `_fetch_media_state()` and return all entries sorted by `days_remaining`. Adds `reason` field to each entry (`app/web.py`)
- `/api/protection-state` refactored to call `_fetch_media_state()` and split by `protected` flag. Adds `reason` to each entry; `protection_source` now correctly returns `"both"` when a title is protected by both Tautulli and a manual override (`app/web.py`)
- `/api/top10-status` refactored: calls `get_all_movies()` and `get_all_series()` once per request and builds title→record maps, eliminating per-title `get_movie_by_id()` / `get_series_by_id()` / `lookup_movie()` / `lookup_series()` calls. `hasFile` and `episodeFileCount` are read directly from the library record, fixing the available/pending status bug. Poster extracted from the library record's `images` array; `"will_add"` titles return `poster: null` (`app/web.py`)
- `renderSchedule()` updated to show `item.reason` as `.entry-reason` below the title (`app/static/script.js`)
- `renderProtectionState()` rewritten: search input, select-all, batch actions, reason below title, "both" source badge (styled as Tautulli). Entry construction extracted to `_makeEntry()` helper (`app/static/script.js`)
- `.prot-entry` changed to `align-items: flex-start` to accommodate multi-line meta content (`app/static/style.css`)
- Tautulli fetch restructured from a ternary to an `if` block to allow timing instrumentation (`app/sync_service.py`)

### Removed
- `_resolve_date()` and `_grace_fields()` module-level helpers removed from `app/web.py` — logic now lives in `build_media_state()`
- Per-title `get_movie_by_id()`, `get_series_by_id()`, `lookup_movie()`, `lookup_series()` calls removed from `/api/top10-status`

---

## CHG-018 — 2026-04-28 — UK timestamp format on Last Sync

### Changed
- `SyncLog.set_last_sync()` now stores the timestamp using `strftime("%H:%M %d/%m/%Y")` instead of `.isoformat(timespec="seconds")`, producing e.g. `07:24 28/04/2026`. Timezone is the server's local time (`app/sync_log.py`)
- `index()` route now reformats the `timestamp` field from the stored sync record before passing it to the template. `_fmt_timestamp()` parses ISO 8601 strings (`%Y-%m-%dT%H:%M:%S` and `%Y-%m-%dT%H:%M`) and converts them to `%H:%M %d/%m/%Y`; any already-formatted or unrecognised string is passed through unchanged. This means existing stored ISO timestamps display in UK format immediately without requiring a new sync (`app/web.py`)

---

## CHG-017 — 2026-04-28 — Status & Actions card redesign and inline sync progress

### Changed
- **Status & Actions card** restructured with a four-section flex layout (`display:flex; flex-direction:column; justify-content:space-between`) so the card fills the same height as the adjacent Top 10 cards. Bold dividers (`.card-divider`, `rgba(255,255,255,0.13)`) separate each section; integration items and sync-stat rows use lighter CSS `border-bottom` rules (`rgba(255,255,255,0.06)` / existing `rgba(255,255,255,0.05)`) (`app/templates/index.html`, `app/static/style.css`)
- "Integration status" rendered as a small-caps section label (`.sac-section-label`) above the integration list. "Last Sync" row is a flex row with the timestamp right-aligned (`app/templates/index.html`, `app/static/style.css`)
- Sync progress bar replaced with an **inline button fill**: the button spans the full card width with left-aligned text. During sync, `--sync-pct` CSS custom property drives a `::before` fill that sweeps left-to-right from 0 → 90% (animated) then jumps to 100% on success. `.syncing` class changes button background to `rgba(77,140,255,0.22)` while the `::before` gradient overlays the filled portion. On failure, `.sync-error` adds a `⚠` via `::after` on the right edge, auto-cleared after 3 s (`app/static/script.js`, `app/static/style.css`)
- Separate `#syncProgress` / `#syncProgressBar` divs removed; `.sync-progress*` CSS classes removed (`app/templates/index.html`, `app/static/style.css`)

---

## CHG-016 — 2026-04-28 — Sync progress bar with duration estimate

### Changed
- `SyncService.run_once()` now records wall time around `_run()` using `time.monotonic()` and adds `duration_seconds` (int) to the result dict. `set_last_sync()` is now called in `run_once()` (after duration is known) rather than inside `_run()` (`app/sync_service.py`)
- `POST /api/sync` reads `duration_seconds` from the previous sync via `sync_log.get_last_sync()` before running, and returns `estimated_seconds` (defaulting to 60 if no history exists) alongside the sync result (`app/web.py`)
- Sync button handler rewritten — removes `syncResult` text box entirely. On click: disables button, sets text to "Syncing…", shows progress bar and animates 0 → 90% over `syncEstimatedSeconds` via `setInterval` every 500 ms. On success: jumps to 100%, waits 600 ms, hides bar, restores button, reloads page. On failure: sets error colour for 1500 ms then resets button. `syncEstimatedSeconds` is seeded from `data-estimated` on the button element and updated from each response (`app/static/script.js`)
- `const syncResult` variable removed from `DOMContentLoaded` scope (`app/static/script.js`)

### Added
- `<div id="syncProgress">` / `<div id="syncProgressBar">` injected below the sync button. `data-estimated` attribute on the button seeds the initial animation duration from the last sync's recorded time (`app/templates/index.html`)
- "Runs immediately alongside the scheduled interval." field-help paragraph above the sync button (`app/templates/index.html`)
- `.sync-progress` — 4 px tall, full-width, `rgba(255,255,255,0.08)` track, `overflow: hidden` (`app/static/style.css`)
- `.sync-progress-bar` — gradient fill matching the primary button, `transition: width 0.5s linear` (`app/static/style.css`)
- `.sync-progress-bar--error` — solid `#e05252` fill for failure state (`app/static/style.css`)

### Removed
- `<div id="syncResult">` text status box removed from the Actions card (`app/templates/index.html`)

---

## CHG-015 — 2026-04-28 — Addition history in History tab

### Added
- `GET /api/addition-history` endpoint: reads `SyncLog.get_entries()`, filters to entries with `date_added` within the last 7 days, deduplicates by title (most recent entry kept), and returns `{"additions": [...]}` sorted newest-first. Uses the existing sync log — no new storage or dependencies (`app/web.py`)
- **Recently Added** table at the top of the History tab, showing title, type, date added, and source for each unique title added in the last 7 days. Loaded asynchronously on tab reveal (`app/templates/index.html`, `app/static/script.js`)
- `loadAdditionHistory(tbody)` and `renderAdditionHistory(tbody, additions)` JS functions (`app/static/script.js`)

---

## CHG-014 — 2026-04-28 — Dashboard layout compaction

### Changed
- Integration Status, Last Sync Summary, and Actions cards merged into a single **Status & actions** card, reducing the grid from three narrow cards to one. Content is separated by `.setting-divider` rules (`app/templates/index.html`)
- Dashboard page subtitle updated to reflect the removed Protected Titles section

### Removed
- **Protected Titles** card removed from the Dashboard tab. Full protection management is available via the dedicated Protection tab (`app/templates/index.html`)

---

## CHG-013 — 2026-04-28 — Poster art on Top 10 panels

### Changed
- `GET /api/top10-status` response shape updated: each title value is now an object `{"status": "...", "poster": "<url>|null"}` instead of a plain status string. The `poster` field contains the `remoteUrl` of the first image with `coverType == "poster"` from the Radarr/Sonarr lookup stub, or `null` if none is found. No new API calls are introduced — the poster URL is extracted from the same lookup response already used for status determination (`app/web.py`)
- `loadTop10Status()` updated to read the new object shape: reads `item.status` for icon rendering (behaviour unchanged) and `item.poster` for the new thumbnail. When a poster URL is present, sets `--poster-url` as a CSS custom property on the `<li>` element and adds the class `top10-item--has-poster` (`app/static/script.js`)
- Poster thumbnail repositioned to the **left** of the title; a 1 px faint vertical divider (`::after` pseudo-element, `rgba(255,255,255,0.07)`) separates it from the title and status icon. `padding-left: 44px` ensures text does not overlap (`app/static/style.css`)

### Added
- `.top10-item--has-poster` CSS rule: `position: relative`, `overflow: hidden`, `padding-left: 44px`. `::before` poster thumbnail at left edge, 36×54 px, `opacity: 0.55`. `::after` 1 px divider at `left: 36px`, full height. Missing or broken images fail silently (`app/static/style.css`)
- `_extract_poster(images)` helper function returns the `remoteUrl` of the first poster-type image or `None` (`app/web.py`)
- "How It Works" section added to README covering sync, grace period, and poster art sourcing
- Poster art bullet added to Features list; poster sourcing note added to Radarr and Sonarr rows in the configuration table (`README.md`)

---

## CHG-012 — 2026-04-27 — Protection manager

### Added
- `GET /api/protection-state` endpoint: fetches all `netflix-sync` tagged titles from Radarr and Sonarr in one bulk call each, determines protection status from the last Tautulli sync result and the manual overrides set, and returns `{"protected": [...], "unprotected": [...]}` sorted alphabetically. Failures in either service are caught and skipped without affecting the other (`app/web.py`)
- **Protection tab** in the top navigation bar; clicking it switches to the protection manager panel client-side (`app/templates/base.html`, `app/templates/index.html`, `app/static/script.js`)
- **Protection manager panel** — two-column layout (Protected / Not Protected) loaded asynchronously from `GET /api/protection-state`:
  - Each protected item shows title, type badge, source badge (Tautulli or Manual), and either an **Unprotect** button (manual) or a "Tautulli protected" lock label (Tautulli — unprotection not allowed)
  - Each unprotected item shows title, type badge, and a **Protect** button
  - Protect / Unprotect actions POST to the existing `/api/overrides` endpoint and refresh the panel in-place (`app/static/script.js`)
- `loadProtectionState(container)`, `renderProtectionState(container, data)`, `handleProtectionToggle(btn, title, protect, container)` JS functions (`app/static/script.js`)
- Protection manager CSS: `.protection-manager`, `.prot-col-header`, `.prot-entry`, `.prot-entry-meta`, `.prot-source-badge`, `.prot-lock-label`, `.prot-action-btn` (`app/static/style.css`)

---

## CHG-011 — 2026-04-27 — Pushover notifications, automatic deletion, and removal history

### Added
- **Pushover notifications** (`app/pushover_client.py`):
  - `PushoverClient` class wrapping the Pushover API (`https://api.pushover.net/1/messages.json`)
  - `is_enabled()` — returns `True` only when `pushover_enabled`, `pushover_user_key`, and `pushover_api_token` are all set
  - `send(title, message, priority)` — never raises; logs a warning on delivery failure
  - Notifications sent for: titles added during sync, per-title deletion, and sync errors (priority 1)
  - `POST /api/test/pushover` endpoint for in-UI delivery test (`app/web.py`)
  - Pushover card in Settings with enable checkbox, user key, API token, and test button (`app/templates/settings.html`)
- **Automatic deletion with grace period** (`app/sync_service.py`):
  - `SyncService.run_deletions()` — runs after every sync when `deletion_enabled` is `True`
  - Only processes titles tagged `netflix-sync` in Radarr / Sonarr; protected titles are never deleted
  - Two-phase flow: title first enters a grace period (`sync_log.start_grace_period`), then is deleted once `grace_period_days` have elapsed
  - `grace_period_days` and `deletion_enabled` settings added to `DEFAULT_SETTINGS` and `ENV_VAR_TO_SETTING` (`app/config.py`)
  - Deletion checkbox and grace-period input added to the Retention & sync settings card with a `⚠️` warning (`app/templates/settings.html`)
- **Grace period tracking** (`app/sync_log.py`):
  - `grace_periods` dict added to persisted state; migrated in on load if absent
  - `start_grace_period(title, media_type)` — idempotent; only records start date on first call
  - `get_grace_periods()` — returns the full dict
  - `clear_grace_period(title)` — removes the entry after successful deletion
- **Removal history** (`app/removal_history.py`):
  - `RemovalHistory` class persisting deletions to `/config/removal_history.json`
  - `log_removal(title, media_type, reason, was_watched)` — appends an entry and saves
  - `get_recent(days)` — returns entries within the given window (default 180 days)
  - `_save()` prunes entries older than 180 days before writing
  - `GET /api/removal-history` endpoint (`app/web.py`)
- **History tab** (`app/templates/index.html`, `app/templates/base.html`, `app/static/script.js`):
  - History tab added to the top navigation bar alongside Dashboard and Logs
  - 5-column table (Title, Type, Date removed, Reason, Watched) loaded asynchronously
  - `loadRemovalHistory(tbody)` and `renderHistory(tbody, history)` functions in `script.js`
- **Scheduled removals table expanded** (`app/templates/index.html`, `app/static/script.js`):
  - Two new columns: **Grace expires** and **Days to delete**
  - `Days to delete` colour-coded: red (≤ 2 days), yellow (≤ 5 days), green (> 5 days)
  - "Due" label shown when `days_until_deletion` ≤ 0
- **Weekly deletion preview** (`app/main.py`):
  - `run_weekly_preview()` daemon thread wakes on the next Saturday at 05:00
  - Scans tagged titles with upcoming removal dates within 7 days and sends a Pushover summary
  - Silently skips if Pushover is not enabled
- **Module-level `_resolve_date()` helper** (`app/sync_service.py`) — resolves a title's add date from the sync log, the Radarr/Sonarr API `added` field, or a fallback date, in that priority order

### Changed
- `SyncService.__init__` now accepts `removal_history: RemovalHistory` and instantiates `PushoverClient` (`app/sync_service.py`)
- `create_app` now accepts `removal_history` parameter and passes it to the removal-history endpoint (`app/web.py`)
- `main()` instantiates `RemovalHistory` and passes it to both `SyncService` and `create_app` (`app/main.py`)
- Settings form `post_settings` adds a `to_bool()` helper for checkbox fields (`deletion_enabled`, `pushover_enabled`) (`app/web.py`)
- `_SENSITIVE_KEYS` extended with `pushover_user_key` and `pushover_api_token` (`app/web.py`)
- Scheduled removals table colspan updated from 6 to 8 for empty-state rows (`app/static/script.js`)
- `.setting-checkbox` and `.setting-divider` styles added for the new settings form layout (`app/static/style.css`)

---

## CHG-010 — 2026-04-27 — Bug fixes from CHG-009

### Fixed
- `SyncService._run()`: `radarr_cache` and `sonarr_cache` were only assigned inside `if mode != "disabled"` blocks but referenced in the `enabled` / `read` branches below, causing a potential `NameError` when either integration is disabled. Both are now initialised to `{}` before the conditional blocks (`app/sync_service.py`)
- Topnav Dashboard and Logs links had no active class applied on initial page load — active state was only set by the click handler. On `DOMContentLoaded`, the Dashboard link now receives the `active` class when the page is the index route. The hardcoded Jinja active-class expression and the empty `class=""` attribute have been removed from both tab-target links in the template, as active state is managed entirely by JS for those links (`app/static/script.js`, `app/templates/base.html`)

---

## CHG-009 — 2026-04-27 — Sync performance, status accuracy, and Logs nav

### Fixed
- `/api/top10-status` now fetches the real library record (`GET /api/v3/movie/{id}` / `GET /api/v3/series/{id}`) when a title is found in Radarr/Sonarr, instead of relying on the search-stub response which does not return accurate `hasFile` / `episodeFileCount` data (`app/web.py`, `app/radarr_client.py`, `app/sonarr_client.py`)

### Added
- `RadarrClient.get_all_movies()` — fetches full library in one call; returns `[]` and logs a warning on failure (`app/radarr_client.py`)
- `RadarrClient.get_movie_by_id(movie_id)` — fetches a single library record by Radarr ID (`app/radarr_client.py`)
- `SonarrClient.get_all_series()` — fetches full library in one call; returns `[]` and logs a warning on failure (`app/sonarr_client.py`)
- `SonarrClient.get_series_by_id(series_id)` — fetches a single library record by Sonarr ID (`app/sonarr_client.py`)
- **Logs** added to the main top navigation bar as a peer of Dashboard and Settings; clicking it switches the panel client-side without a page reload (`app/templates/base.html`, `app/templates/index.html`, `app/static/script.js`)

### Changed
- `RadarrClient.add_movie` and `SonarrClient.add_series` accept an optional `library_cache` dict (normalised lowercase title → record); if the title is found with a non-zero id the method returns `False` immediately without a network call (`app/radarr_client.py`, `app/sonarr_client.py`)
- `SyncService._run()` calls `get_all_movies()` / `get_all_series()` once per sync run (when the mode is not `disabled`) and passes the resulting cache into all `add_movie` / `add_series` calls, eliminating up to 20 sequential existence-check requests per sync (`app/sync_service.py`)
- Read-mode existence check in `_run()` now uses the bulk cache directly instead of calling `lookup_movie` / `lookup_series` per title (`app/sync_service.py`)
- In-page tab switcher (Dashboard / Logs buttons) removed from the dashboard page; Logs is now in the topnav (`app/templates/index.html`)
- `run_worker` in `main.py` already reads `run_interval_seconds` after each sync run; added inline comment making this explicit (`app/main.py`)

---

## CHG-008 — 2026-04-27 — Dashboard improvements

### Added
- Tab navigation bar on dashboard with **Dashboard** and **Logs** tabs; all log content moved to the Logs tab, freeing the main grid from the log panel (`app/templates/index.html`, `app/static/script.js`, `app/static/style.css`)
- Log output dynamically fills available screen height via `calc(100vh - 370px)` with a 300 px minimum (`app/static/style.css`)
- Status icons for Trakt Top 10 Movies and Series panels:
  - ⏳ Pending (monitored, no file)
  - ✅ Available (file downloaded)
  - ➕ Will Add (not in library)
  - ➖ Disabled (integration off)
  - Loaded asynchronously with tooltip labels (`app/static/script.js`, `app/templates/index.html`)
- `GET /api/top10-status` endpoint querying Radarr/Sonarr for per-title status; skips individual failures (`app/web.py`)

### Changed
- Increased log scrollback buffer from 100 to 2000 lines (`app/web.py`)

---

## CHG-007 — 2026-04-27 — Test connection buttons

### Added
- Test connection buttons for Radarr, Sonarr, and Tautulli in Settings (`app/templates/settings.html`)
- `POST /api/test/radarr` and `/api/test/sonarr` endpoints:
  - Validate URL + API key
  - Return quality profiles and root folders on success (`app/web.py`)
- `POST /api/test/tautulli` endpoint returning Plex server name (`app/web.py`)
- Dynamic UI replacement of quality profile/root folder inputs with populated dropdowns (`app/static/script.js`)
- Clear connection feedback:
  - `✅ Connected`
  - `❌ <reason>` with specific error handling (`app/static/script.js`, `app/static/style.css`)
- Support for `__REDACTED__` sentinel resolving to stored API key (`app/web.py`)

### Changed
- Improved UX for integration setup via inline validation and dynamic field updates

### Infrastructure
- Added shared helpers `_resolve_test_key`, `_exc_msg`, `_test_arr`
- Added `import requests as _requests` alias (`app/web.py`)

---

## CHG-006 — 2026-04-27 — Live log feed

### Added
- `GET /api/logs` endpoint returning last 100 log lines (`app/web.py`)
- `POST /api/logs/clear` endpoint to truncate log file (`app/web.py`)
- `_tail_file(path, n)` helper for efficient log reading (`app/web.py`)
- Live log panel with:
  - Polling every 3 seconds
  - Colour-coded levels
  - Auto-scroll behavior (`app/templates/index.html`, `app/static/script.js`, `app/static/style.css`)
- Log controls:
  - Pause/Resume with status badge
  - Copy to clipboard
  - Download logs as `.log`
  - Clear logs (`app/static/script.js`)
- Monospace, selectable, wrapped log output (`app/static/style.css`)

### Infrastructure
- Added `RotatingFileHandler`:
  - `/config/app.log`
  - 5 MB max, 3 backups (`app/main.py`)
- Unified logging format across handlers (`app/main.py`)
- Added `LOG_PATH` config with env override (`app/config.py`)

---

## CHG-005 — 2026-04-27 — Dashboard features

### Added
- Integration status panel (Radarr, Sonarr, Tautulli) with colour indicators (`app/templates/index.html`, `app/static/style.css`)
- Trakt Top 10 movies and series panels (`app/templates/index.html`)
- Import preview panel (added / would-add / already-in-library states)
- `netflix-sync` tagging system for Radarr/Sonarr:
  - Auto-created if missing
  - Graceful fallback (`app/radarr_client.py`, `app/sonarr_client.py`)
- `get_tagged_movies` / `get_tagged_series` retrieval methods
- Tautulli protection list with manual override controls
- Manual override persistence via `/config/manual_overrides.json`
- `POST /api/overrides` endpoint
- Scheduled removal table with:
  - Date added
  - Removal date
  - Protection status
  - Urgency colour coding
- `GET /api/removal-schedule` endpoint
- Last sync summary card
- Sync log stored in `/config/sync_log.json`
- Auto-refresh after manual sync

### Infrastructure
- `SyncLog` class (thread-safe)
- `ManualOverrides` class (thread-safe)
- `SyncService` integration with logging and last-sync state
- App wiring updates (`create_app`, routes)

---

## CHG-004 — 2026-04-27 — sync_service review fixes

### Fixed
- Corrected `radarr_mode` and `sonarr_mode` values (`read_only` → `read`)
- Added missing `tautulli_mode` documentation entry

### Changed
- Simplified `protected_titles` type annotation

---

## CHG-003 — 2026-04-27 — Redact sensitive fields in settings UI

### Security
- API key/password fields now use `type="password"` with `__REDACTED__` sentinel
- Sentinel preserves stored values unless explicitly changed
- Sensitive fields redacted in `GET /api/settings`

### Added
- Added missing `web_password` input field

---

## CHG-002 — 2026-04-27 — README review fixes

### Fixed
- Corrected "Daily sync" → "Scheduled sync"
- Removed inaccurate retention behavior claims
- Fixed Docker bind mount example
- Added missing section separator

### Added
- Added `CHANGELOG.md` to repo structure
- Expanded configuration table
- Added Trakt Client ID setup instructions

---

## CHG-001 — 2026-04-27 — Code review fixes

### Security
- Ignored `config/settings.json`
- Added `settings.json.example`
- Moved API keys to headers
- Added optional Basic Auth for web UI

### Fixed
- Removed broken `fetch_netflix_top_10` call
- Fixed incorrect `tvdbId` fallback

### Performance
- Replaced full-library scans with direct lookup calls

### Thread Safety
- Added locks to `SettingsStore` and `SyncService`
- Shared `SyncService` instance across threads

### Changed
- Replaced deprecated datetime usage
- Improved error logging in settings loader
- Removed redundant environment checks
- Cleaned unused config alias

### Added
- Country-based Trakt fetch with deduplication
- Switched to `waitress` WSGI server
- Added missing CSS class

### Documentation
- Corrected README data source (Netflix → Trakt)
- Removed unimplemented features
- Documented Basic Auth and setup steps
- Cleaned docker-compose config