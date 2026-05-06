# Backend Rules

## Architecture

- web.py → API routes and request handling only
- sync_service.py → sync orchestration and lifecycle logic
- radarr_client.py / sonarr_client.py → external API calls only, no logic
- sync_log.py, manual_overrides.py, removal_history.py → persistence only

## Data Aggregation

- Endpoints may aggregate data directly using bulk-fetched results
- Shared logic should be extracted into helpers when reused across endpoints, but is not required to follow a single global state model
- Prefer simple aggregation over introducing global state models

## Performance — STRICT

- Never call lookup_movie, lookup_series, or get_*_by_id inside a loop
- Always fetch full libraries once with get_all_movies() / get_all_series()
- Always build in-memory dict maps for O(1) lookups

## Deletion Safety

- Deletion must only ever be triggered from sync_service.run_deletions() — never from an endpoint directly
- Only streamarr tagged items may be deleted
- Protected items are never deleted

## Protection

- Protection = `streamarr-state-protected` tag only
- Tautulli = retention clock signal only (via `last_watched`) — never a protection source
- `protection_source` valid values: `"manual"` | `None`

## Error Handling

- Catch exceptions per external service
- Log warnings and continue — never let one failing service break an endpoint

## Logging

- Log meaningful messages at key operations
- Include timing for sync phases using time.monotonic()
