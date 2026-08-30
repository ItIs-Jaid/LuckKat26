# Supervisor A — Backend (metrics layer + API)

You are a **Supervisor orchestrator** (tier 2 of 3). The Lead has locked the design at
`docs/superpowers/specs/2026-08-30-devsecloc-dashboard-metrics-design.md` — READ IT FIRST;
it is the binding contract. Your job: implement the **backend** of the new localhost-interaction-metrics
layer and prove it green. You may fan out to **Leaf workers** (subagents) for sub-pieces, but you
must integrate, test, and document. Do NOT touch files owned by Supervisor B (static/index.html) or C (.gitignore/README/hygiene).

## Your file ownership
- CREATE `dashboard/metrics.py` (DB layer: signed-cookie + log_event + summary over dedicated `metrics.db`)
- EDIT `dashboard/server.py` (mount a metrics APIRouter; set signed cookie on `/`; bind 127.0.0.1)
- CREATE `dashboard/tests/test_metrics.py`

## Exact contract (verbatim from the design doc)
- Cookie `METRICS_VISITOR` = `f"{vid}.{sig}"`; `vid = secrets.token_hex(16)`;
  `sig = hmac.new(METRICS_SECRET, vid.encode(), sha256).hexdigest()`. Validate with `hmac.compare_digest`.
- Cookie attrs: HttpOnly, SameSite=Lax, Max-Age=31536000, Path=/.
- Secret: env `METRICS_SECRET`; if unset, dev fallback secret + log warning (NEVER log the secret).
- `metrics.db` schema (idempotent CREATE TABLE IF NOT EXISTS):
  ```sql
  CREATE TABLE IF NOT EXISTS visitors (id TEXT PRIMARY KEY, created_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, visitor_id TEXT NOT NULL,
    event TEXT NOT NULL, table_name TEXT, meta TEXT, ts TEXT NOT NULL);
  CREATE INDEX IF NOT EXISTS idx_events_visitor ON events(visitor_id);
  CREATE INDEX IF NOT EXISTS idx_events_event ON events(event);
  CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
  ```
- Path: env `METRICS_DB_PATH` or default `dashboard/metrics.db` (gitignored).
- `metrics.py` exposes: `init_metrics(path=None)`, `get_metrics_path()`, `issue_visitor()->(vid,value)`,
  `validate_cookie(value)->vid|None`, `log_event(vid,event,table,meta)->int`, `summary()->dict`.
- `summary()` returns: `visits` (count visitors), `unique_visitors` (same), `events` (count events),
  `by_event` ({event:count}), `active_sessions` (visitors with an event in last 30 min),
  `top_tables` ([{table,n}] by event count, table_name not null).
- API endpoints to ADD in server.py (keep all existing KB endpoints UNCHANGED):
  - On `GET /` response, set `METRICS_VISITOR` cookie if the request has none (use `Response`/`starlette`).
  - `POST /api/metrics` — JSON body `{"event":str,"table"?:str,"meta"?:str<=200}`.
    `event` ∈ {page_view,table_select,search,sort,row_open,filter}.
    Requires valid signed cookie → else 401. Unknown event → 400. Returns `{"ok":true,"id":int}`.
  - `GET /api/metrics/summary` → the `summary()` dict.
  - Bind host `127.0.0.1` (the `uvicorn` call in run.sh already does; ensure server.py importable for tests).
- ALL SQL parameterized. Column names whitelisted. No string-concat of values. kb/kb.db stays read-only (you don't touch db.py).

## Tests (must pass — run from dashboard/ with `uv run --no-project pytest -q`)
- `dashboard/tests/test_metrics.py`: cookie round-trip issue/validate; tampered value → None;
  log_event then summary correct (events, unique_visitors, by_event, top_tables); bad event → 400
  via TestClient; unsigned POST → 401. Use a TEMP metrics.db (fixture via monkeypatch METRICS_DB_PATH),
  never the live file. The 14 existing KB tests MUST stay green.
- Use `dashboard/tests/conftest.py` pattern: build a `client` TestClient with a signed cookie helper.

## Documentation you must write
- Append a "## Interaction metrics (backend)" section to `dashboard/README.md` describing:
  cookie scheme, env vars (`METRICS_SECRET`, `METRICS_DB_PATH`), the endpoints, and the schema.
  Note this is a NEW dedicated store, kb/kb.db remains read-only.
- Keep notes concise and factual.

## Verify before returning
- `cd dashboard && uv run --no-project pytest -q` → all green (14 existing + your new).
- Manual smoke (optional): `uv run --no-project uvicorn server:app --port 8000` then
  `curl -i localhost:8000/ -c cookies.txt` → confirm Set-Cookie METRICS_VISITOR; then
  `curl -b cookies.txt -X POST localhost:8000/api/metrics -H 'Content-Type: application/json' -d '{"event":"page_view"}'`
  → `{"ok":true,...}`; then `curl -b cookies.txt localhost:8000/api/metrics/summary` → reflects it.

## Report back to Lead (concise)
Files created/edited, test count, any deviations from contract + why, open concerns.
