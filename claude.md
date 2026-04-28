# Netflix Media Sync

A Flask-based media lifecycle system. Syncs trending content via Trakt into Radarr and Sonarr. Tracks protection, deletion, and history.

This is NOT a sync script. It is a state-driven media lifecycle system.

## Core Principles

- Deterministic behaviour — same input always produces same output across dashboard, protection, top 10, and deletion
- No duplicated logic — if the same logic appears in two places, extract a helper
- Prefer simple, direct implementations over heavy abstraction
- Fail gracefully — external service failures must not crash the app

## Performance (Global Rule)

- All endpoints must use bulk-fetched data and perform lightweight in-memory aggregation
- No endpoint may make per-item external API calls inside a loop

## Consistency Rule

- Similar logic across endpoints must behave consistently
- If logic becomes complex or duplicated, extract a shared helper rather than copying it

## Non-Goals

- No heavy frontend frameworks
- No over-engineering or unnecessary abstractions
- No breaking existing working features
- No new pip dependencies without explicit instruction
