# Template Rules

- Server-rendered Jinja2 only — no frontend frameworks
- Templates display values prepared by routes — no business logic inside templates
- Templates must not attempt to reconstruct or infer backend state
- Dynamic sections are populated by async JS calls to API endpoints
- Use existing CSS classes — do not invent new layout patterns unless necessary

## UX Requirements

- Always show why something is happening — use the reason field where available
- Protection must clearly show source: manual vs Tautulli
- Deletion must show time remaining
- Prefer async updates over full page reloads
