# Netflix Media Sync

A Flask-based media lifecycle system. Syncs trending content via Trakt into Radarr and Sonarr. Tracks protection, deletion, and history. Provides a web UI for control and visibility.

This is NOT a sync script. It is a state-driven media lifecycle system.

## Core Principles

- Single source of truth — all logic derives from build_media_state()
- No duplicated logic across endpoints
- Fail gracefully — external service failures must not crash the app
- Deterministic — same input always produces same output across dashboard, protection, top 10, and deletion

## Non-Goals

- No heavy frontend frameworks
- No over-engineering or unnecessary abstractions
- No breaking existing working features
- No new pip dependencies without explicit instruction