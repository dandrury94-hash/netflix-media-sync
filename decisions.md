# DECISIONS.md — Streamarr

Architectural decisions that define how Streamarr behaves and **why**.  
These are guardrails for future changes and for Claude Code.

---

## Core Principle

**Streamarr must be deterministic, tag-driven, and side-effect predictable.**

No hidden state. No inferred ownership. No title-based ambiguity.

---

## D1 — Tags are the single source of truth

**Decision:**
All lifecycle control (managed, protected, eligible) is derived from tags in Radarr/Sonarr.

**Why:**
Previous implementations relied on title matching and stored state, which caused drift and incorrect deletions.

**Implications:**
- `streamarr` tag → item is managed
- `streamarr-state-protected` → item is protected
- If a tag is removed externally, Streamarr respects it immediately
- No internal override systems

---

## D2 — Streamarr only operates on its own tagged items

**Decision:**
Only items with the `streamarr` tag are ever evaluated.

**Why:**
Unmanaged library items must never be touched or even considered.

**Implications:**
- Fixes issues like items appearing "overdue" incorrectly
- Prevents accidental deletions of externally managed content
- Applies to:
  - Deletion logic
  - UI state
  - Notifications

---

## D3 — Protection is tag-based only (no stored overrides)

**Decision:**
Protection is represented solely via the `streamarr-state-protected` tag.

**Why:**
`ManualOverrides.json` created dual sources of truth and sync inconsistencies.

**Implications:**
- UI toggles write directly to Radarr/Sonarr
- No local persistence of protection state
- Protection is instantly reflected system-wide

---

## D4 — Tautulli is not a protection mechanism

**Decision:**
Tautulli is used only to provide `last_watched` timestamps.

**Why:**
Using Tautulli as a protection source created hidden logic and confusion.

**Implications:**
- No "Tautulli protected" state
- No title-based protection lists
- Watching content extends retention instead of blocking deletion

---

## D5 — Retention is time-based, anchored to activity

**Decision:**
Retention is calculated using:
- `last_watched` (if available)
- otherwise `date_added`

**Why:**
Static timers do not reflect real usage.

**Implications:**
- Watching resets the retention clock
- No separate "keep alive" mechanism required
- Behavior is predictable and user-driven

---

## D6 — SyncLog stores metadata, not state

**Decision:**
`SyncLog` is retained only for metadata (e.g. `date_added`, `last_watched`).

**Why:**
Previously it acted as a shadow state system, causing drift.

**Implications:**
- No eligibility or protection logic stored
- Safe to use for historical/reference data only
- Can be replaced later without affecting logic

---

## D7 — Deletion logic is deterministic and tag-scoped

**Decision:**
Deletion eligibility is computed strictly from:
- tag presence
- retention timing
- protection tag

**Why:**
String matching and mixed logic caused inconsistent deletions.

**Implications:**
- No fuzzy matching
- No dependency on external lists
- Fully predictable outcomes

---

## D8 — Grace period is removed

**Decision:**
Grace periods are replaced with a pre-deletion notification.

**Why:**
Grace periods introduced unnecessary state complexity.

**Implications:**
- No `grace_periods` tracking
- Single clear timeline:
  - retention ends → notification → deletion
- Simpler mental model

---

## D9 — Notifications replace hidden safety nets

**Decision:**
Users are warned **before deletion**, not protected implicitly.

**Why:**
Silent protections are confusing; visibility is better than hidden rules.

**Implications:**
- Weekly preview job surfaces upcoming deletions
- Future: 7-day pre-deletion Pushover alerts
- No automatic "soft protection"

---

## D10 — media_state is the canonical read model

**Decision:**
All UI and API state must come from `build_media_state()`.

**Why:**
Previously, multiple endpoints recomputed logic differently.

**Implications:**
- No duplication of eligibility/protection logic
- Web layer must not derive state independently
- Ensures consistency across UI

---

## D11 — Multi-source attribution is preserved

**Decision:**
Items track all contributing sources (e.g. Trakt + FlixPatrol).

**Why:**
Single-source attribution loses important context.

**Implications:**
- `sources` is a list, not a string
- Used for:
  - transparency
  - future ranking/weighting
- UI should display multiple sources

---

## D12 — Deterministic before safe experimentation

**Decision:**
Simulation mode is deferred until core logic is stable.

**Why:**
Simulating broken logic provides false confidence.

**Implications:**
- P1 must be complete before simulation
- Simulation mode will mirror real logic exactly
- No divergence between real and simulated paths

---

## D13 — No external system ownership inference

**Decision:**
Streamarr does not attempt to infer who added content (e.g. Overseerr/Seerr).

**Why:**
Tagging external systems introduces coupling and complexity.

**Implications:**
- No `seerr` or external ownership tags
- Ownership = Streamarr tag only
- Everything else is ignored

---

## D14 — ChangeLog is a completion gate

**Decision:**
A change is not complete until recorded in `CHANGELOG.md`.

**Why:**
Ensures traceability and prevents silent architectural drift.

**Implications:**
- Every task must map to a CHG entry
- Decisions should reference CHG history where relevant

---

## D15 — Avoid reintroducing rejected patterns

**Forbidden patterns:**
- Title-based matching for lifecycle decisions
- Local override files (e.g. ManualOverrides)
- Multiple sources of truth for protection/state
- Per-endpoint logic duplication
- Hidden safety mechanisms (implicit protection)

---

## Future Clarifications (Open Questions)

These are intentionally unresolved and should not be assumed:

- Should SyncLog eventually be removed entirely?
- Should Radarr/Sonarr native `added` dates replace SyncLog?
- How should multi-source weighting influence ranking (Phase 3)?

---

## Summary

Streamarr is:

- **Tag-driven**
- **Deterministic**
- **Stateless (for decisions)**
- **Transparent to the user**

If a proposed change violates any of the above, it should be rejected or redesigned.