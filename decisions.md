# DECISIONS.md — Streamarr

Architectural decisions that define how Streamarr behaves and **why**.  
These are guardrails for future changes and for Claude Code.

---

## Core Principle

Streamarr must be deterministic, tag-driven, and side-effect predictable.

No hidden state. No inferred ownership. No title-based ambiguity.

---

## D1 — Tags are the single source of truth

**Decision:**  
All lifecycle control (managed, protected, eligible) is derived from tags in Radarr/Sonarr.

**Why:**  
Previous implementations relied on title matching and stored state, which caused drift and incorrect deletions.

**Introduced:** CHG-030 (tag namespace) + CHG-031 (core realignment)

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

**Introduced:** CHG-031 (ownership model), enforced in P1-7

**Implications:**
- Prevents accidental deletions of externally managed content
- Fixes "false overdue" issues
- Applies to:
  - Deletion logic
  - UI state
  - Notifications

---

## D3 — Protection is tag-based only (no stored overrides)

**Decision:**  
Protection is represented solely via the `streamarr-state-protected` tag.

**Why:**  
ManualOverrides created dual sources of truth and sync inconsistencies.

**Introduced:** CHG-034 (P1-2 + P1-3)

**Implications:**
- UI toggles write directly to Radarr/Sonarr
- No local persistence of protection state
- Protection is instantly reflected system-wide

---

## D4 — Tautulli is not a protection mechanism

**Decision:**  
Tautulli is used only to provide `last_watched` timestamps.

**Why:**  
Using Tautulli as protection created hidden logic and confusion.

**Introduced:** CHG-034 (P1-2 + P1-3) → fully enforced CHG-037 (P2-2)

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

**Introduced:** CHG-035 (P1-4)

**Implications:**
- Watching resets the retention clock
- No separate "keep alive" mechanism required
- Behaviour is predictable and user-driven

---

## D6 — SyncLog stores metadata, not state

**Decision:**  
SyncLog is retained only for metadata (date_added, last_watched, sources).

**Why:**  
Previously it acted as a shadow state system, causing drift.

**Introduced:** CHG-031 → refined in CHG-034

**Implications:**
- No eligibility or protection logic stored
- Safe for historical/reference data only
- May be replaced later without affecting logic

---

## D7 — Deletion logic is deterministic and tag-scoped

**Decision:**  
Deletion eligibility is computed strictly from:
- tag presence
- retention timing
- protection tag

**Why:**  
Mixed logic and string matching caused inconsistent deletions.

**Introduced:** CHG-036 (P1-5 + P1-6 + P1-7)

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

**Introduced:** CHG-036 (P1-6)

**Implications:**
- No grace_period tracking
- Single clear timeline:
  retention ends → notification → deletion
- Simpler mental model

---

## D9 — Notifications replace hidden safety nets

**Decision:**  
Users are warned before deletion, not protected implicitly.

**Why:**  
Silent protections are confusing; visibility is better.

**Introduced:** CHG-036 (P1-6)

**Implications:**
- Weekly preview surfaces upcoming deletions
- Future: 7-day pre-deletion notifications
- No automatic "soft protection"

---

## D10 — media_state is the canonical read model

**Decision:**  
All UI and API state must come from build_media_state().

**Why:**  
Multiple endpoints previously recomputed logic inconsistently.

**Introduced:** CHG-019 (original state model) → reinforced in CHG-034

**Implications:**
- No duplication of eligibility/protection logic
- Web layer must not derive state independently
- Ensures consistency across UI

---

## D11 — Multi-source attribution is preserved

**Decision:**  
Items track all contributing sources (e.g. Trakt + FlixPatrol).

**Why:**  
Single-source attribution loses context and future usefulness.

**Introduced:** CHG-032 (P1-0 + P1-1)

**Implications:**
- `sources` is a list, not a string
- Used for:
  - transparency
  - future ranking/weighting
- UI should support multiple sources

---

## D12 — Deterministic before safe experimentation

**Decision:**  
Simulation mode is deferred until core logic is stable.

**Why:**  
Simulating incorrect logic creates false confidence.

**Introduced:** CHG-036 planning phase

**Implications:**
- Phase 1 must be complete first
- Simulation must mirror real execution exactly
- No divergence between real and simulated paths

---

## D13 — No external system ownership inference

**Decision:**  
Streamarr does not infer who added content (e.g. Overseerr/Seerr).

**Why:**  
External tagging introduces coupling and long-term complexity.

**Introduced:** CHG-036 (decision during P1-7 discussion)

**Implications:**
- No external ownership tags
- Ownership = streamarr tag only
- Everything else is ignored

---

## D14 — CHANGELOG is a completion gate

**Decision:**  
A change is not complete until recorded in CHANGELOG.md.

**Why:**  
Prevents silent architectural drift and ensures traceability.

**Introduced:** Project-wide convention (formalised in CLAUDE.md)

**Implications:**
- Every task maps to a CHG entry
- No "invisible" changes
- CHANGELOG is part of the workflow

---

## D15 — Avoid reintroducing rejected patterns

**Decision:**  
Certain patterns are explicitly forbidden.

**Why:**  
These caused real production issues previously.

**Introduced:** Accumulated across CHG-019 → CHG-034

**Forbidden patterns:**
- Title-based matching for lifecycle decisions
- Local override files
- Multiple sources of truth
- Per-endpoint logic duplication
- Hidden safety mechanisms

---

## Future Clarifications (Open Questions)

These are intentionally unresolved:

- Should SyncLog eventually be removed entirely?
- Should Radarr/Sonarr native `added` dates replace SyncLog?
- How should multi-source weighting influence ranking (Phase 3)?

---

## Summary

Streamarr is:

- Tag-driven  
- Deterministic  
- Stateless (for decisions)  
- Transparent  

If a change violates these principles, it must be rejected or redesigned.