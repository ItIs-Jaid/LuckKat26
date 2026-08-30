# DevSecLocHostOps — Local Dashboard + Localhost Interaction Metrics

**Goal:** one cohesive local-first app. Mature existing KB dashboard (FastAPI + `kb/kb.db` read-only + virtualized cyberpunk GUI) **plus a new localhost-interaction-metrics layer** backed by a dedicated SQLite `metrics.db`, surfaced back into the GUI as a dashboard. Runs fully local, push-ready to public GitHub (foreign `localhostops` tree excluded by `.gitignore`).

**Execution model:** Lead → 3 Supervisor orchestrators (disjoint file ownership) → Leaf workers. Each tier verifies with real tests before returning.

---

## Layers (kept separate so they evolve independently)

1. **DB layer** — new `dashboard/metrics.py` owns a dedicated SQLite `metrics.db` (read-write): signed-cookie issue/validate, `log_event(...)`, aggregation queries. `kb/kb.db` stays **read-only** (security: safe over NAS share, never polluted).
2. **Python run layer** — `dashboard/server.py` mounts a `metrics.router` (APIRouter): sets the signed cookie on `/`, accepts `POST /api/metrics`, serves `GET /api/metrics/summary`. Binds `127.0.0.1` only. Existing KB endpoints unchanged.
3. **GUI** — `dashboard/static/index.html` adds an **INTERACTION METRICS** panel from `/api/metrics/summary`; JS `track(event, table, meta)` POSTs on table-select / search / sort / row-open. Existing virtualized table untouched; all output escaped via existing `esc()`.
4. **Tests** — new `dashboard/tests/test_metrics.py` + `dashboard/tests/test_integration.py` (+ cohesive boot test). Existing 14 tests stay green. A top-level test boots the whole app to prove **one cohesive running local app**, not fragments.

---

## API contract (LOCKED — all tiers build against these exact values)

- `GET /` → `static/index.html`. On response, set cookie `METRICS_VISITOR` if absent.
- `GET /health` → `{"status":"ok"}` (DB-aware; 503 if KB store unreadable).
- `GET /api/tables` → `[{name, rows, columns:[{name,type,nullable}], searchable}]`
- `GET /api/summary` → `{tables, vuln_severity, tool_category}`
- `GET /api/rows?table=&sort=&dir=&limit=&after=&q=&<col>=<val>` → `{items, next_cursor, total}`
- `GET /api/row/{table}/{id}` → `{row, sources, advisory_keys, provenance_tags}`
- `POST /api/metrics`
  - Body (JSON): `{"event": <str>, "table"?: <str>, "meta"?: <str<=200 chars>}`
  - `event` ∈ `{page_view, table_select, search, sort, row_open, filter}`
  - Requires valid signed `METRICS_VISITOR` cookie. Missing/invalid → `401`. Unknown event → `400`. Returns `{"ok": true, "id": <int>}`.
- `GET /api/metrics/summary` → `{"visits":int, "unique_visitors":int, "events":int, "by_event":{event:count}, "active_sessions":int, "top_tables":[{"table":str,"n":int}]}`
  - `active_sessions` = visitors with an event in the last 30 minutes.

## Cookie scheme (security-critical — verbatim)

- Name: `METRICS_VISITOR`
- Value: `f"{vid}.{sig}"` where `vid = secrets.token_hex(16)` and `sig = hmac.new(METRICS_SECRET, vid.encode(), sha256).hexdigest()`
- Server validates with `hmac.compare_digest` (constant-time). Invalid/missing → treat as no visitor (401 on POST).
- Cookie attributes: `HttpOnly`, `SameSite=Lax`, `Max-Age=31536000`, `Path=/`.
- Secret: env `METRICS_SECRET`. If unset, server.py uses a dev fallback secret and logs a warning (NEVER log the secret).

## DB schema (`metrics.db`, created idempotently by `metrics.py` if missing)

```sql
CREATE TABLE IF NOT EXISTS visitors (
    id         TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    visitor_id  TEXT NOT NULL,
    event       TEXT NOT NULL,
    table_name  TEXT,
    meta        TEXT,
    ts          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_visitor ON events(visitor_id);
CREATE INDEX IF NOT EXISTS idx_events_event   ON events(event);
CREATE INDEX IF NOT EXISTS idx_events_ts      ON events(ts);
```

- `metrics.py` exposes: `init_metrics(path=None)`, `get_metrics_path()`, `issue_visitor() -> (vid, cookie_value)`, `validate_cookie(value) -> vid|None`, `log_event(vid, event, table, meta) -> int`, `summary() -> dict`, and a `MetricsDB`/connection helper. All SQL parameterized.
- Path: env `METRICS_DB_PATH` or default `dashboard/metrics.db` (gitignored via `*.db`, `*.db-wal`, `*.db-shm`).

---

## Test evidence required (all tiers must keep this green)

`dashboard/tests/test_metrics.py`:
- signed cookie round-trips through `issue_visitor()` / `validate_cookie()`; tampered value → `None`.
- `log_event` then `summary()` returns correct `events`, `unique_visitors`, `by_event`, `top_tables`.
- bad event body → `400`; unsigned POST → `401`.
- uses a temp `metrics.db` (fixture), never the live file.

`dashboard/tests/test_integration.py`:
- `TestClient(server.app)` with a real signed cookie → `POST /api/metrics` → `GET /api/metrics/summary` reflects the logged event.
- Full-app boot: `GET /` → 200 (serves html), `/health` → 200, `/api/metrics/summary` → 200.
- Existing 14 KB tests remain green (run from `dashboard/` with `uv run --no-project pytest -q`).

## Security rules (non-negotiable)

- HMAC-signed `HttpOnly` cookie; server validates signature; never trust the raw value.
- Parameterized SQL everywhere; column names whitelisted (no string-concat of values).
- Bind `127.0.0.1` (localhost-only); never expose on `0.0.0.0`.
- No PII in `metrics.db` (only an opaque visitor id + event counters).
- `kb/kb.db` stays read-only (mode=ro); `metrics.db` is the only writable store.
- GUI output escaped via existing `esc()`; never `innerHTML` untrusted data.

## Out-of-scope / GitHub hygiene

Foreign `localhostops` tree (`api/`, `pipeline/`, `data/`, `display/`, `k8s/`, `docker-compose*.yml`, `analysis/`, `docs/pipeline.md`, `.env.example`, `requirements*.txt`) stays gitignored. `dashboard/` itself is committable. Never commit a live `*.db`. Lead does NOT push (local-first boundary) — delivers a verified push-ready branch + continue prompt.

## File ownership (disjoint → supervisors run concurrently)

- **Supervisor A (backend):** `dashboard/metrics.py`, `dashboard/server.py` (router + cookie), `dashboard/tests/test_metrics.py`.
- **Supervisor B (GUI):** `dashboard/static/index.html` (metrics panel + `track()`), `dashboard/tests/test_integration.py` GUI-facing parts.
- **Supervisor C (hygiene/docs):** `.gitignore` scrub, `dashboard/README.md` metrics section, `dashboard/run.sh` env defaults, continue-prompt doc, final `git status`/`git add -A -n` scrub check.
- **Lead (after A/B/C):** `dashboard/tests/test_integration.py` cohesive boot test (reads server), run full suite, live boot + curl cookie→log→summary, verify KB read-only, finalize continue prompt.
