"""Localhost-interaction-metrics DB layer (OWN dedicated, writable metrics.db).

This module is SEPARATE from db.py (which owns the read-only kb/kb.db). It owns a
dedicated SQLite store, ``metrics.db``, that records opaque localhost-visitor ids
and anonymous interaction events. No PII is stored: only an opaque visitor id, an
event name, an optional table name, and a short (<=200 char) meta string.

Security model (verbatim from the locked design):
  * The visitor cookie ``METRICS_VISITOR`` is ``f"{vid}.{sig}"`` where
    ``vid = secrets.token_hex(16)`` and ``sig`` is an HMAC-SHA256 of ``vid``
    under ``METRICS_SECRET``. Validation uses ``hmac.compare_digest`` (constant
    time). The raw cookie value is never trusted.
  * All SQL is parameterized; only fixed column/table names are ever interpolated,
    and those are whitelisted. No string-concatenation of caller values.

Path: env ``METRICS_DB_PATH`` or default ``dashboard/metrics.db`` (gitignored).
Secret: env ``METRICS_SECRET``; if unset, a dev fallback secret is used and a
warning is logged (the secret is NEVER logged).
"""
from __future__ import annotations

import hmac
import logging
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Allowed interaction events (contract-locked).
ALLOWED_EVENTS = frozenset(
    {"page_view", "table_select", "search", "sort", "row_open", "filter"}
)

# Max length of the optional `meta` field (contract: str<=200).
META_MAX = 200

# Insecure fallback used only when METRICS_SECRET is unset. NEVER logged.
_DEV_FALLBACK_SECRET = "dev-insecure-fallback-secret-change-me"
_secret_warned = False

# Module-singleton resolved metrics DB path (set by init_metrics / get_metrics_path).
_metrics_path: Path | None = None

SCHEMA = """
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
"""


def get_secret() -> str:
    """Return the HMAC secret, falling back to a dev secret with a one-time warning.

    The secret itself is never logged.
    """
    global _secret_warned
    env = os.environ.get("METRICS_SECRET")
    if env:
        return env
    if not _secret_warned:
        logger.warning(
            "METRICS_SECRET not set; using an INSECURE dev fallback secret. "
            "Set METRICS_SECRET before serving real traffic."
        )
        _secret_warned = True
    return _DEV_FALLBACK_SECRET


def _resolve_path() -> Path:
    """Resolve the metrics DB path from METRICS_DB_PATH env or the default."""
    env = os.environ.get("METRICS_DB_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve().parent
    return here / "metrics.db"


def get_metrics_path() -> Path:
    """Return the resolved metrics DB path, resolving it on first use."""
    global _metrics_path
    if _metrics_path is None:
        _metrics_path = _resolve_path()
    return _metrics_path


def init_metrics(path: str | os.PathLike | None = None) -> Path:
    """Create the metrics DB (idempotent) and return its path.

    Pass ``path`` to force a specific file (used by tests). If ``None``, the env
    var METRICS_DB_PATH or the default location is used. The parent directory is
    created if needed so the file is safe to open.
    """
    global _metrics_path
    if path is not None:
        _metrics_path = Path(path)
    else:
        _metrics_path = _resolve_path()
    _metrics_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()
    return _metrics_path


def _connect() -> sqlite3.Connection:
    """Open a connection to the (resolved) metrics DB."""
    conn = sqlite3.connect(get_metrics_path())
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    """Current UTC timestamp as a fixed-width ISO8601 string (lexically sortable)."""
    return datetime.now().isoformat(timespec="seconds")


def _sign(vid: str) -> str:
    return hmac.new(get_secret().encode(), vid.encode(), "sha256").hexdigest()


def issue_visitor() -> tuple[str, str]:
    """Issue a new signed visitor: returns ``(vid, cookie_value)``.

    Also registers the visitor row so ``summary()`` counts it. The cookie value is
    ``f"{vid}.{sig}"``.
    """
    vid = secrets.token_hex(16)
    value = f"{vid}.{_sign(vid)}"
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO visitors(id, created_at) VALUES (?, ?)",
            (vid, _now()),
        )
    return vid, value


def validate_cookie(value) -> str | None:
    """Validate a METRICS_VISITOR cookie value; return the vid or None if invalid.

    Uses ``hmac.compare_digest`` for constant-time signature comparison. Never
    raises on malformed input.
    """
    if not value or not isinstance(value, str) or "." not in value:
        return None
    vid, _, sig = value.rpartition(".")
    if not vid or not sig:
        return None
    if hmac.compare_digest(_sign(vid), sig):
        return vid
    return None


def log_event(
    vid: str,
    event: str,
    table: str | None = None,
    meta: str | None = None,
) -> int:
    """Record an interaction event for ``vid``; return the new event row id.

    Raises ``ValueError`` for an unknown event or an over-length ``meta`` (the API
    layer maps these to HTTP 400). The visitor row is ensured so it counts toward
    ``summary()`` even if the cookie was minted directly in a test.
    """
    if event not in ALLOWED_EVENTS:
        raise ValueError(f"unknown event: {event!r}")
    if meta is not None and len(meta) > META_MAX:
        raise ValueError(f"meta exceeds {META_MAX} chars")
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO visitors(id, created_at) VALUES (?, ?)",
            (vid, _now()),
        )
        cur = conn.execute(
            "INSERT INTO events(visitor_id, event, table_name, meta, ts) "
            "VALUES (?, ?, ?, ?, ?)",
            (vid, event, table, meta, _now()),
        )
        return int(cur.lastrowid)


def summary() -> dict:
    """Aggregate metrics: visits, unique_visitors, events, by_event, active_sessions, top_tables."""
    cutoff = (datetime.now() - timedelta(minutes=30)).isoformat(timespec="seconds")
    with _connect() as conn:
        visits = conn.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]
        events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        by_event = {
            row["event"]: row["c"]
            for row in conn.execute(
                "SELECT event, COUNT(*) AS c FROM events GROUP BY event"
            )
        }
        active_sessions = conn.execute(
            "SELECT COUNT(DISTINCT visitor_id) FROM events WHERE ts >= ?",
            (cutoff,),
        ).fetchone()[0]
        top_tables = [
            {"table": row["table_name"], "n": row["c"]}
            for row in conn.execute(
                "SELECT table_name, COUNT(*) AS c FROM events "
                "WHERE table_name IS NOT NULL "
                "GROUP BY table_name ORDER BY c DESC, table_name ASC"
            )
        ]
    return {
        "visits": visits,
        "unique_visitors": visits,
        "events": events,
        "by_event": by_event,
        "active_sessions": active_sessions,
        "top_tables": top_tables,
    }
