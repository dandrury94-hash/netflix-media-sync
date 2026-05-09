const STATUS_ICONS = {
  pending:  "⏳",
  available: "✅",
  will_add: "➕",
  disabled: "➖",
};

const STATUS_LABELS = {
  pending:  "Pending — monitored but not yet downloaded",
  available: "Available — downloaded and in library",
  will_add: "Will Add — not yet in Radarr/Sonarr",
  disabled: "Disabled — integration disabled",
};

document.addEventListener("DOMContentLoaded", () => {
  const syncButton = document.getElementById("syncButton");
  const settingsForm = document.getElementById("settingsForm");
  const saveResult = document.getElementById("saveResult");

  const setStatus = (element, text, state = "") => {
    element.textContent = text;
    element.classList.remove("success", "error");
    if (state) element.classList.add(state);
  };

  // ── Settings sidebar tab switching ──
  document.querySelectorAll(".settings-sidenav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".settings-sidenav-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".settings-section").forEach((s) => s.classList.remove("active"));
      btn.classList.add("active");
      const section = document.getElementById("stab-" + btn.dataset.settingsTab);
      if (section) section.classList.add("active");
    });
  });

  // ── Top-nav tab switching ──
  document.querySelectorAll(".topnav a[data-tab-target]").forEach((link) => {
    link.addEventListener("click", (e) => {
      if (!document.querySelector(".tab-panel")) return;
      e.preventDefault();
      const tab = link.dataset.tabTarget;
      document.querySelectorAll(".tab-panel").forEach((p) =>
        p.classList.toggle("active", p.id === `tab-${tab}`)
      );
      document.querySelectorAll(".topnav a").forEach((a) => a.classList.remove("active"));
      link.classList.add("active");
    });
  });

  // Set the correct tab-target link as active on initial page load.
  if (document.querySelector(".tab-panel")) {
    const dashLink = document.querySelector(".topnav a[data-tab-target='dashboard']");
    if (dashLink) dashLink.classList.add("active");
  }

  // ── Sync button ──
  if (syncButton) {
    const syncErrorBox = document.getElementById("syncErrorBox");
    const syncErrorText = document.getElementById("syncErrorText");
    const syncErrorClear = document.getElementById("syncErrorClear");

    if (syncErrorClear && syncErrorBox) {
      syncErrorClear.addEventListener("click", () => { syncErrorBox.hidden = true; });
    }

    let syncEstimatedSeconds = parseInt(syncButton.dataset.estimated || "60", 10) || 60;
    const syncButtonLabel = syncButton.querySelector("span");

    syncButton.addEventListener("click", async () => {
      if (syncErrorBox) syncErrorBox.hidden = true;
      syncButton.disabled = true;
      syncButton.classList.add("syncing");
      syncButton.style.setProperty("--sync-pct", "0%");
      if (syncButtonLabel) syncButtonLabel.textContent = "Syncing…";

      const steps = Math.max(1, (syncEstimatedSeconds * 1000) / 500);
      const widthPerStep = 90 / steps;
      let currentWidth = 0;
      const timer = setInterval(() => {
        currentWidth = Math.min(90, currentWidth + widthPerStep);
        syncButton.style.setProperty("--sync-pct", `${currentWidth}%`);
        if (currentWidth >= 90) clearInterval(timer);
      }, 500);

      try {
        const response = await fetch("/api/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        clearInterval(timer);
        if (!response.ok) throw new Error(`Sync failed (HTTP ${response.status}) — check logs for details`);
        const data = await response.json();
        if (data.estimated_seconds) syncEstimatedSeconds = data.estimated_seconds;
        syncButton.style.setProperty("--sync-pct", "100%");
        await new Promise((r) => setTimeout(r, 600));
        syncButton.classList.remove("syncing");
        syncButton.style.removeProperty("--sync-pct");
        if (syncButtonLabel) syncButtonLabel.textContent = "Sync Now";
        syncButton.disabled = false;
        window.location.reload();
      } catch (err) {
        clearInterval(timer);
        syncButton.classList.remove("syncing");
        syncButton.style.removeProperty("--sync-pct");
        if (syncButtonLabel) syncButtonLabel.textContent = "Sync Now";
        syncButton.disabled = false;
        if (syncErrorBox) {
          syncErrorBox.hidden = false;
          if (syncErrorText) syncErrorText.textContent = err.message || "Sync failed — check logs for details";
        }
      }
    });
  }

  // ── Preview sync ──
  const previewButton = document.getElementById("previewButton");
  const previewResult = document.getElementById("previewResult");
  if (previewButton) {
    previewButton.addEventListener("click", async () => {
      previewButton.disabled = true;
      previewButton.querySelector("span").textContent = "Previewing…";
      if (previewResult) previewResult.hidden = true;
      try {
        const response = await fetch("/api/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ simulate: true }),
        });
        if (!response.ok) throw new Error(`Preview failed (HTTP ${response.status})`);
        const data = await response.json();
        const result = data.result || {};
        const movies = (result.would_add_movies || []).length;
        const series = (result.would_add_series || []).length;
        if (previewResult) {
          if (movies === 0 && series === 0) {
            previewResult.textContent = "Preview: nothing new to add.";
          } else {
            const parts = [];
            if (movies) parts.push(`${movies} movie${movies !== 1 ? "s" : ""}`);
            if (series) parts.push(`${series} series`);
            previewResult.textContent = `Preview: ${parts.join(" and ")} to add.`;
          }
          previewResult.hidden = false;
        }
      } catch (err) {
        if (previewResult) {
          previewResult.textContent = err.message || "Preview failed.";
          previewResult.hidden = false;
        }
      } finally {
        previewButton.disabled = false;
        previewButton.querySelector("span").textContent = "Preview";
        checkConnections();
      }
    });
  }

  // ── Settings form ──
  if (settingsForm) {
    settingsForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      setStatus(saveResult, "Saving settings…");
      const formData = new FormData(settingsForm);
      const payload = {};
      payload.netflix_top_countries = formData.getAll("netflix_top_countries");
      payload.sources = formData.getAll("sources");
      payload.flixpatrol_services = formData.getAll("flixpatrol_services");
      for (const [key, value] of formData.entries()) {
        if (key === "netflix_top_countries") continue;
        if (key === "sources") continue;
        if (key === "flixpatrol_services") continue;
        payload[key] = value;
      }
      const fpTypeContainer = document.getElementById("fpServiceList");
      const fpServiceTypes = {};
      if (fpTypeContainer) {
        fpTypeContainer.querySelectorAll(".fp-type-cb[data-type='movie']").forEach((movieCb) => {
          const key = movieCb.dataset.service;
          const row = movieCb.closest(".fp-service-card");
          const seriesCb = row && row.querySelector(".fp-type-cb[data-type='series']");
          const types = [];
          if (movieCb.checked) types.push("movie");
          if (seriesCb && seriesCb.checked) types.push("series");
          fpServiceTypes[key] = types;
        });
      }
      payload.flixpatrol_service_types = fpServiceTypes;
      try {
        const response = await fetch("/api/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const result = await response.json();
        if (result.status === "saved") {
          setStatus(saveResult, "Settings saved successfully.", "success");
        } else {
          setStatus(saveResult, "Unable to save settings.", "error");
        }
      } catch (error) {
        setStatus(saveResult, `Save failed: ${error.message}`, "error");
      }
    });
  }

  // ── FlixPatrol service preview ──
  const fpLoadBtn = document.getElementById("fpLoadBtn");
  const fpListEl = document.getElementById("fpServiceList");
  if (fpLoadBtn) {
    // Restore saved services on page load from data attributes embedded by Jinja
    const savedServices = JSON.parse(fpListEl?.dataset.savedServices || "[]");
    const savedServiceTypes = JSON.parse(fpListEl?.dataset.savedServiceTypes || "{}");
    if (savedServices.length) {
      renderFlixPatrolServices([], savedServices, savedServiceTypes);
    }

    fpLoadBtn.addEventListener("click", async () => {
      const country = document.getElementById("flixpatrolCountry")?.value || "";
      const statusEl = document.getElementById("fpLoadStatus");

      // Preserve current UI state before re-rendering
      const savedChecked = Array.from(
        document.querySelectorAll('input[name="flixpatrol_services"]:checked')
      ).map((el) => el.value);
      const currentTypes = {};
      if (fpListEl) {
        fpListEl.querySelectorAll(".fp-type-cb[data-type='movie']").forEach((movieCb) => {
          const key = movieCb.dataset.service;
          const row = movieCb.closest(".fp-service-card");
          const seriesCb = row && row.querySelector(".fp-type-cb[data-type='series']");
          const types = [];
          if (movieCb.checked) types.push("movie");
          if (seriesCb && seriesCb.checked) types.push("series");
          currentTypes[key] = types;
        });
      }
      // Merge: persisted base, overridden by current UI selections
      const mergedTypes = { ...savedServiceTypes, ...currentTypes };

      setTestResult(statusEl, "Loading…", "");
      fpLoadBtn.disabled = true;

      try {
        const resp = await fetch(`/api/flixpatrol/preview?country=${encodeURIComponent(country)}`);
        const data = await resp.json();
        if (data.error) {
          setTestResult(statusEl, `❌ ${data.error}`, "error");
        } else {
          setTestResult(statusEl, `✅ ${data.services.length} services found`, "success");
          if (data.cache) updateFpCacheStatus(data.cache);
          renderFlixPatrolServices(data.services, savedChecked, mergedTypes);
        }
      } catch (err) {
        setTestResult(statusEl, `❌ ${err.message}`, "error");
      } finally {
        fpLoadBtn.disabled = false;
      }
    });
  }

  // ── FlixPatrol refresh button ──
  const fpRefreshBtn = document.getElementById("fpRefreshBtn");
  if (fpRefreshBtn) {
    fpRefreshBtn.addEventListener("click", async () => {
      const statusEl = document.getElementById("fpLoadStatus");
      setTestResult(statusEl, "Refreshing…", "");
      fpRefreshBtn.disabled = true;
      if (fpLoadBtn) fpLoadBtn.disabled = true;
      try {
        const resp = await fetch("/api/flixpatrol/refresh", { method: "POST" });
        const data = await resp.json();
        if (data.cache) updateFpCacheStatus(data.cache);
        if (data.status === "ok") {
          setTestResult(statusEl, `✅ Refreshed — ${data.services.length} service(s) found`, "success");
        } else if (data.status === "stale") {
          setTestResult(statusEl, `⚠ Using stale data — ${data.error}`, "error");
        } else {
          setTestResult(statusEl, `❌ ${data.error || "Refresh failed"}`, "error");
        }
      } catch (err) {
        setTestResult(statusEl, `❌ ${err.message}`, "error");
      } finally {
        fpRefreshBtn.disabled = false;
        if (fpLoadBtn) fpLoadBtn.disabled = false;
      }
    });
  }


  // ── Plex test connection ──
  const plexTestBtn = document.getElementById("plexTestBtn");
  if (plexTestBtn) {
    plexTestBtn.addEventListener("click", async () => {
      const resultEl = document.getElementById("plexTestResult");
      const url = document.querySelector('[name="plex_url"]')?.value.trim() || "";
      const tokenEl = document.querySelector('[name="plex_token"]');
      const token = tokenEl ? tokenEl.value.trim() : "";
      setTestResult(resultEl, "Testing…", "");
      plexTestBtn.disabled = true;
      try {
        const resp = await fetch("/api/test/plex", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, token }),
        });
        const data = await resp.json();
        if (data.status === "ok") {
          setTestResult(resultEl, `✅ ${data.message}`, "success");
        } else {
          setTestResult(resultEl, `❌ ${data.message}`, "error");
        }
      } catch (err) {
        setTestResult(resultEl, `❌ ${err.message}`, "error");
      } finally {
        plexTestBtn.disabled = false;
      }
    });
  }

  // ── Plex sync collections ──
  const plexSyncBtn = document.getElementById("plexSyncBtn");
  if (plexSyncBtn) {
    plexSyncBtn.addEventListener("click", async () => {
      const statusEl = document.getElementById("plexSyncStatus");
      setTestResult(statusEl, "Syncing…", "");
      plexSyncBtn.disabled = true;
      try {
        const resp = await fetch("/api/plex/sync", { method: "POST" });
        const data = await resp.json();
        if (data.ok) {
          setTestResult(
            statusEl,
            `✅ Done — ${data.movie_count} movies, ${data.tv_count} TV (+${data.added}/-${data.removed})`,
            "success"
          );
        } else {
          setTestResult(statusEl, `❌ ${data.error || "Sync failed"}`, "error");
        }
      } catch (err) {
        setTestResult(statusEl, `❌ ${err.message}`, "error");
      } finally {
        plexSyncBtn.disabled = false;
      }
    });
  }

  // ── Plex remove collections ──
  const plexRemoveBtn = document.getElementById("plexRemoveBtn");
  if (plexRemoveBtn) {
    plexRemoveBtn.addEventListener("click", async () => {
      if (!confirm("Remove all Streamarr collections from Plex?\n\nThis deletes the Streamarr, Netflix, Disney+, and other service collections. They can be recreated by syncing again.")) return;
      const statusEl = document.getElementById("plexSyncStatus");
      setTestResult(statusEl, "Removing…", "");
      plexRemoveBtn.disabled = true;
      try {
        const resp = await fetch("/api/plex/collections", { method: "DELETE" });
        const data = await resp.json();
        if (data.ok) {
          setTestResult(statusEl, `✅ Removed ${data.removed} collection${data.removed !== 1 ? "s" : ""}`, "success");
        } else {
          setTestResult(statusEl, `❌ ${data.error || "Remove failed"}`, "error");
        }
      } catch (err) {
        setTestResult(statusEl, `❌ ${err.message}`, "error");
      } finally {
        plexRemoveBtn.disabled = false;
      }
    });
  }

  // ── Test connection buttons ──
  document.querySelectorAll(".test-conn-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const service = btn.dataset.service;
      const resultEl = document.getElementById(`${service}TestResult`);

      if (service === "pushover") {
        const keyEl = document.querySelector('[name="pushover_user_key"]');
        const tokenEl = document.querySelector('[name="pushover_api_token"]');
        const user_key = keyEl ? keyEl.value.trim() : "";
        const api_token = tokenEl ? tokenEl.value.trim() : "";
        setTestResult(resultEl, "Sending…", "");
        btn.disabled = true;
        try {
          const resp = await fetch("/api/test/pushover", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_key, api_token }),
          });
          const data = await resp.json();
          if (data.status === "ok") {
            setTestResult(resultEl, `✅ ${data.message}`, "success");
          } else {
            setTestResult(resultEl, `❌ ${data.message}`, "error");
          }
        } catch (err) {
          setTestResult(resultEl, `❌ ${err.message}`, "error");
        } finally {
          btn.disabled = false;
        }
        return;
      }

      const urlEl = document.querySelector(`[name="${service}_url"]`);
      const keyEl = document.querySelector(`[name="${service}_api_key"]`);
      const url = urlEl ? urlEl.value.trim() : "";
      const api_key = keyEl ? keyEl.value.trim() : "";

      setTestResult(resultEl, "Testing…", "");
      btn.disabled = true;

      try {
        const resp = await fetch(`/api/test/${service}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, api_key }),
        });
        const data = await resp.json();

        if (data.status === "ok") {
          setTestResult(resultEl, `✅ ${data.message}`, "success");
          if (data.quality_profiles && data.quality_profiles.length) {
            const qName = service === "radarr" ? "radarr_quality_profile_id" : "sonarr_quality_profile_id";
            const curQ = document.querySelector(`[name="${qName}"]`)?.value ?? "1";
            replaceWithSelect(qName, data.quality_profiles.map((p) => ({ value: p.id, label: p.name })), curQ);
          }
          if (data.root_folders && data.root_folders.length) {
            const fName = service === "radarr" ? "root_folder_movies" : "root_folder_series";
            const curF = document.querySelector(`[name="${fName}"]`)?.value ?? "";
            replaceWithSelect(fName, data.root_folders.map((p) => ({ value: p, label: p })), curF);
          }
        } else {
          setTestResult(resultEl, `❌ ${data.message}`, "error");
        }
      } catch (err) {
        setTestResult(resultEl, `❌ ${err.message}`, "error");
      } finally {
        btn.disabled = false;
      }
    });
  });

  // ── Removal schedule ──
  const removalBody = document.getElementById("removalScheduleBody");
  if (removalBody) {
    loadRemovalSchedule(removalBody);
  }

  const removalSearchInput = document.getElementById("removalSearchInput");
  if (removalSearchInput) {
    removalSearchInput.addEventListener("keyup", (e) => {
      const q = e.target.value.toLowerCase().trim();
      document.querySelectorAll("#removalScheduleBody tr").forEach((row) => {
        const title = row.querySelector("td")?.textContent.toLowerCase() || "";
        row.style.display = !q || title.includes(q) ? "" : "none";
      });
    });
  }

  // ── Removal history ──
  const historyBody = document.getElementById("removalHistoryBody");
  if (historyBody) {
    loadRemovalHistory(historyBody);
  }

  // ── Addition history ──
  const additionBody = document.getElementById("additionHistoryBody");
  if (additionBody) {
    loadAdditionHistory(additionBody);
  }

  // ── Protection manager ──
  const protectionPanel = document.getElementById("protectionPanel");
  if (protectionPanel) {
    loadProtectionState(protectionPanel);
  }

  const activeWatchesPanel = document.getElementById("activeWatchesPanel");
  if (activeWatchesPanel) {
    loadActiveWatches(activeWatchesPanel);
  }

  // ── Top 10 rank indicators ──
  const top10Items = document.querySelectorAll(".top10-item[data-title]");
  if (top10Items.length) {
    _applyRankIndicators();
    try {
      const cached = localStorage.getItem("top10-status-cache");
      if (cached) _applyTop10Data(JSON.parse(cached));
    } catch { /* ignore */ }
    loadTop10Status();
  }

  // ── Live log panel ──
  const logOutput = document.getElementById("logOutput");
  if (logOutput) {
    const pauseBtn = document.getElementById("logsPauseBtn");
    const clearBtn = document.getElementById("logsClearBtn");
    const downloadBtn = document.getElementById("logsDownloadBtn");
    const statusBadge = document.getElementById("logStatusBadge");
    let logPaused = false;
    let lastSnapshot = "";
    let currentLines = [];

    if (pauseBtn) {
      pauseBtn.addEventListener("click", () => {
        logPaused = !logPaused;
        pauseBtn.textContent = logPaused ? "Resume" : "Pause";
        if (statusBadge) {
          statusBadge.textContent = logPaused ? "Paused" : "Live";
          statusBadge.classList.toggle("paused", logPaused);
        }
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener("click", async () => {
        try {
          await fetch("/api/logs/clear", { method: "POST" });
        } catch { /* ignore */ }
        currentLines = [];
        lastSnapshot = "";
        logOutput.innerHTML = '<div class="log-empty">Log cleared.</div>';
      });
    }

    const copyBtn = document.getElementById("logsCopyBtn");
    if (copyBtn) {
      copyBtn.addEventListener("click", async () => {
        if (!currentLines.length) return;
        await navigator.clipboard.writeText(currentLines.join("\n"));
        const original = copyBtn.textContent;
        copyBtn.textContent = "Copied!";
        setTimeout(() => { copyBtn.textContent = original; }, 1500);
      });
    }

    if (downloadBtn) {
      downloadBtn.addEventListener("click", () => {
        const blob = new Blob([currentLines.join("\n")], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `streamarr-${new Date().toISOString().slice(0, 10)}.log`;
        a.click();
        URL.revokeObjectURL(url);
      });
    }

    async function fetchLogs() {
      // Only poll when the logs tab is visible — skip silently otherwise.
      const logTab = document.getElementById("tab-logs");
      if (logPaused || !logTab?.classList.contains("active")) return;
      try {
        const resp = await fetch("/api/logs");
        const data = await resp.json();
        const lines = data.lines || [];
        const snapshot = lines.join("\n");
        if (snapshot === lastSnapshot) return;
        lastSnapshot = snapshot;
        currentLines = lines;
        renderLogs(logOutput, lines);
      } catch { /* ignore */ }
    }

    // Trigger an immediate fetch when the user navigates to the logs tab.
    document.querySelectorAll(".topnav a[data-tab-target='logs']").forEach((link) => {
      link.addEventListener("click", () => fetchLogs());
    });

    setInterval(fetchLogs, 3000);
  }

  updateNextSync();
  checkConnections();
});

async function checkConnections() {
  const items = document.querySelectorAll(".integration-item[data-service]");
  if (!items.length) return;
  items.forEach((item) => {
    const el = item.querySelector(".conn-status");
    if (el && item.dataset.mode !== "disabled") el.textContent = "…";
  });
  try {
    const resp = await fetch("/api/connection-status");
    if (!resp.ok) return;
    const data = await resp.json();
    items.forEach((item) => {
      const service = item.dataset.service;
      const el = item.querySelector(".conn-status");
      if (!el || !(service in data)) return;
      if (data[service].ok) {
        el.textContent = "Connected";
        el.style.color = "#2ecf7d";
      } else {
        el.textContent = "Error";
        el.style.color = "#e05252";
      }
    });
  } catch { /* ignore */ }
}

async function updateNextSync() {
  const el = document.getElementById("nextSyncDisplay");
  if (!el) return;
  try {
    const resp = await fetch("/api/sync-status");
    if (!resp.ok) return;
    const data = await resp.json();
    if (!data.last_sync_ts || !data.run_interval_seconds) return;
    const nextTs = data.last_sync_ts + data.run_interval_seconds;
    function render() {
      const diffSec = Math.round(nextTs - Date.now() / 1000);
      if (diffSec <= 0) {
        el.textContent = "Overdue";
        el.style.color = "#e05252";
      } else {
        const totalMin = Math.floor(diffSec / 60);
        const hrs = Math.floor(totalMin / 60);
        const min = totalMin % 60;
        el.textContent = hrs >= 1 ? `in ${hrs}h ${min}m` : `in ${totalMin}m`;
        el.style.color = "";
      }
    }
    render();
    setInterval(render, 60_000);
  } catch { /* ignore */ }
}

function _applyRankIndicators() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  document.querySelectorAll(".top10-item[data-rank]").forEach((li) => {
    if (li.querySelector(".rank-badge")) return;

    const rank = parseInt(li.dataset.rank, 10);
    const prevRank = li.dataset.prevRank ? parseInt(li.dataset.prevRank, 10) : null;
    const firstSeen = li.dataset.firstSeen || null;

    const seenDate = firstSeen ? new Date(firstSeen) : null;
    seenDate && seenDate.setHours(0, 0, 0, 0);
    const daysSinceSeen = seenDate ? Math.round((today - seenDate) / 86400000) : null;
    const isNew = daysSinceSeen !== null && daysSinceSeen < 2;

    if (isNew) {
      const badge = document.createElement("span");
      badge.className = "rank-badge rank-badge--new";
      badge.textContent = "NEW";
      li.prepend(badge);
    } else if (prevRank !== null && rank < prevRank) {
      const badge = document.createElement("span");
      badge.className = "rank-badge rank-badge--up";
      badge.textContent = "↑";
      li.prepend(badge);
    } else if (prevRank !== null && rank > prevRank) {
      const badge = document.createElement("span");
      badge.className = "rank-badge rank-badge--down";
      badge.textContent = "↓";
      li.prepend(badge);
    }

    if (firstSeen) {
      const seenDate = new Date(firstSeen);
      seenDate.setHours(0, 0, 0, 0);
      const days = Math.round((today - seenDate) / 86400000);
      if (days > 0) {
        const daysEl = document.createElement("span");
        daysEl.className = "rank-days";
        daysEl.title = `In Top 10 for ${days} day${days === 1 ? "" : "s"}`;
        daysEl.textContent = `${days}d`;
        li.appendChild(daysEl);
      }
    }
  });
}

function _applyTop10Data(all) {
  document.querySelectorAll(".top10-item[data-title]").forEach((li) => {
    const title = li.dataset.title;
    const item = all[title];
    if (!item) return;
    const { status, poster } = item;

    li.querySelectorAll(".top10-status, .top10-dismiss, .top10-undo").forEach((el) => el.remove());
    li.classList.toggle("top10-item--dismissed", !!item.dismissed);
    li.classList.toggle("top10-item--has-poster", !!poster);
    li.classList.toggle("top10-item--no-poster", !poster);
    if (poster) {
      li.style.setProperty("--poster-url", `url(${poster})`);
    } else {
      li.style.removeProperty("--poster-url");
    }

    if (item.dismissed) {
      if (item.undo_until && Date.now() < Date.parse(item.undo_until)) {
        const undo = document.createElement("button");
        undo.className = "top10-undo";
        undo.title = "Undo dismiss";
        undo.textContent = "↩";
        undo.addEventListener("click", async (e) => {
          e.stopPropagation();
          try {
            await fetch("/api/dismiss", {
              method: "DELETE",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ title }),
            });
            await loadTop10Status();
          } catch { /* ignore */ }
        });
        li.appendChild(undo);
      }
      return;
    }

    const dismiss = document.createElement("button");
    dismiss.className = "top10-dismiss";
    dismiss.title = "Dismiss — skip on future syncs and remove from library";
    dismiss.textContent = "×";
    dismiss.addEventListener("click", async (e) => {
      e.stopPropagation();
      const in_library = status !== "will_add" && status !== "disabled";
      try {
        await fetch("/api/dismiss", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, type: item.type, in_library }),
        });
        await loadTop10Status();
      } catch { /* ignore */ }
    });
    li.prepend(dismiss);

    if (!STATUS_ICONS[status]) return;
    const span = document.createElement("span");
    span.className = "top10-status";
    span.title = STATUS_LABELS[status] || "";
    span.textContent = STATUS_ICONS[status];
    li.appendChild(span);

  });
}

async function loadTop10Status() {
  try {
    const resp = await fetch("/api/top10-status");
    const data = await resp.json();
    const all = { ...data.movies, ...data.series };
    try { localStorage.setItem("top10-status-cache", JSON.stringify(all)); } catch { /* ignore */ }
    _applyTop10Data(all);
  } catch { /* ignore */ }
}

async function loadRemovalSchedule(tbody) {
  try {
    const resp = await fetch("/api/removal-schedule");
    const data = await resp.json();
    renderSchedule(tbody, data.schedule || []);
  } catch {
    tbody.innerHTML = '<tr><td colspan="7" class="table-empty">Failed to load removal schedule.</td></tr>';
  }
}

async function loadAdditionHistory(tbody) {
  try {
    const resp = await fetch("/api/addition-history");
    const data = await resp.json();
    renderAdditionHistory(tbody, data.additions || []);
  } catch {
    tbody.innerHTML = '<tr><td colspan="4" class="table-empty">Failed to load addition history.</td></tr>';
  }
}

function fmtSource(key) {
  return key === "flixpatrol" ? "FlixPatrol" : key.charAt(0).toUpperCase() + key.slice(1);
}

function renderAdditionHistory(tbody, additions) {
  if (!additions.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="table-empty">No titles added in the last 7 days.</td></tr>';
    return;
  }
  tbody.innerHTML = additions.map((item) => {
    const srcs = (item.sources || (item.source ? [item.source] : [])).map(fmtSource).join(" + ");
    return `<tr>
    <td>${escHtml(item.title)}</td>
    <td style="text-transform:capitalize">${escHtml(item.type)}</td>
    <td>${escHtml(item.date_added)}</td>
    <td>${escHtml(srcs)}</td>
  </tr>`;
  }).join("");
}

async function loadRemovalHistory(tbody) {
  try {
    const resp = await fetch("/api/removal-history");
    const data = await resp.json();
    renderHistory(tbody, data.history || []);
  } catch {
    tbody.innerHTML = '<tr><td colspan="5" class="table-empty">Failed to load removal history.</td></tr>';
  }
}

function renderSchedule(tbody, schedule) {
  if (!schedule.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="table-empty">No <code>streamarr</code> tagged titles found in Radarr / Sonarr.</td></tr>';
    return;
  }
  tbody.innerHTML = schedule.map((item) => {
    const daysClass =
      item.days_remaining < 0 ? "days-urgent" :
      item.days_remaining <= 7 ? "days-urgent" :
      item.days_remaining <= 14 ? "days-warning" : "days-ok";
    const daysLabel = item.days_remaining < 0 ? "Overdue" : `${item.days_remaining}d`;
    const statusCell = item.protected
      ? '<span class="protected-badge">Protected</span>'
      : '<span style="color:var(--muted)">—</span>';
    let actionCell;
    const src = item.protection_source;
    if (src === "tautulli" || src === "both") {
      actionCell = '<span class="prot-lock-label">Tautulli</span>';
    } else if (item.protected) {
      actionCell = `<button class="button button-secondary button-sm sched-prot-btn" data-title="${escHtml(item.title)}" data-type="${escHtml(item.type)}" data-protect="false">Unprotect</button>`;
    } else {
      actionCell = `<button class="button button-secondary button-sm sched-prot-btn sched-prot-btn--protect" data-title="${escHtml(item.title)}" data-type="${escHtml(item.type)}" data-protect="true">Protect</button>`;
    }
    return `<tr>
      <td>${escHtml(item.title)}</td>
      <td style="text-transform:capitalize">${escHtml(item.type)}</td>
      <td>${item.date_added}</td>
      <td>${item.removal_date}</td>
      <td>${statusCell}</td>
      <td><span class="${daysClass}">${daysLabel}</span></td>
      <td>${actionCell}</td>
    </tr>`;
  }).join("");
  tbody.querySelectorAll(".sched-prot-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const protecting = btn.dataset.protect === "true";
      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Saving…";
      try {
        const resp = await fetch("/api/overrides", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: btn.dataset.title, type: btn.dataset.type, protected: protecting }),
        });
        if (!resp.ok) throw new Error("Request failed");
        loadRemovalSchedule(tbody);
        const pp = document.getElementById("protectionPanel");
        if (pp) loadProtectionState(pp);
      } catch {
        btn.textContent = originalText;
        btn.disabled = false;
      }
    });
  });
}

function renderHistory(tbody, history) {
  if (!history.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="table-empty">No titles have been removed yet.</td></tr>';
    return;
  }
  tbody.innerHTML = history.map((item) => `<tr>
    <td>${escHtml(item.title)}</td>
    <td style="text-transform:capitalize">${escHtml(item.type)}</td>
    <td>${escHtml(item.date_removed)}</td>
    <td>${escHtml(item.reason)}</td>
    <td>${item.was_watched ? "✅" : "—"}</td>
  </tr>`).join("");
}

async function loadProtectionState(container) {
  container.innerHTML = '<p style="color:var(--muted);font-size:0.9rem;margin:0">Loading…</p>';
  try {
    const resp = await fetch("/api/protection-state");
    const data = await resp.json();
    renderProtectionState(container, data);
  } catch {
    container.innerHTML = '<p style="color:var(--muted);font-size:0.9rem;margin:0">Failed to load protection state.</p>';
  }
}

function renderProtectionState(container, data) {
  const protectedItems = data.protected || [];
  const unprotectedItems = data.unprotected || [];

  if (!protectedItems.length && !unprotectedItems.length) {
    container.innerHTML = '<p style="color:var(--muted);font-size:0.9rem;margin:0">No <code>streamarr</code> tagged titles found. Run a sync to populate.</p>';
    return;
  }

  container.innerHTML = `
    <div class="prot-search-wrap">
      <input type="text" id="protSearchInput" class="prot-search" placeholder="Search titles…">
    </div>
    <div class="protection-manager">
      <div class="protection-column">
        <div class="prot-col-header">
          <input type="checkbox" class="prot-sel-all" id="protSelAllProtected">
          <h3 class="prot-col-title">Protected</h3>
          <span class="prot-count prot-count--protected">${protectedItems.length}</span>
          <button class="button button-secondary button-sm prot-batch-btn" id="protUnprotectSelected">Unprotect Selected</button>
        </div>
        <ul class="prot-list" id="protMgrProtectedList"></ul>
      </div>
      <div class="protection-column">
        <div class="prot-col-header">
          <input type="checkbox" class="prot-sel-all" id="protSelAllUnprotected">
          <h3 class="prot-col-title">Not Protected</h3>
          <span class="prot-count prot-count--unprotected">${unprotectedItems.length}</span>
          <button class="button button-secondary button-sm prot-batch-btn prot-batch-btn--protect" id="protProtectSelected">Protect Selected</button>
        </div>
        <ul class="prot-list" id="protMgrUnprotectedList"></ul>
      </div>
    </div>`;

  // Search
  document.getElementById("protSearchInput").addEventListener("keyup", (e) => {
    const q = e.target.value.toLowerCase().trim();
    container.querySelectorAll(".prot-entry").forEach((li) => {
      const t = li.querySelector(".prot-entry-title")?.textContent.toLowerCase() || "";
      li.style.display = !q || t.includes(q) ? "" : "none";
    });
  });

  // Select-all: protected (only non-disabled checkboxes)
  document.getElementById("protSelAllProtected").addEventListener("change", (e) => {
    document.querySelectorAll("#protMgrProtectedList .prot-entry-cb:not(:disabled)").forEach((cb) => {
      cb.checked = e.target.checked;
    });
  });

  // Select-all: unprotected
  document.getElementById("protSelAllUnprotected").addEventListener("change", (e) => {
    document.querySelectorAll("#protMgrUnprotectedList .prot-entry-cb").forEach((cb) => {
      cb.checked = e.target.checked;
    });
  });

  // Batch unprotect
  document.getElementById("protUnprotectSelected").addEventListener("click", async () => {
    const checked = [...document.querySelectorAll("#protMgrProtectedList .prot-entry-cb:checked:not(:disabled)")];
    if (!checked.length) return;
    await fetch("/api/overrides/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        items: checked.map(cb => ({ title: cb.dataset.title, type: cb.dataset.type })),
        protected: false,
      }),
    });
    await loadProtectionState(container);
  });

  // Batch protect
  document.getElementById("protProtectSelected").addEventListener("click", async () => {
    const checked = [...document.querySelectorAll("#protMgrUnprotectedList .prot-entry-cb:checked")];
    if (!checked.length) return;
    await fetch("/api/overrides/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        items: checked.map(cb => ({ title: cb.dataset.title, type: cb.dataset.type })),
        protected: true,
      }),
    });
    await loadProtectionState(container);
  });

  const _SRC_LABELS = { tautulli: "Tautulli", manual: "Manual", both: "Both" };

  function _makeEntry(item, isProtected) {
    const isTautulli = item.source === "tautulli" || item.source === "both";
    const li = document.createElement("li");
    li.className = "prot-entry";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.className = "prot-entry-cb";
    cb.value = item.title;
    cb.dataset.title = item.title;
    cb.dataset.type = item.type;
    if (isProtected) cb.disabled = isTautulli;
    li.appendChild(cb);

    const meta = document.createElement("div");
    meta.className = "prot-entry-meta";

    const titleEl = document.createElement("span");
    titleEl.className = "prot-entry-title";
    titleEl.textContent = item.title;

    const typeBadge = document.createElement("span");
    typeBadge.className = "prot-entry-type";
    typeBadge.textContent = item.type;

    meta.append(titleEl, typeBadge);

    if (isProtected && item.source) {
      const srcClass = item.source === "both" ? "tautulli" : item.source;
      const sourceBadge = document.createElement("span");
      sourceBadge.className = `prot-source-badge prot-source-badge--${srcClass}`;
      sourceBadge.textContent = _SRC_LABELS[item.source] || item.source;
      meta.appendChild(sourceBadge);
    }

    if (item.reason) {
      const reasonEl = document.createElement("span");
      reasonEl.className = "entry-reason";
      reasonEl.textContent = item.reason;
      meta.appendChild(reasonEl);
    }

    li.appendChild(meta);

    if (isProtected) {
      if (isTautulli) {
        const lock = document.createElement("span");
        lock.className = "prot-lock-label";
        lock.textContent = "Tautulli protected";
        li.appendChild(lock);
      } else {
        const btn = document.createElement("button");
        btn.className = "button button-secondary button-sm prot-action-btn";
        btn.textContent = "Unprotect";
        btn.addEventListener("click", () => handleProtectionToggle(btn, item.title, item.type, false, container));
        li.appendChild(btn);
      }
    } else {
      const btn = document.createElement("button");
      btn.className = "button button-secondary button-sm prot-action-btn prot-action-btn--protect";
      btn.textContent = "Protect";
      btn.addEventListener("click", () => handleProtectionToggle(btn, item.title, item.type, true, container));
      li.appendChild(btn);
    }

    return li;
  }

  const protList = document.getElementById("protMgrProtectedList");
  protectedItems.forEach((item) => protList.appendChild(_makeEntry(item, true)));

  const unprotList = document.getElementById("protMgrUnprotectedList");
  unprotectedItems.forEach((item) => unprotList.appendChild(_makeEntry(item, false)));
}

async function handleProtectionToggle(btn, title, type, protect, container) {
  btn.disabled = true;
  try {
    const resp = await fetch("/api/overrides", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, type, protected: protect }),
    });
    if (!resp.ok) throw new Error("Request failed");
    await loadProtectionState(container);
  } catch {
    btn.disabled = false;
  }
}

async function loadActiveWatches(container) {
  try {
    const resp = await fetch("/api/active-watches");
    const data = await resp.json();
    renderActiveWatches(container, data);
  } catch {
    container.innerHTML = '<p style="color:var(--muted);font-size:0.9rem;margin:0">Failed to load watch history.</p>';
  }
}

function renderActiveWatches(container, data) {
  const items = data.items || [];
  if (!items.length) {
    container.innerHTML = '<p style="color:var(--muted);font-size:0.9rem;margin:0">No watch history found for managed titles.</p>';
    return;
  }
  const rows = items.map(item => `
    <tr>
      <td>${escHtml(item.title)}</td>
      <td>${item.type === "movie" ? "Movie" : "Series"}</td>
      <td>${escHtml(item.last_watched)}</td>
    </tr>`).join("");
  container.innerHTML = `
    <table class="removal-table">
      <thead>
        <tr><th>Title</th><th>Type</th><th>Last watched</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setTestResult(el, text, state) {
  if (!el) return;
  el.textContent = text;
  el.className = "test-conn-result";
  if (state) el.classList.add(`test-conn-result--${state}`);
}

function replaceWithSelect(fieldName, options, currentValue) {
  const el = document.querySelector(`[name="${fieldName}"]`);
  if (!el) return;
  const sel = document.createElement("select");
  sel.name = fieldName;
  options.forEach(({ value, label }) => {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = label;
    if (String(value) === String(currentValue)) opt.selected = true;
    sel.appendChild(opt);
  });
  el.replaceWith(sel);
}

function logLineClass(line) {
  if (/\[ERROR\]/.test(line)) return "log-error";
  if (/\[WARNING\]/.test(line)) return "log-warn";
  if (/\[DEBUG\]/.test(line)) return "log-debug";
  if (/\[INFO\]/.test(line)) return "log-info";
  return "log-default";
}

function renderLogs(container, lines) {
  const atBottom =
    container.scrollHeight - container.scrollTop - container.clientHeight < 40;
  if (!lines.length) {
    container.innerHTML = '<div class="log-empty">No log entries yet.</div>';
    return;
  }
  container.innerHTML = lines
    .map((l) => `<div class="log-line ${logLineClass(l)}">${escHtml(l)}</div>`)
    .join("");
  if (atBottom) container.scrollTop = container.scrollHeight;
}

function updateFpCacheStatus(cache) {
  const el = document.getElementById("fpCacheStatus");
  if (!el || !cache) return;
  let html = "";
  if (cache.cached_at) {
    const ts = new Date(cache.cached_at * 1000);
    const timePart = ts.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const datePart = ts.toLocaleDateString([], { day: "2-digit", month: "2-digit", year: "numeric" });
    html += `<p class="field-help">Last fetched: ${escHtml(timePart + " " + datePart)}`;
    if (cache.is_stale) html += ' <span class="fp-stale-badge">Stale</span>';
    html += "</p>";
  }
  if (cache.banned) {
    html += `<p class="field-help fp-ban-msg">🚫 ${escHtml(cache.error)}</p>`;
  } else if (cache.error) {
    html += `<p class="field-help fp-stale-msg">⚠ ${escHtml(cache.error)}</p>`;
  }
  el.innerHTML = html;
}

function renderFlixPatrolServices(services, checkedKeys = [], serviceTypes = {}) {
  const container = document.getElementById("fpServiceList");
  if (!container) return;

  container.innerHTML = "";

  if (!services.length && !checkedKeys.length) return;

  const rows = services.length
    ? services
    : checkedKeys.map((k) => ({
        key: k,
        label: k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        movie_count: null,
        series_count: null,
      }));

  const grid = document.createElement("div");
  grid.className = "fp-service-grid";

  rows.forEach((svc) => {
    const isChecked = checkedKeys.includes(svc.key);
    const savedTypes = serviceTypes[svc.key];
    const movieChecked = !savedTypes || savedTypes.includes("movie");
    const seriesChecked = !savedTypes || savedTypes.includes("series");

    const card = document.createElement("div");
    card.className = "fp-service-card";

    const name = document.createElement("div");
    name.className = "fp-card-name";
    name.textContent = svc.label;
    card.appendChild(name);

    const enableLabel = document.createElement("label");
    enableLabel.className = "setting-checkbox";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.name = "flixpatrol_services";
    cb.value = svc.key;
    cb.checked = isChecked;
    cb.className = "fp-service-cb";

    enableLabel.appendChild(cb);
    enableLabel.appendChild(document.createTextNode(" Enable"));
    card.appendChild(enableLabel);

    const typeToggles = document.createElement("div");
    typeToggles.className = "fp-type-toggles fp-card-types";

    [["movie", "Movies"], ["series", "TV"]].forEach(([type, label]) => {
      const typeLabel = document.createElement("label");
      typeLabel.className = "fp-type-label";

      const typeCb = document.createElement("input");
      typeCb.type = "checkbox";
      typeCb.className = "fp-type-cb";
      typeCb.dataset.service = svc.key;
      typeCb.dataset.type = type;
      typeCb.checked = type === "movie" ? movieChecked : seriesChecked;

      typeLabel.appendChild(typeCb);
      typeLabel.appendChild(document.createTextNode(" " + label));
      typeToggles.appendChild(typeLabel);
    });

    card.appendChild(typeToggles);

    if (svc.movie_count !== null) {
      const counts = document.createElement("div");
      counts.className = "fp-service-counts";
      if (svc.movie_count > 0) {
        const mc = document.createElement("span");
        mc.className = "fp-count-badge fp-count-badge--movie";
        mc.textContent = `${svc.movie_count} movies`;
        counts.appendChild(mc);
      }
      if (svc.series_count > 0) {
        const sc = document.createElement("span");
        sc.className = "fp-count-badge fp-count-badge--series";
        sc.textContent = `${svc.series_count} series`;
        counts.appendChild(sc);
      }
      card.appendChild(counts);
    }

    grid.appendChild(card);
  });

  container.appendChild(grid);

  const toggleRow = document.createElement("div");
  toggleRow.className = "fp-toggle-row";

  const selAll = document.createElement("button");
  selAll.type = "button";
  selAll.className = "button button-secondary button-sm";
  selAll.textContent = "Select all";
  selAll.addEventListener("click", () => {
    container.querySelectorAll(".fp-service-cb").forEach((cb) => { cb.checked = true; });
  });

  const selNone = document.createElement("button");
  selNone.type = "button";
  selNone.className = "button button-secondary button-sm";
  selNone.textContent = "Select none";
  selNone.addEventListener("click", () => {
    container.querySelectorAll(".fp-service-cb").forEach((cb) => { cb.checked = false; });
  });

  toggleRow.appendChild(selAll);
  toggleRow.appendChild(selNone);
  container.appendChild(toggleRow);
}