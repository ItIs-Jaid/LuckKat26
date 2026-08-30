# agentic DevSecLocHostOps

*Local-first AI agent stack + a self-contained local dashboard. This repository is a WORK IN PROGRESS.*

> **Status: incomplete / work-in-progress.** The code here is real and runs locally, but it is
> not a finished product. Pieces are at different maturity levels (see "Maturity" notes per
> section). Expect rough edges, missing docs, and interfaces that will change. Nothing here
> requires the internet to run.

---

## What this repo contains

Two related but independent parts live in this tree:

1. **The agentic DevSecLocHostOps stack** — documentation for a local-first setup where a
   reasoning agent (Hermes) and its subagent team drive JetBrains IDEs over open protocols
   (MCP / ACP). See `docs/integration-map.md`, `docs/device-inventory.md`, `docs/tool-reference.md`.
2. **The Local Dashboard app** (the part that is actually built and runnable) — a FastAPI +
   SQLite dashboard that browses a local knowledge base and tracks anonymous localhost
   interaction metrics. This is the focus of the three layers below.

---

## The Local Dashboard — three layers

The dashboard is deliberately split into three layers so each can be understood, tested, and
evolved on its own. They connect as: **the JS GUI asks → the Python middle reads the SQL stores
and answers → the GUI renders the result.**

### 1. SQL backend (the data)

Two SQLite databases, kept separate on purpose:

- **`kb/kb.db` — read-only knowledge base.** The source of truth the dashboard browses.
  ~12 tables (languages, libraries, patterns, tutorials, sources, vulnerabilities,
  security_tools, methodologies, code_reviews, errors, research_runs, review_queue). The server
  opens it in `mode=ro` so it can never be written to or locked, even over a network share.
- **`dashboard/metrics.db` — writable interaction store.** A dedicated DB holding only an opaque
  visitor id and anonymous event counters (`visitors` + `events` tables). Created automatically
  on first run. Holds **no PII** (no IP, no user-agent, no content).

Why two stores: the KB is a curated reference; mixing live analytics writes into it would
pollute and risk it. Separation keeps the read path safe and the write path isolated.

Schema (`metrics.db`):

```sql
CREATE TABLE visitors ( id TEXT PRIMARY KEY, created_at TEXT NOT NULL );
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visitor_id TEXT NOT NULL, event TEXT NOT NULL,
    table_name TEXT, meta TEXT, ts TEXT NOT NULL
);
```

### 2. Python middle (the server)

`dashboard/server.py` (FastAPI) is the only writer/reader between the GUI and the SQL.

- **KB read endpoints (read-only):** `GET /api/tables`, `GET /api/summary`,
  `GET /api/rows` (server-side keyset pagination — the table never loads fully into memory),
  `GET /api/row/{table}/{id}`.
- **Metrics endpoints (writable, gated):** `POST /api/metrics` logs an interaction event;
  `GET /api/metrics/summary` aggregates visits / unique visitors / events / active sessions /
  top tables. `GET /` issues a signed `METRICS_VISITOR` cookie when absent.
- **Security posture:** the visitor cookie is HMAC-SHA256 signed and validated with a
  constant-time compare (tampered/missing → `401`); all SQL is parameterized; the server binds
  `127.0.0.1` only (never `0.0.0.0`); `kb/kb.db` is opened read-only. The secret comes from the
  `METRICS_SECRET` env var (dev fallback + warning if unset).
- `dashboard/metrics.py` owns the metrics store; `dashboard/db.py` owns the read-only KB access
  (severity normalization, keyset cursors, source-id joins).

### 3. JS GUI (the frontend)

`dashboard/static/index.html` is a **single self-contained file** — all CSS/JS inline, zero
CDN/outbound requests. Two surfaces:

- **Interaction Metrics panel** (the home view): four stat tiles (visits, unique visitors,
  events, active sessions) plus "by event" and "top tables" breakdowns, fed by
  `GET /api/metrics/summary`. Styled as a dark, rounded, green/blue-accent panel.
- **KB browser** (reachable via three category buttons under the metrics panel — *Browse
  Tables*, *Search*, *Inspect Row*): a virtualized windowed table that renders only the visible
  rows (handles large tables without DOM bloat), sortable headers, a search box, and a row
  detail drawer. Navigation is menu → content → back (no persistent sidebar).

Client-side tracking is best-effort and never blocks the UI: a `track()` function POSTs events
only when the signed cookie is present, and swallows all errors. All dynamic text is set via
`textContent` / an `esc()` helper — no untrusted data reaches `innerHTML`.

---

## Run it

```bash
cd dashboard
./run.sh          # or: .\run.ps1  (creates a .venv via uv, serves http://127.0.0.1:8000)
```

Open http://127.0.0.1:8000. Point at a different KB with `KB_DB_PATH`; the metrics store with
`METRICS_DB_PATH`; set `METRICS_SECRET` for real traffic.

Tests (synthetic fixture DB, no real data needed):

```bash
cd dashboard && uv run --no-project pytest -q
```

---

## Maturity / what is incomplete

- **Dashboard app (this repo's runnable part):** functional end-to-end; 28 tests green. The
  metrics schema and GUI are basic but real.
- **KB content:** the live `kb/kb.db` is local-only and not committed; the app expects it to
  exist on your machine (or set `KB_DB_PATH`).
- **Agentic stack docs (`docs/`):** documented, partially verified (IDE/agent connection not
  yet executed live). Treat as design reference, not a runbook.
- **Deployment artifacts (`k8s/`, `deploy/`, `docker-compose*.yml`):** present as scaffolding
  for a future k3s/NAS deployment of the *foreign* "localhostops" pipeline — **out of scope for
  this dashboard** and excluded from what is documented as production-ready here.
- **No CI, no release, no cloud.** Local-first by design.

*Local-first. Open protocols. You hold the keys.*
