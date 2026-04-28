# Backend Rules

## Architecture

- web.py → API routes only, no business logic
- sync_service.py → sync + lifecycle logic
- media_state.py → unified state model
- radarr_client.py / sonarr_client.py → external API calls only
- sync_log.py, manual_overrides.py, removal_history.py → persistence

## Core Model

All endpoints must derive from build_media_state(). Never recompute protection, deletion eligibility, or status independently per endpoint.

Each MediaStateEntry contains: title, type, radarr_id, sonarr_id, in_library, has_file, protected, protection_source, eligible_for_deletion, grace_started, grace_expires, days_until_deletion, in_grace, days_remaining, date_added, removal_date, status, reason.

## Performance — STRICT

Never call lookup_movie, lookup_series, or get_*_by_id inside a loop.
Always fetch full libraries once with get_all_movies() / get_all_series().
Always build dict maps for O(1) lookups.

## Deletion

Only netflix-sync tagged items. Two phases: grace period start, then deletion after grace expires. Protected items are never deleted.

## Protection

Manual overrides take priority. Tautulli protection is read-only. Both must come from unified state — never computed separately.

## Error Handling

Catch exceptions per service. Log warnings. Never let one failing service break an endpoint.

## Logging

Log meaningful messages. Include timing for sync phases using time.monotonic(). Avoid noise.