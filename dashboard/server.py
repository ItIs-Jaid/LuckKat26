"""Local-first KB dashboard — FastAPI backend over kb/kb.db.

Endpoints (locked contract; the frontend depends on these exactly):
  GET /            -> dashboard/static/index.html (or inline fallback)
  GET /health      -> {"status":"ok"}
  GET /api/tables  -> [{name, rows, columns:[{name,type,nullable}], searchable}]
  GET /api/summary -> {tables, vuln_severity, tool_category}
  GET /api/rows?table=&sort=&dir=&limit=&after=&q=&<col>=<val>
                     -> {items, next_cursor, total}
  GET /api/row/{table}/{id} -> {row, sources, advisory_keys, provenance_tags}
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel

import db
import metrics

STATIC = Path(__file__).resolve().parent / "static" / "index.html"

app = FastAPI(title="DevSecLoc KB dashboard")

# Initialise the dedicated metrics store (idempotent). Path comes from the
# METRICS_DB_PATH env var (set by tests before importing this module) or the
# default dashboard/metrics.db. kb/kb.db stays read-only; metrics.db is the only
# writable store.
metrics.init_metrics()

_RESERVED = {"table", "sort", "dir", "limit", "after", "q"}

# Signed-cookie attributes (security-critical, verbatim from the locked design).
_COOKIE_NAME = "METRICS_VISITOR"
_COOKIE_MAX_AGE = 31536000  # 1 year

router = APIRouter()


class MetricsEvent(BaseModel):
    """JSON body for POST /api/metrics."""

    event: str
    table: str | None = None
    meta: str | None = None


@router.post("/api/metrics")
def api_metrics(event: MetricsEvent, request: Request) -> dict:
    cookie = request.cookies.get(_COOKIE_NAME)
    vid = metrics.validate_cookie(cookie) if cookie else None
    if vid is None:
        raise HTTPException(status_code=401, detail="invalid or missing visitor cookie")
    try:
        eid = metrics.log_event(vid, event.event, event.table, event.meta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "id": eid}


@router.get("/api/metrics/summary")
def api_metrics_summary() -> dict:
    return metrics.summary()


app.include_router(router)


@app.get("/health")
def health() -> dict:
    # DB-aware: fail readiness if the KB store can't be opened (NAS down / bad perms).
    try:
        with db.connect() as c:
            c.execute("SELECT 1").fetchone()
    except Exception:
        raise HTTPException(status_code=503, detail="kb store unavailable")
    return {"status": "ok"}


@app.get("/", response_model=None)
def index(request: Request) -> Response:
    # Issue a signed visitor cookie if the request has none (or the one it has
    # is invalid). We never trust the raw value; validate_cookie re-checks the
    # HMAC. Registering the visitor also lets summary() count the visit.
    existing = request.cookies.get(_COOKIE_NAME)
    new_cookie: str | None = None
    if not existing or metrics.validate_cookie(existing) is None:
        _, new_cookie = metrics.issue_visitor()

    if STATIC.exists():
        resp: Response = FileResponse(STATIC, media_type="text/html")
    else:
        resp = HTMLResponse(
            "<!doctype html><meta charset=utf-8><title>KB dashboard</title>"
            "<h1>KB dashboard</h1><p>Backend up; frontend not built yet. "
            "See <a href='/api/summary'>/api/summary</a>.</p>"
        )

    if new_cookie:
        resp.set_cookie(
            _COOKIE_NAME,
            new_cookie,
            httponly=True,
            samesite="lax",
            max_age=_COOKIE_MAX_AGE,
            path="/",
        )
    return resp


@app.get("/api/tables")
def api_tables() -> list[dict]:
    out = []
    for name in db.list_tables():
        cols = db.list_columns(name)
        text_cols = {c["name"] for c in cols if c["type"] == "TEXT"}
        with db.connect() as c:
            rows = c.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        out.append(
            {"name": name, "rows": rows, "columns": cols, "searchable": bool(text_cols)}
        )
    return out


@app.get("/api/summary")
def api_summary() -> dict:
    return db.summary()


@app.get("/api/rows")
def api_rows(
    request: Request,
    table: str,
    sort: str = "id",
    dir: str = "desc",
    limit: int = 50,
    after: str | None = None,
    q: str | None = None,
):
    try:
        col_names = {c["name"] for c in db.list_columns(table)}
    except ValueError:
        raise HTTPException(status_code=404, detail=f"unknown table: {table}")

    filters = {}
    for k, v in request.query_params.items():
        if k in _RESERVED or k not in col_names:
            continue
        filters[k] = v

    try:
        return db.query_rows(
            table, sort=sort, dir=dir, limit=limit, after=after, q=q, filters=filters
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Malformed cursor (base64/binascii), bad JSON, etc. -> 400, never 500.
        raise HTTPException(status_code=400, detail=f"bad request: {e}")


@app.get("/api/row/{table}/{row_id}")
def api_row(table: str, row_id: int) -> dict:
    try:
        return db.row_detail(table, row_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"unknown table: {table}")
    except LookupError:
        raise HTTPException(status_code=404, detail=f"no row {row_id} in {table}")
