# Lessons

Patterns from corrections. Read at session start. Update after any correction.

---

## Never tag pre-existing library items

**Correction:** CHG-032 introduced `_ensure_movie_tagged()` / `_ensure_series_tagged()` to retroactively
apply the `streamarr` tag to items already in Radarr/Sonarr. This made pre-existing library items
deletion candidates — items the user added before Streamarr existed.

**Rule:** `add_movie()` and `add_series()` must return `False` silently for any item that already exists
in the library (cache hit with id, or API lookup result with id). Streamarr only owns items it
adds via POST. Never touch, tag, or modify pre-existing items.

---

## Wait for user confirmation before committing

**Rule:** After implementing a change, describe what to test and wait for explicit confirmation
that it works before running `git commit`. Do not pre-emptively commit.

---

## Deterministic source lists — use dict insertion order, not sets

**Context:** Multi-source deduplication in `fetch_from_sources()`.

**Rule:** Use `{source: None}` dicts (not sets) to track sources per title. `list(d.keys())` is
insertion-ordered in Python 3.7+. Sets have undefined iteration order and produce non-deterministic
tag sets across runs.

---

## Verify Tautulli (and similar) API response envelope before writing client code

**Context:** `tautulli_client.fetch_protected_titles()` always returned an empty set.
`_request()` returns `response["response"]`, so `get_history` data lives at
`response.data.data` (double-nested) and `get_activity` sessions at `response.data.sessions`.
The original code did `history.get("data", [])` which returned the inner dict, failed the
`isinstance(list)` check, and silently fell through to `[]`.

**Rule:** When writing a client against a wrapped API (Tautulli, Radarr, etc.), log the raw
response shape on first integration and assert the path to the actual records. Never assume
a single `.get("data")` unwraps to the payload — check whether it's a list or another dict.

---

## Read the actual source before writing integration code

**Context:** Scraper files were generated based on the integration brief
before the upstream repo was accessible. Selectors and data shapes were
guessed.

**Rule:** Never write integration code until you have read the actual
source. If a repo is referenced, fetch it first. If it is not
accessible, say so and wait.

---

## Confirm repo and branch before touching any file

**Context:** Work was started in streaming-scraper instead of
netflix-media-sync. Branch was not checked before making changes.

**Rule:** At session start always run `git status` and `git branch`.
Confirm repo and branch before proceeding.

---

## New data sources must default to disabled or most restrictive state

**Context:** FlixPatrol with all services enabled triggered 100+ imports
before the service filter UI existed.

**Rule:** Never wire a new source to Radarr/Sonarr before the user has
explicitly chosen what to import. Build the filter before the source,
or default to disabled.

---

## Per-item API calls must be wrapped in try/except

**Context:** A single 503 from Radarr aborted the entire sync mid-run.

**Rule:** A single item failure must never abort the batch. Wrap every
per-item external call in try/except. Skip and log, never raise.

---

## Resolve stable values once before entering a loop

**Context:** `ensure_tag("streamarr")` was called per item inside the
add loop, making one redundant API call per title.

**Rule:** Resolve tag IDs, profile IDs, and root folder paths once
before the loop. Pass resolved values in. Never resolve inside a loop
what can be resolved once outside it.

---

## Lock architectural decisions in CLAUDE.md before the session ends

**Context:** Decisions made mid-session (ManualOverrides removal,
ownership rule, protection as a tag) were not written into CLAUDE.md
and had to be rediscovered later.

**Rule:** Any locked architectural decision must be in CLAUDE.md before
the session ends. Decisions made only in chat are invisible to future
sessions.

---

## Check CHG number from CHANGELOG.md before writing any entry

**Context:** Session A prompt used CHG-031 which was already taken.

**Rule:** At session start grep CHANGELOG.md for the last CHG number.
State the next number explicitly. Never assume from memory.

---

## Scope work to what fits within remaining session limits

**Context:** Complex changes were started with insufficient session
remaining, producing truncated or incomplete output.

**Rule:** If the user indicates low remaining usage, scope to what
can be completed and committed cleanly. A partial implementation is
worse than none.