# Template Rules

- Server-rendered Jinja2 only — no frontend frameworks
- Templates display state passed from routes — no business logic in templates
- Dynamic sections are populated by async JS calls to API endpoints
- Use existing CSS classes — do not invent new layout patterns unless necessary
- Keep cards clean — avoid cramming multiple concerns into one section

## UX Requirements

- Always show why something is happening — use the reason field where available
- Protection must clearly show source: manual vs Tautulli
- Deletion must show time remaining
- Top 10 must show accurate availability status
- Prefer async updates over full page reloads