# 01 — Security / Red-Team Review (Lens 1): KB Dashboard app

Lens: adversarial (break it). Scope (locked): `dashboard/server.py`, `dashboard/db.py`,
`dashboard/static/index.html`. Read-only; no edits. Verified by static read + live PoC
against a fixture SQLite (injected SQLi/garbage cursors) and end-to-end via
`fastapi.testclient.TestClient` against the real `server.app`.

## Verdict
**No exploitable vulnerability found in the 7 in-scope attack surfaces.** The SQL layer is
correctly whitelisted, the file server is constant-path, the frontend escapes every dynamic
sink, DoS caps are present, and every request-error path returns 4xx. The single prior-wave
MEDIUM (unhandled binascii 500) is a **false positive** — `binascii.Error` *is* a
`ValueError` subclass, so it was never unhandled; current code additionally has a broad
`except Exception`. The prior-wave LOW (unescaped card keys) is **fixed** — both cards now
`esc(k)`. Findings below are informational/robustness only.

---

## Re-assessment of prior wave (01-security-redteam.md, written earlier this session)

| Prior ID | Claim | Status | Evidence |
|---|---|---|---|
| MEDIUM — malformed `after` → 500 | `binascii.Error` "NOT a ValueError subclass" | **INVALID (false positive)** | PoC: `binascii.Error.__mro__` = `(binascii.Error, ValueError, Exception, ...)`. `GET /api/rows?table=vulnerabilities&after=garbage!!!` → **HTTP 400** (`{"detail":"Incorrect padding"}`). Even old code (only `except ValueError`) would have caught it; current code also has `except Exception` (server.py:96). |
| LOW — card keys unescaped (lines 277, 293) | `k` from summary keys not `esc()`'d | **FIXED** | Current index.html:277 `esc(k)` in sev card; :293 `esc(k)` (twice) in cat card. Both now escaped. |
| MEDIUM — no auth | full LAN read | **Out of this lens's scope** (deployment/arch; not one of the 7 in-scope surfaces; contract + local-first posture per 561.md). Noted as INFO below. |
| MEDIUM — k8s securityContext | hardening | **Out of 3-file scope** (dashboard.yaml). Not re-reviewed here. |
| MEDIUM — floating deps | requirements.txt | **Out of 3-file scope.** Not re-reviewed here. |
| LOW — `q` unbounded | | **FIXED** | db.py:194-195 caps `q` at 256 chars (verified with 10k-char input → no crash). |
| LOW — no rate limit / max-fetch | | **Still valid but low** | ENSURE_MAX_DEPTH=256 caps chained prefetch (index.html:397,403); bound is frontend-only, no server throttle. |
| LOW — zero injection tests | | **Still valid** | No negative tests assert hostile `sort`/`filters`/`after` are rejected (current PoC proves code is safe, but it isn't locked by a test). |
| OK — SQLi safe / LFI safe / k8s PV / container | | **Confirmed** | See OK list. |

---

## Findings (current code)

### [LOW] `api_tables` / `api_summary` have no error handling — can 500 on a DB anomaly
**file:** `server.py:50-61` (`api_tables`), `server.py:64-66` → `db.summary()` `db.py:120-142`.
**Surface:** #7 error handling.
**Why it's not request-triggerable:** neither endpoint takes params; the table list and counts
come from trusted `sqlite_master`. But the interpolation is unguarded:
- `api_tables` does `f"SELECT COUNT(*) FROM {name}"` for every name in `list_tables()`. If
  the KB ever contains a table whose name breaks bare-identifier parsing (e.g. a space/quote
  in the name — legal in SQLite when created quoted), this raises `sqlite3.OperationalError`
  with **no try/except → HTTP 500**.
- `summary()` unconditionally queries `vulnerabilities` and `security_tools`
  (`db.py:128`, `db.py:133`); if either table is absent, `OperationalError: no such table` →
  unhandled 500 in `api_summary`.
**Impact:** availability/robustness only — not injection, not attacker-triggerable via the API
today. Low because it depends on a corrupt/odd DB, not on request input.
**Fix:** wrap both in `try/except Exception → 503` (or `500` with generic detail), and/or
quote identifiers with double-quotes in the COUNT queries for safety.

### [INFO] No authentication / authorization on any endpoint (full read of KB)
**file:** `server.py:28-108` (all routes).
**Surface:** not one of the 7 in-scope items; flagged because it was a prior MEDIUM.
**Impact:** any client that reaches the pod can enumerate all tables (`/api/tables`) and
keyset-walk every row (`/api/rows?table=<x>&limit=500&after=<cursor>`), exfiltrating CVE
lists, `sources`/`security_tools` URLs, `code_reviews` findings, and `errors` (which can
contain internal file paths). Acceptable only under the stated ClusterIP/LAN + local-first
posture; becomes a real exposure the moment NodePort/LoadBalancer is enabled.
**Fix (out of lens scope / locked contract):** keep `ClusterIP` + NetworkPolicy; or front
with an authenticated reverse proxy; add a CI guard failing if `Service.type != ClusterIP`.

### [INFO] No server-side rate limiting (DoS amplification bounded only by frontend)
**file:** `static/index.html:397-417` (`ensureLoaded`), `db.py:192` (limit≤500).
**Surface:** #5 DoS.
**Impact:** `ENSURE_MAX_DEPTH=256` and `limit≤500` bound a single client, but there is no
per-client throttle. A LAN host can still spray keyset fetches. Low given read-only SQLite
and LAN posture.

---

## Verified SAFE (PoC / grep evidence) — the 7 in-scope surfaces

**(1) SQLi via table/sort/column names — WHITELISTED, not raw-injected.** ✅
- `table` validated by membership in `list_tables()` (`db.py:111-113` `_ensure_table`,
  called at `db.py:185` and via `server.py:80-82` → 404 on unknown). Interpolated only after
  this check (`db.py:274,278,303`).
- `sort` validated `if sort not in col_names → ValueError` (`db.py:188-189`). PoC:
  `sort="id; DROP TABLE vulnerabilities--"` → `ValueError: cannot sort by unknown column` → HTTP 400.
- `dir` validated `if dir not in ("asc","desc") → ValueError` (`db.py:190-191`); only
  `dir.upper()` (∈ {ASC,DESC}) reaches SQL (`db.py:279`). PoC: `dir="union"` → 400.
- **PoC SQLi sweep (all rejected → 400/404, table survived):** `sort∈{id;DROP--, id) OR 1=1--, 1=1}`,
  `dir∈{asc;DROP--, union, DESC}`, unknown table → 404.

**(2) Column name in f-string SQL without PRAGMA whitelist — NONE.** ✅
- Cursor predicate interpolates `{sort}` (`db.py:256,263`) but `sort` is PRAGMA-validated
  (`col_names` from `list_columns` → `PRAGMA table_info`, `db.py:79-90,186-187`).
- Equality filter `{k}` (`db.py:240`) and LIKE `{c}` (`db.py:211`) both sourced from
  `col_names`/`text_cols` (PRAGMA). `filters` keys pre-filtered server-side:
  `if k in _RESERVED or k not in col_names: continue` (`server.py:85-87`).
- **PoC:** filter `id="1 OR 1=1"` → bound as a value, 0 rows (no injection, `db.py:240` uses `?`).

**(3) Path traversal / LFI in `FileResponse(STATIC)` — SAFE.** ✅
- `STATIC = Path(__file__).resolve().parent / "static" / "index.html"` is a **constant**
  (`server.py:21`); served verbatim (`server.py:41-42`). No request input reaches any file
  path. `KB_DB_PATH` is env-only (`db.py:43-48`), never request-derived. DB opened `?mode=ro`.

**(4) XSS in frontend — FULLY CLOSED (prior LOW fixed).** ✅
- Every dynamic sink is escaped. 12 `innerHTML` usages audited:
  - Static/clears: `index.html:249,251,304,316,519,588`.
  - `esc()`-wrapped: sev-card key `:277`, cat-card key `:293` (**fixed**), `col.type` `:323`,
    drawer `row` JSON `:524`, `s.url` `:528`, `s.title` `:529`, `advisory_keys` JSON `:532`,
    error message `:540`. Severity/category also flow only through `esc(k)`.
  - `textContent` used for `t.name` `:260`, `col.name` `:324`, all grid cells `:439`.
- `esc()` defined `index.html:330` escapes `&<>`; dynamic values (severity tokens, table
  names, card labels, source titles/URLs — all server-derived) are wrapped. URLs are rendered
  as **text inside `<span>`**, never as `href`/`src`, so even a `javascript:` value is inert.
- No `createElement('a')`, no `href=` with dynamic value, no `window.location`/`window.open`
  anywhere in the file (grep). 

**(5) DoS caps — PRESENT.** ✅
- `limit = max(1, min(int(limit), 500))` (`db.py:192`); FastAPI also 422s non-int `limit`
  (PoC `limit=abc` → 422). `q` capped `q[:256]` (`db.py:194-195`, verified 10k input OK).
- Frontend `ENSURE_MAX_DEPTH = 256` (`index.html:397,403`) caps chained prefetch;
  `MAX_SPACER = 30000000` (`index.html:162,358`) caps spacer height.

**(6) Open redirect / SSRF — NONE.** ✅
- `api()` uses only relative paths (`index.html:206-211`); no `redirect`, no `Location`
  header, no outbound HTTP from the server (only local SQLite reads). No user-controlled URL
  is ever turned into a navigation target.

**(7) Error handling — api_rows / api_row return 4xx; two read-only helpers could 500 on DB anomaly.** ✅/⚠️
- `api_rows` (`server.py:69-98`): `ValueError` → 404 (unknown table) or 400 (bad sort/dir);
  broad `except Exception` → 400 (covers `binascii.Error`, `json.JSONDecodeError`).
- `api_row` (`server.py:101-108`): `ValueError` → 404 (unknown table);
  `LookupError` → 404 (no such row). `row_detail` guards `None` `source_id` (`db.py:332-336`).
- **Gap (LOW):** `api_tables` and `api_summary` have **no** try/except (see finding above) —
  the only in-scope path that can emit an unhandled 500, and only on a malformed/absent table
  in the DB.

---

## Compact JSON verdict
```json
{
  "critical": [],
  "high": [],
  "medium": [],
  "low": [
    "api_tables (server.py:50-61) and api_summary (server.py:64-66 -> db.py:120-142) lack error handling; an odd/absent table name in the DB can raise an unhandled sqlite3.OperationalError -> HTTP 500 (robustness/availability; not request-triggerable, not injection)"
  ],
  "ok": [
    "SQLi: table/sort/dir/column names are whitelisted via list_tables()/PRAGMA table_info; all values parameterized; PoC sort='id;DROP--' and dir='union' -> HTTP 400, table survived",
    "LFI: FileResponse serves a constant STATIC path (server.py:21,41-42); no request input reaches any filesystem path",
    "XSS: all 12 innerHTML sinks escaped via esc()/textContent; prior unescaped card keys (index.html:277,293) now fixed; no dynamic href/src/location",
    "DoS: limit capped 500 (db.py:192), q capped 256 (db.py:194-195), ENSURE_MAX_DEPTH 256 + MAX_SPACER (index.html:397,403,162,358)",
    "SSRF/open-redirect: none; relative-only fetch, no server outbound, no Location/redirect",
    "error-handling: api_rows/api_row return 4xx for all hostile input; malformed cursor -> 400 (binascii.Error is a ValueError subclass; prior-wave MEDIUM was a false positive)",
    "no-auth (prior MEDIUM) reclassified as INFO/out-of-scope: safe only under ClusterIP+LAN+local-first; exposure if NodePort/LoadBalancer enabled"
  ],
  "verdict": "No exploitable vulnerability in the 7 in-scope attack surfaces. Prior-wave MEDIUM (unhandled binascii 500) is a false positive; prior-wave LOW (unescaped card keys) is fixed. Only low-severity robustness gap remains: api_tables/api_summary can 500 on a malformed DB (not request-triggerable). App is safe to ship under the stated ClusterIP/LAN/local-first posture."
}
```
