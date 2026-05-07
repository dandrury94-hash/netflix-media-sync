# FILES_OF_INTEREST.md — Streamarr

This file highlights the **most important files in the project**, what they do, and when they should be modified.

Claude Code should use this as a **navigation shortcut** before exploring the full repo.

---

## 🧠 Core Architecture (Read First)

### `app/media_state.py`
**Purpose:**  
Canonical state builder for all media.

**Why it matters:**  
- This is the **single source of truth for UI/API state**
- Computes:
  - protection
  - retention
  - eligibility
  - status
  - reason

**Used by:**
- `web.py` (via `_fetch_media_state()`)

**Rules:**
- ✅ ALL state logic belongs here
- ❌ Do NOT duplicate logic elsewhere

**Related Decisions:**
- D1 — Tags are source of truth
- D5 — Retention model
- D7 — Deterministic deletion
- D10 — Canonical read model

---

### `app/sync_service.py`
**Purpose:**  
Core orchestration engine.

**Responsibilities:**
- Fetch from sources (Trakt, FlixPatrol)
- Apply tags in Radarr/Sonarr
- Trigger deletions
- Write metadata to SyncLog

**Rules:**
- ❌ Do NOT compute UI state here
- ❌ Do NOT use title-based logic
- ✅ Only operate on tagged items

**Related Decisions:**
- D1 — Tag-driven system
- D2 — Only operate on streamarr-tagged items
- D7 — Deterministic deletion
- D11 — Multi-source attribution

---

### `app/web.py`
**Purpose:**  
Flask web layer (UI + API)

**Responsibilities:**
- Expose endpoints
- Render templates
- Call `_fetch_media_state()`

**Rules:**
- ❌ Do NOT compute business logic here
- ❌ Do NOT derive protection/eligibility manually
- ✅ Only transform and return data

**Critical Function:**
- `_fetch_media_state()` → entry point into system state

**Related Decisions:**
- D10 — Canonical read model

---

## 🏷 Tag System

### `app/tags.py`
**Purpose:**  
Central definition of all Streamarr tags

**Expected contents:**
- `streamarr`
- `streamarr-state-protected`

**Rules:**
- ✅ All tag names must be defined here
- ❌ Do NOT hardcode tag strings elsewhere

**Related Decisions:**
- D1 — Tags are source of truth
- D3 — Protection is tag-based

---

## 🗃 Metadata & History

### `app/sync_log.py`
**Purpose:**  
Stores metadata only

**Stores:**
- `date_added`
- `last_watched`
- `sources`

**Rules:**
- ❌ Must NOT influence protection
- ❌ Must NOT determine eligibility
- ✅ Used only for reference + retention anchoring

**Related Decisions:**
- D6 — Metadata only

---

### `app/removal_history.py`
**Purpose:**  
Tracks what has been deleted

**Rules:**
- Purely historical
- No impact on logic

---

## 📡 External Integrations

### `app/radarr_client.py`
### `app/sonarr_client.py`

**Purpose:**  
API clients for Radarr/Sonarr

**Responsibilities:**
- Fetch library items
- Apply/remove tags
- Trigger deletions

**Rules:**
- ❌ No business logic here
- ❌ No filtering decisions
- ✅ Thin API wrappers only

---

### `app/tautulli_client.py`
**Purpose:**  
Fetch watch history

**Rules:**
- Only used for `last_watched`
- ❌ Must NOT be used for protection

**Related Decisions:**
- D4 — Tautulli is signal only

---

### `app/plex_client.py`
**Purpose:**  
Manage Plex collections (per-service and main Streamarr collection)

**Responsibilities:**
- `sync_plex_collections()` — creates/updates one collection per source service plus a main
  Streamarr collection covering all service-tagged items (root tag OR src tag)
- `test_connection()` — verifies Plex reachability for connection status endpoint

**Rules:**
- ❌ No business logic — collection membership is driven entirely by Radarr/Sonarr tags
- ✅ Streamarr collection = union of root-tagged items and source-tagged items
- ✅ Service collections = source-tagged items only

**Introduced:** CHG-049 (initial), CHG-052–056 (pre-Streamarr item handling)

---

## 🌐 Source Aggregation

### `app/netflix_fetcher.py`
**Purpose:**  
Multi-source fetch orchestration

**Responsibilities:**
- Combine Trakt + FlixPatrol results via `fetch_from_sources()`
- Deduplicate by `(title, type)` and build the `sources` list per item
- Pass merged result to `SyncService._run()`

**Rules:**
- ✅ Maintain `sources` as a list (insertion-ordered, deduplicated)
- ❌ Do NOT collapse to single source

**Related Decisions:**
- D11 — Multi-source attribution

---

### `app/scraper/core/aggregator.py`
**Purpose:**  
FlixPatrol-internal aggregator — combines per-service scrape results into a
unified item list. Not involved in Trakt + FlixPatrol merging.

**Rules:**
- Returns items with a single `source` key (service name)
- Aggregation of cross-source `sources` lists happens upstream in `netflix_fetcher.py`

---

## ⚙️ Config & Settings

### `app/settings.py`
**Purpose:**  
Persistent configuration store

---

### `config/settings.json`
**Purpose:**  
User-configurable values

---

## 🖥 UI Layer

### `app/templates/`
### `app/static/`

**Purpose:**  
Frontend rendering

**Rules:**
- ❌ No business logic
- ❌ No state derivation
- ✅ Pure display layer

---

## 🧵 Background Workers

### `app/main.py`
**Purpose:**  
Application entrypoint

**Includes:**
- Worker loop (`run_worker`)
- Weekly preview job

---

## 🔥 High-Risk Areas (Handle Carefully)

These areas are tightly coupled to core logic:

- `media_state.py`
- `sync_service.py`
- deletion logic
- tag handling

**Any change here must:**
- Be reflected in `CHANGELOG.md`
- Respect all decisions in `DECISIONS.md`

---

## 🚫 Common Mistakes to Avoid

- Recomputing state in `web.py`
- Using title matching for logic
- Adding new state stores
- Mixing UI and business logic
- Ignoring tag-based rules
- Introducing secondary sources of truth

---

## 🧭 How to Navigate the Codebase

### If you need to…

**Understand UI state →**
→ `media_state.py`

**Modify sync behaviour →**
→ `sync_service.py`

**Add API endpoint →**
→ `web.py` (but call `_fetch_media_state()`)

**Change tagging →**
→ `tags.py` + `sync_service.py`

**Debug retention/deletion →**
→ `media_state.py` (first), then `sync_service.py`

---

## 🎯 Guiding Rule

If you're about to write logic and you're not in `media_state.py`…

**You're probably in the wrong place.**