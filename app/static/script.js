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
  const syncResult = document.getElementById("syncResult");
  const settingsForm = document.getElementById("settingsForm");
  const saveResult = document.getElementById("saveResult");

  const setStatus = (element, text, state = "") => {
    element.textContent = text;
    element.classList.remove("success", "error");
    if (state) element.classList.add(state);
  };

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
    syncButton.addEventListener("click", async () => {
      syncButton.disabled = true;
      setStatus(syncResult, "Running sync…");
      try {
        const response = await fetch("/api/sync", { method: "POST" });
        const data = await response.json();
        const r = data.result || {};
        const added = (r.added_movies || []).length + (r.added_series || []).length;
        setStatus(syncResult, `Sync complete — ${added} title(s) added. Refreshing…`, "success");
        setTimeout(() => window.location.reload(), 1500);
      } catch (error) {
        setStatus(syncResult, `Sync failed: ${error.message}`, "error");
        syncButton.disabled = false;
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
      for (const [key, value] of formData.entries()) {
        if (key === "netflix_top_countries") continue;
        payload[key] = value;
      }
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

  // ── Manual override checkboxes ──
  document.querySelectorAll(".override-checkbox").forEach((cb) => {
    cb.addEventListener("change", async () => {
      const title = cb.dataset.title;
      const wasChecked = cb.checked;
      try {
        const resp = await fetch("/api/overrides", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, protected: wasChecked }),
        });
        if (!resp.ok) throw new Error("Request failed");
        const badge = cb.closest(".protection-item").querySelector(".protect-badge--manual");
        if (wasChecked && !badge) {
          const span = document.createElement("span");
          span.className = "protect-badge protect-badge--manual";
          span.textContent = "Override";
          cb.closest(".protection-item").appendChild(span);
        } else if (!wasChecked && badge) {
          badge.remove();
        }
      } catch {
        cb.checked = !wasChecked;
      }
    });
  });

  // ── Test connection buttons ──
  document.querySelectorAll(".test-conn-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const service = btn.dataset.service;
      const resultEl = document.getElementById(`${service}TestResult`);
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

  // ── Top 10 status icons ──
  const top10Items = document.querySelectorAll(".top10-item[data-title]");
  if (top10Items.length) {
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
        a.download = `netflix-sync-${new Date().toISOString().slice(0, 10)}.log`;
        a.click();
        URL.revokeObjectURL(url);
      });
    }

    async function fetchLogs() {
      if (logPaused) return;
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

    fetchLogs();
    setInterval(fetchLogs, 3000);
  }
});

async function loadTop10Status() {
  try {
    const resp = await fetch("/api/top10-status");
    const data = await resp.json();
    const all = { ...data.movies, ...data.series };
    document.querySelectorAll(".top10-item[data-title]").forEach((li) => {
      const title = li.dataset.title;
      const status = all[title];
      if (!status || !STATUS_ICONS[status]) return;
      const span = document.createElement("span");
      span.className = "top10-status";
      span.title = STATUS_LABELS[status] || "";
      span.textContent = STATUS_ICONS[status];
      li.appendChild(span);
    });
  } catch { /* ignore */ }
}

async function loadRemovalSchedule(tbody) {
  try {
    const resp = await fetch("/api/removal-schedule");
    const data = await resp.json();
    renderSchedule(tbody, data.schedule || []);
  } catch {
    tbody.innerHTML = '<tr><td colspan="6" class="table-empty">Failed to load removal schedule.</td></tr>';
  }
}

function renderSchedule(tbody, schedule) {
  if (!schedule.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="table-empty">No <code>netflix-sync</code> tagged titles found in Radarr / Sonarr.</td></tr>';
    return;
  }
  tbody.innerHTML = schedule.map((item) => {
    const daysClass =
      item.days_remaining < 0 ? "days-urgent" :
      item.days_remaining <= 7 ? "days-urgent" :
      item.days_remaining <= 14 ? "days-warning" : "days-ok";
    const daysLabel = item.days_remaining < 0
      ? "Overdue"
      : `${item.days_remaining}d`;
    const statusCell = item.protected
      ? '<span class="protected-badge">Protected</span>'
      : '<span style="color:var(--muted)">—</span>';
    return `<tr>
      <td>${escHtml(item.title)}</td>
      <td style="text-transform:capitalize">${escHtml(item.type)}</td>
      <td>${item.date_added}</td>
      <td>${item.removal_date}</td>
      <td>${statusCell}</td>
      <td><span class="${daysClass}">${daysLabel}</span></td>
    </tr>`;
  }).join("");
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
