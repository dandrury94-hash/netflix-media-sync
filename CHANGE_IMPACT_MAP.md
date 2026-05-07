# CHANGE_IMPACT_MAP.md — Streamarr

Purpose: make it immediately obvious **where to look and what to touch** when implementing or modifying a feature.

This prevents scattered edits, regressions, and duplicate logic.

---

# 🧠 Core Principle

Every meaningful change in Streamarr should map to **one primary layer**, with clearly defined ripple effects.

Sources → Sync → Tags → State → API → UI

---

# 🔧 Impact Map by Change Type

---

## 1. 📥 Source ingestion changes
(e.g. Trakt / FlixPatrol / aggregation logic)

### Primary files
- app/netflix_fetcher.py  ← Trakt + FlixPatrol merging, `sources` list building
- app/sync_service.py

### Likely required changes
- Normalize item structure (title, type, sources)
- Ensure multi-source merging works correctly

### Must also check
- sync_log.log_add() → ensure sources is stored
- Deduplication logic in sync

### Must NOT touch
- media_state.py ❌
- UI ❌

---

## 2. 🏷 Tagging / ownership logic
(e.g. streamarr tag, protection tag, ownership checks)

### Primary files
- app/tags.py
- app/sync_service.py
- app/radarr_client.py
- app/sonarr_client.py

### Likely required changes
- Tag constants / helpers
- Tag application/removal logic
- Ownership checks before add/delete

### Must also check
- get_tagged_movies() / get_tagged_series()
- Tag filtering consistency across clients

### Must NOT do
- No title-based matching ❌ (CHG-035)
- No UI-based protection logic ❌

---

## 3. 🧠 State computation (CRITICAL LAYER)
(e.g. retention, protection, eligibility, reasons)

### Primary file (authoritative)
- app/media_state.py

### Supporting entry point
- app/web.py → _fetch_media_state()

### Likely required changes
- Retention logic (date_added vs last_watched)
- Protection logic (tags only)
- Deletion eligibility rules
- Reason generation

### Must also check
- SyncLog schema if adding metadata
- That ALL endpoints consume media_state (not recompute)

### Must NOT do
- No logic duplication in web.py ❌
- No direct API calls here ❌
- No tag writes here ❌

---

## 4. 🗑 Deletion logic
(e.g. what gets removed and when)

### Primary file
- app/sync_service.py → run_deletions()

### Likely required changes
- Eligibility conditions
- Notification timing
- Tag-based filtering

### Must also check
- media_state alignment (same logic assumptions)
- Pushover notifications

### Must NOT do
- No title matching ❌
- No processing of untagged items ❌ (P1-7)
- No hidden side effects ❌

---

## 5. 🕒 Retention / time-based logic
(e.g. last_watched, retention windows)

### Primary files
- app/media_state.py
- app/sync_service.py
- app/sync_log.py
- app/tautulli_client.py

### Likely required changes
- last_watched updates
- Retention anchor logic
- Date resolution rules

### Must also check
- SyncLog schema changes
- Backwards compatibility of stored data

### Important rule
- Tautulli = signal only (not protection) (CHG-036)

---

## 6. 📦 SyncLog / metadata storage
(e.g. additions, last_watched, history)

### Primary file
- app/sync_log.py

### Likely required changes
- Entry schema updates (e.g. sources[])
- Helper methods (get_date_added, etc.)

### Must also check
- All writers of SyncLog (sync_service)
- All readers (media_state, web endpoints)

### Must NOT do
- No business logic here ❌
- No decision-making ❌

---

## 7. 🌐 API / Web layer
(e.g. endpoints, JSON responses)

### Primary file
- app/web.py

### Likely required changes
- Add new endpoints
- Adjust response shape

### Must also check
- All endpoints use _fetch_media_state()
- No inline logic duplication

### Must NOT do
- No retention logic ❌
- No protection logic ❌
- No direct Radarr/Sonarr calls for state ❌

---

## 8. 🎛 UI / frontend
(e.g. dashboard, settings, display)

### Primary files
- app/templates/*
- app/static/script.js

### Likely required changes
- Display new fields (reason, sources, etc.)
- Add toggles (e.g. simulation mode)

### Must also check
- API response compatibility
- UI reflects tag state accurately

### Must NOT do
- No business logic in JS ❌
- No duplicated state logic ❌

---

## 9. 🔔 Notifications (Pushover)
(e.g. pre-deletion alerts, weekly preview)

### Primary files
- app/pushover_client.py
- app/sync_service.py
- scheduler functions (worker / weekly preview)

### Likely required changes
- Trigger conditions
- Message formatting

### Must also check
- Deletion timing alignment
- Retention calculations

---

## 10. 🧪 Simulation mode (P2-5)
(e.g. safe dry-run execution)

### Primary files
- app/sync_service.py
- app/settings.py
- app/web.py

### Likely required changes
- Conditional writes (skip mutations)
- Logging "would do" actions instead

### Must also check
- UI indicator
- No accidental writes leak through

### Must NOT do
- No Radarr/Sonarr writes ❌
- No SyncLog writes ❌

---

# 🚨 High-Risk Areas

Changes here require extra caution:

### media_state.py
- Single source of truth
- Any bug propagates everywhere

### run_deletions()
- Can delete real media
- Must be deterministic and tag-based

### SyncLog schema
- Persistent data
- Breaking changes affect all users

---

# ✅ Safe Change Pattern

When implementing a feature:

1. Identify layer (source, sync, state, API, UI)
2. Modify ONLY that layer first
3. Follow impact map to update dependencies
4. Verify:
   - No duplicated logic introduced
   - No forbidden patterns used
   - CHANGELOG.md updated

---

# ❌ Anti-Patterns (Do Not Introduce)

- Recomputing state in web.py
- Using title-string matching for ownership
- Mixing tag logic with UI logic
- Writing to Radarr/Sonarr outside sync_service
- Adding new "state" outside media_state

---

# 🧭 Mental Model

If you're unsure where something belongs:

- "What should happen?" → sync_service
- "What is the current state?" → media_state
- "How is it shown?" → web.py / UI
- "Where is it stored?" → SyncLog
- "What owns it?" → tags

---

This file exists to reduce:
- cognitive load
- token usage
- architectural drift

If a change doesn't clearly map here → pause and reassess.