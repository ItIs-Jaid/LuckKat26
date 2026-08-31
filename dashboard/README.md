# KB Bulk-Info Dashboard (local-first)

A local-first FastAPI dashboard that browses the bulk contents of the DevSecLoc
knowledge base (`kb/kb.db`) and stays responsive as the DB grows very large
(server-side keyset pagination + a windowed/virtualized frontend table).

**Out of scope:** the `api/` + `pipeline/` + `data/` ("localhostops") project that
shares this repo tree is a *different* app. This dashboard reads only `kb/kb.db`.

## Run

```bash
# bash / MSYS (Git Bash)
cd dashboard
./run.sh
```

```powershell
# PowerShell
cd dashboard
.\run.ps1
```

Both scripts create a `.venv` via `uv`, install `requirements.txt`, default
`KB_DB_PATH` to `<repo>/kb/kb.db` (repo root = the directory containing `dashboard/`),
and serve on `http://127.0.0.1:8000` (`--reload`). No cloud, no outbound calls.

## Point at a different DB

```bash
export KB_DB_PATH="C:/path/to/other/kb.db"   # bash
$env:KB_DB_PATH = "C:/path/to/other/kb.db"   # PowerShell
```

## Endpoints (read-only)

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Serves the self-contained dashboard UI |
| GET | `/health` | `{"status":"ok"}` |
| GET | `/api/tables` | Table list with row counts + columns |
| GET | `/api/summary` | Aggregate cards (per-table totals, vuln severity, tool categories) |
| GET | `/api/rows?table=&sort=&dir=&limit=&after=&q=` | Windowed rows (keyset pagination) |
| GET | `/api/row/{table}/{id}` | Single row + resolved sources (or advisory keys) |

## Interaction Metrics

The dashboard also collects **anonymous, localhost-only interaction metrics** in a
dedicated SQLite database (`metrics.db`), fully separate from the read-only knowledge
base (`kb/kb.db`). It answers "how is the dashboard being used locally?" with no PII
and without ever writing to the KB store.

### What it is
- A signed-cookie visitor tracker: `GET /` issues an `HttpOnly` `METRICS_VISITOR` cookie (HMAC-signed) if absent.
- The frontend logs interaction events (`page_view`, `table_select`, `search`, `sort`, `row_open`, `filter`) via `POST /api/metrics`.
- `GET /api/metrics/summary` aggregates totals, unique visitors, per-event counts, and top tables.
- All data lives in `dashboard/metrics.db` (gitignored). The KB store stays read-only.

### Security model
- **Signed cookie** — `METRICS_VISITOR = "<vid>.<sig>"`, where `vid` is a random 32-hex token and `sig = HMAC-SHA256(METRICS_SECRET, vid)`. The server validates with a constant-time compare; a tampered/missing cookie → `401` on `POST`.
- **No PII** — only an opaque visitor id and event counters are stored. No IP, no user agent, no content.
- **Read-only KB** — `kb/kb.db` is opened read-only; `metrics.db` is the only writable store.
- **Localhost only** — the server binds `127.0.0.1`; it is never exposed on `0.0.0.0`.
- **Secret handling** — `METRICS_SECRET` comes from the environment. If unset, the metrics layer uses an ephemeral dev secret and logs a warning (the secret is never logged).

### Environment variables
| Var | Default | Purpose |
|---|---|---|
| `KB_DB_PATH` | `dashboard/../kb/kb.db` | Read-only knowledge-base DB (unchanged). |
| `METRICS_SECRET` | *(unset → dev fallback + warning)* | HMAC key for the visitor cookie. Set in production. |
| `METRICS_DB_PATH` | `dashboard/metrics.db` | Writable metrics store (gitignored). |

### How to run
```bash
cd dashboard
./run.sh          # serves http://127.0.0.1:8000 (--reload)
```
`run.sh` passes `METRICS_SECRET` through from the environment and defaults `METRICS_DB_PATH`/`KB_DB_PATH`. Then open http://127.0.0.1:8000.

### Metrics endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Issues the `METRICS_VISITOR` cookie if absent; serves the UI. |
| POST | `/api/metrics` | Body `{"event":..., "table"?:..., "meta"?:<200 chars>}`. Requires a valid cookie → `401`; unknown event → `400`. Returns `{"ok": true, "id": <int>}`. |
| GET | `/api/metrics/summary` | `{"visits":int, "unique_visitors":int, "events":int, "by_event":{event:count}, "active_sessions":int, "top_tables":[{"table":str,"n":int}]}`. `active_sessions` = visitors with an event in the last 30 minutes. |

### Schema (`metrics.db`)
```sql
CREATE TABLE visitors (
    id         TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
CREATE TABLE events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    visitor_id  TEXT NOT NULL,
    event       TEXT NOT NULL,
    table_name  TEXT,
    meta        TEXT,
    ts          TEXT NOT NULL
);
CREATE INDEX idx_events_visitor ON events(visitor_id);
CREATE INDEX idx_events_event   ON events(event);
CREATE INDEX idx_events_ts      ON events(ts);
```

### Interaction metrics (GUI)

The frontend renders an **INTERACTION METRICS** panel in the dashboard (directly
below the summary cards). It is fed by `GET /api/metrics/summary` and shows:

- **four stat cards** — visits, unique visitors, events, active sessions;
- **by event** — a bar breakdown of event counts (`page_view`, `table_select`,
  `search`, `sort`, `row_open`, `filter`);
- **top tables** — a bar breakdown of the most-interacted tables.

The panel reuses the dashboard's existing cyberpunk classes (`.card`, `.special`,
`.special-title`, `.bar-row`, `.bar-track`, `.bar-fill`) so it matches the rest of
the UI.

**Client-side tracking is best-effort and never blocks the UI:**

- A `track(event, table, meta)` function POSTs `{"event","table","meta"}` to
  `/api/metrics` **only when a `METRICS_VISITOR` cookie is present** (the server
  issues it on `GET /`). With no cookie, no request is made.
- Every fetch error is swallowed; analytics can never break the dashboard.
- The tracker is wired into: `selectTable` → `table_select`, the search input
  (debounced) → `search`, `toggleSort` → `sort`, `openDetail` → `row_open`, and
  reset/filter → `filter`. `track('page_view')` fires once on load.
- No PII is collected — only an opaque visitor id and event counters.
- **All dynamic text is HTML-escaped via the existing `esc()`** (DOM is built with
  `textContent`, never raw `innerHTML`), so metric values cannot inject markup.

## Local-first / no-CDN

The frontend `static/index.html` is fully self-contained: all CSS/JS is inline and
it makes **zero** `http(s)://` requests. The backend serves only from the local DB.

## Tests

```bash
cd dashboard
uv run pytest -q
```

Tests use a synthetic fixture DB (no copy of the real `kb.db`), so they run offline
and stay fast.
