# CLAUDE.md — Streamarr

This file defines how Claude Code should operate within the Streamarr project.

It is **authoritative**. Follow it strictly.

---

## 🧭 Core Principles

- Streamarr is a **deterministic system**
- **Tags are the single source of truth**
- **No duplicated logic across layers**
- **No hidden or implicit state**
- **Every change must be traceable via CHANGELOG.md**

---

## 🔒 Hard Rules (Non-Negotiable)

### 1. CHANGELOG is a gate
- Do **not** present work as complete until:
  - CHANGELOG.md is updated
  - A new CHG-XXX entry is added
- If no changelog entry → the work is **not complete**

---

### 2. media_state is the ONLY state engine
- All UI/API state must come from:
  _fetch_media_state()
- Which delegates to:
  build_media_state()

❌ NEVER:
- Recompute protection
- Recompute eligibility
- Recompute deletion logic
- Recompute retention logic

---

### 3. Tags define reality
- streamarr → managed by Streamarr  
- streamarr-state-protected → protected  

Everything must derive from **tag presence**, not stored values.

---

### 4. No title-based logic (except logging)
❌ Forbidden:
- Matching titles for protection  
- Matching titles for deletion  
- Matching titles for ownership  

✅ Allowed:
- Logging (SyncLog)  
- Display purposes only  

---

### 5. SyncLog is metadata only
SyncLog may store:
- date_added
- last_watched
- sources

SyncLog must NOT:
- Drive protection  
- Drive eligibility  
- Act as source of truth  

---

### 6. No duplicate logic across files
- Logic must live in **one place only**
- If logic exists in:
  - media_state.py
- It must NOT be duplicated in:
  - web.py
  - sync_service.py
  - any endpoint

---

### 7. Deterministic deletions only
Deletion must be based on:
- Tag presence (streamarr)
- Retention window
- Protection tag absence

Nothing else.

---

## 🚫 Forbidden Patterns

These have caused bugs previously and must not be reintroduced:

- ❌ Title-based protection systems  
- ❌ ManualOverrides-style state files  
- ❌ Multiple competing “sources of truth”  
- ❌ Per-endpoint state calculation  
- ❌ Hidden background mutations  
- ❌ Using Tautulli as a protection system  
- ❌ Mixing business logic into Flask routes  
- ❌ Re-fetching Radarr/Sonarr per item inside loops  

---

## 🧠 Architectural Decisions (Summary)

Refer to DECISIONS.md for full context.

Key highlights:
- Tags are the only state authority  
- Tautulli is signal only (last_watched), not protection  
- Retention is anchored to:
  - last_watched OR
  - date_added  
- Streamarr only operates on its own tagged items  
- Deletion logic must be fully deterministic  

---

## 🧩 Development Workflow

### Before starting work:
- Read:
  - CLAUDE.md
  - DECISIONS.md
  - FILES_OF_INTEREST.md
  - CHANGE_IMPACT_MAP.md
  - CHANGELOG.md
  - tasks/todo.md

---

### While implementing:
- Keep logic centralized
- Avoid introducing new state
- Prefer extending existing structures

---

### Before marking complete:
- Update CHANGELOG.md
- Ensure:
  - No duplicated logic introduced
  - No forbidden patterns used
  - Tags remain the source of truth

---

## 📌 Canonical Data Flow

Sources → SyncService → Radarr/Sonarr (tags applied)  
→ SyncLog (metadata only)  
→ _fetch_media_state()  
→ build_media_state()  
→ API/UI

---

## ⚠️ Known Constraints

- Only streamarr-tagged items are managed
- Unmanaged library items must never appear in UI
- Deletion must never affect non-streamarr content
- All protection must come from tags

---

## 🎯 Goal

Keep Streamarr:
- Predictable
- Inspectable
- Safe
- Easy to reason about

If a change makes the system harder to reason about, it is wrong.