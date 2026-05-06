# Netflix Media Sync

A Flask-based media lifecycle system. Syncs trending content via Trakt
and FlixPatrol into Radarr and Sonarr. Tracks protection, deletion,
and history. Rebranded to Streamarr.

This is NOT a sync script. It is a state-driven media lifecycle system.

---

## 1. Core Rules

- Admin-only tool — prioritise simplicity over scalability
- Avoid over-engineering
- Keep changes minimal and localised
- Do not refactor working systems without explicit instruction
- When in doubt, do less

---

## 2. Core Principles

- Deterministic behaviour — same input always produces same output
  across dashboard, protection, top 10, and deletion
- No duplicated logic — if the same logic appears in two places,
  extract a helper
- Prefer simple, direct implementations over heavy abstraction
- Fail gracefully — external service failures must not crash the app

---

## 3. Architecture Rules

- Maintain clear separation of concerns:
  - Sync logic ONLY in sync_service.py
  - API/UI logic ONLY in web.py
  - External calls ONLY in client files (radarr_client, sonarr_client, etc.)
  - Tag constants and helpers ONLY in tags.py
- Do NOT move logic into the frontend or templates
- Do NOT duplicate logic across layers

---

## 4. Sync Behaviour Rules

- The system is a reconciliation engine, not a one-off script
- All sync operations must be:
  - Idempotent (safe to run multiple times)
  - Deterministic (same input → same result)
- Respect integration modes:
  - "disabled" = no interaction
  - "read" = fetch + simulate only
  - "enabled" = apply changes
- Never bypass or weaken these modes

---

## 5. State & Persistence Rules

- All persistent state must go through:
  - SyncLog
  - SettingsStore
- ManualOverrides.json is removed — protection state lives in
  Radarr/Sonarr as the streamarr-state-protected tag
- Do NOT introduce new ad-hoc file writes
- Ensure thread safety is preserved

---

## 6. Tag Architecture (Locked)

- app/tags.py is the single source of truth for all tag constants
  and helpers — never hardcode tag strings elsewhere
- Tag vocabulary:
  - streamarr — ownership marker (required on every managed item)
  - streamarr-src-{source} — e.g. streamarr-src-netflix
  - streamarr-cat-movie / streamarr-cat-tv — category
  - streamarr-state-protected — protection (replaces ManualOverrides)
- Deletion eligibility is determined solely by presence of the
  streamarr tag — items without it are not managed by Streamarr
- Streamarr only owns what it adds — existing library items are
  never tagged, modified, or deleted
- Protection state is written immediately to Radarr/Sonarr on
  UI toggle — not deferred to the next sync

---

## 7. API & Integration Rules

- External services must be accessed ONLY via their client classes
- All endpoints must use bulk-fetched data and perform lightweight
  in-memory aggregation
- No endpoint may make per-item external API calls inside a loop
- Handle failures gracefully:
  - Never crash the entire sync due to one bad item
  - Skip + log errors instead
- Avoid unnecessary repeated API calls

---

## 8. UI Rules

- UI reflects backend state — it must not contain business logic
- All data must come from API endpoints
- Keep behaviour consistent with existing patterns
  (polling, endpoints, etc.)

---

## 9. Changelog Rules (CRITICAL)

Every meaningful change MUST update CHANGELOG.md.

Follow this exact format:

    ## CHG-XXX — YYYY-MM-DD — Title

    ### Additions
    - ...

    ### Changes
    - ...

    ### Fixes
    - ...

    ### Infrastructure
    - ...

Rules:
- Increment CHG number sequentially
- Use today's date
- Be specific (mention files and behaviour)
- Do NOT summarise vaguely
- Match the existing tone and level of detail
- Current CHG number: CHG-032 (next is CHG-033)

---

## 10. Code Quality Rules

- Prefer clarity over cleverness
- Avoid large, monolithic functions
- Reuse existing helpers where possible
- Do not introduce unnecessary dependencies
- Keep changes minimal and focused

---

## 11. Performance Rules

- All endpoints must use bulk-fetched data and perform lightweight
  in-memory aggregation
- No endpoint may make per-item external API calls inside a loop
- Similar logic across endpoints must behave consistently
- If logic becomes complex or duplicated, extract a shared helper
  rather than copying it

---

## 12. Non-Goals

- No heavy frontend frameworks
- No over-engineering or unnecessary abstractions
- No breaking existing working features
- No new pip dependencies without explicit instruction

---

## 13. Workflow & Orchestration

### Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or
  architectural decisions)
- If something goes sideways, STOP and re-plan immediately
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### Self-Improvement Loop
- After ANY correction from the user: update tasks/lessons.md
  with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more
  elegant way?"
- If a fix feels hacky: "Knowing everything I know now,
  implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

### Autonomous Bug Fixing
- When given a bug report: just fix it
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

---

## 14. Task Management

1. **Plan First** — write plan to tasks/todo.md with checkable items
2. **Verify Plan** — check in before starting implementation
3. **Track Progress** — mark items complete as you go
4. **Explain Changes** — high-level summary at each step
5. **Document Results** — add review section to tasks/todo.md
6. **Capture Lessons** — update tasks/lessons.md after corrections