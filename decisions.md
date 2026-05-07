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

## D16 — When to branch vs. commit directly to master

**Decision:**  
Branch for a change when any of the following apply:
- Touches core logic files (`sync_service.py`, `media_state.py`, `config.py`, SyncLog schema)
- Has a spec or design phase before implementation can begin
- Risk of regression is non-trivial (multiple files, interconnected logic)
- Could sit in progress across multiple sessions

Commit directly to master when all of the following are true:
- Isolated to UI, templates, or static assets with no logic changes
- Scope is small and the full change lands in one session
- No risk of leaving master in a broken intermediate state
- No spec work required — the approach is already clear

**Why:**  
Feature branches provide isolation for iterative design and protect master from half-finished work. But unnecessary branching adds friction for changes that are clearly scoped and safe.

**Introduced:** CHG-043 planning phase

**Tiebreaker:**  
If the change requires a spec phase before code can be written, always branch.

---

## D17 — External signals stored under canonical library title

**Decision:**
Any external signal written to SyncLog (e.g. `last_watched`) must use the Radarr/Sonarr title as the key, not the title returned by the external service.

**Why:**
Tautulli (and other external services) may return titles with slightly different casing. If the external title is stored directly, lookups by Radarr/Sonarr title silently miss the record and the signal is lost.

**Introduced:** CHG-048 (audit fix — Tautulli last_watched key)

**Implications:**
- Before writing to SyncLog, resolve the library canonical title from the Radarr/Sonarr cache
- Use `cache[title.lower()]["title"]` to get the canonical form
- Applies to any future external signal (not just last_watched)

---

## D18 — Retention date calculation must mirror build_media_state

**Decision:**
Any code that computes a removal date outside `build_media_state` must use the same fallback chain: SyncLog `date_added` → Radarr/Sonarr API `added` field → today.

**Why:**
`run_weekly_preview` previously defaulted to `today` when SyncLog had no entry, while `build_media_state` first tried the API `added` field. This caused the weekly Pushover preview to show different removal dates than the dashboard.

**Introduced:** CHG-048 (audit fix — weekly preview date fallback)

**Implications:**
- If duplicating date resolution logic outside `build_media_state`, always include the API fallback
- Prefer calling `build_media_state` directly where possible to avoid divergence

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