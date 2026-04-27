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

  // ── Removal schedule ──
  const removalBody = document.getElementById("removalScheduleBody");
  if (removalBody) {
    loadRemovalSchedule(removalBody);
  }
});

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
