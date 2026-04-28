# Frontend Rules

- Vanilla JS only — no libraries beyond what already exists in the project
- All data comes from API endpoints — never compute state in JS
- Use existing helpers: escHtml(), setTestResult(), setStatus(), renderSchedule(), renderProtectionState(), _makeEntry()
- All dynamic sections load asynchronously on DOMContentLoaded
- Never make per-item API calls inside loops — batch or use a single endpoint
- Tab switching is client-side via data-tab-target attributes — do not add page navigations
- Active tab state is managed by JS, not Jinja