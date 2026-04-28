# Frontend Rules

- Vanilla JS only — no libraries beyond what already exists
- UI reflects API responses directly — no assumption of shared global state model
- All data comes from API endpoints — never derive or compute state in JS
- Use existing helpers: escHtml(), setTestResult(), setStatus(), renderSchedule()
- Never make per-item API calls inside loops — use a single bulk endpoint
- Tab switching is client-side via data-tab-target — do not add page navigations
- Active tab state is managed by JS, not Jinja
