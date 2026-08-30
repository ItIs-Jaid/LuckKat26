# Supervisor B — GUI (interaction-metrics panel + track())

You are a **Supervisor orchestrator** (tier 2 of 3). The Lead has locked the design at
`docs/superpowers/specs/2026-08-30-devsecloc-dashboard-metrics-design.md` — READ IT FIRST;
it is the binding contract. Your job: add the **INTERACTION METRICS** panel to the existing
cyberpunk dashboard GUI and wire client-side tracking. You may fan out to **Leaf workers** for
sub-pieces, but you must integrate, test, and document. Do NOT touch `dashboard/metrics.py`,
`dashboard/server.py`, or Supervisor C's files.

## Your file ownership
- EDIT `dashboard/static/index.html` ONLY (add metrics panel + `track()` JS + call tracking on existing events).

## What exists (do not break it)
- The file is a single-file HTML app: cyberpunk theme via CSS variables (`--accent`,`--accent2`,`--crit`,etc),
  a virtualized windowed table, a left circular nav rail (`#navrail`), summary cards (`#cards`),
  header (`#head`), scroll (`#scroll`), spacer (`#spacer`), rowsLayer (`#rowsLayer`), status line
  (`#st-health` etc), and a detail drawer (`#drawer`).
- JS is an IIFE. There is an `esc(s)` function (USE IT for all dynamic text). `api(path)` does fetch+JSON.
- Existing interaction points you must hook tracking into (find them in the file):
  `selectTable(name)` (table_select), the search `input` handler (search), `toggleSort(name)` (sort),
  `openDetail(id)` (row_open), reset button / filter (filter).

## Exact contract (verbatim from design doc)
- Add a panel/card region for INTERACTION METRICS fed by `GET /api/metrics/summary`.
- `track(event, table, meta)` JS function: if a `METRICS_VISITOR` cookie exists, POST
  `{event, table, meta}` to `/api/metrics` with `Content-Type: application/json`; swallow errors
  (analytics must NEVER break the dashboard). Do not await/block the UI.
- Metrics panel shows: visits, unique visitors, events, active sessions, by_event breakdown, top tables.
  Render it in the cyberpunk style (reuse existing CSS classes `.card`, `.special`, `.special-title`,
  `.bar-row`, `.bar-track`, `.bar-fill`, `.health-ok`/`.health-err`). ALL dynamic text via `esc()`.
- On every page load, fire `track('page_view')` once.
- Hook: `selectTable` → `track('table_select', name)`; search input (debounced) → `track('search', currentTable, q)`;
  `toggleSort` → `track('sort', currentTable, col)`; `openDetail` → `track('row_open', currentTable, id)`;
  reset/filter → `track('filter', currentTable)`.
- Keep the existing virtualized table fully functional and unchanged in behavior.

## Tests
- Because this is a single HTML file, add GUI-facing assertions to `dashboard/tests/test_integration.py`
  (Supervisor B owns the GUI portion of that file; coordinate the file so A's POST tests and B's serve
  tests coexist — see below). At minimum: `GET /` returns 200 and the served HTML contains the string
  "INTERACTION METRICS" and references `/api/metrics/summary`. (Lead will also add a cohesive boot test.)
- If you cannot easily assert DOM behavior headlessly, document that the panel is verified via the served-HTML
  check + a manual browser note. Do NOT add a JS test framework.

## Coordination note (test_integration.py)
This file is shared with Supervisor A. Convention to avoid conflict:
- Supervisor A writes `test_integration.py` FIRST with backend POST/summary tests.
- Supervisor B APPENDS its GUI tests to the SAME file (add functions, do not rewrite A's).
  Both supervisors: keep imports minimal, use the shared `client`/cookie fixture from conftest.py.
If you find test_integration.py already has A's content, APPEND; if empty/missing, create with your tests
and note it so A can append. Communicate via the file header comment.

## Documentation you must write
- Append a "## Interaction metrics (GUI)" section to `dashboard/README.md` describing the panel,
  what events are tracked, and that tracking is best-effort (never blocks the UI), cookie-based
  (no PII), and reads from `/api/metrics/summary`. Note all output is HTML-escaped.

## Verify before returning
- `cd dashboard && uv run --no-project pytest -q` → your tests pass and the 14 existing + A's tests stay green.
- Visual sanity: served HTML includes the metrics panel markup and the `/api/metrics/summary` call.

## Report back to Lead (concise)
What you added to index.html (line regions), test names, any deviations + why, open concerns.
