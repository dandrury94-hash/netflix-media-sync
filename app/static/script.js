document.addEventListener("DOMContentLoaded", () => {
  const syncButton = document.getElementById("syncButton");
  const syncResult = document.getElementById("syncResult");
  const settingsForm = document.getElementById("settingsForm");
  const saveResult = document.getElementById("saveResult");

  const setStatus = (element, text, state = "") => {
    element.textContent = text;
    element.classList.remove("success", "error");
    if (state) {
      element.classList.add(state);
    }
  };

  if (syncButton) {
    syncButton.addEventListener("click", async () => {
      setStatus(syncResult, "Running sync...");
      try {
        const response = await fetch("/api/sync", { method: "POST" });
        const data = await response.json();
        setStatus(syncResult, `Added ${data.result.added_movies.length} movies, ${data.result.added_series.length} series.`, "success");
      } catch (error) {
        setStatus(syncResult, `Sync failed: ${error.message}`, "error");
      }
    });
  }

  if (settingsForm) {
    settingsForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      setStatus(saveResult, "Saving settings...");
      const formData = new FormData(settingsForm);
      const payload = {};
      payload.netflix_top_countries = formData.getAll("netflix_top_countries");
      for (const [key, value] of formData.entries()) {
        if (key === "netflix_top_countries") {
          continue;
        }
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
});
