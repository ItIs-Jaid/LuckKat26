"""Local-first DB layer for the KB bulk-info dashboard.

Reads kb/kb.db (or KB_DB_PATH). stdlib sqlite3 only. No cloud, no writes.
All queries are parameterized (no string concatenation of values) to stay
injection-safe; only column/window names are whitelisted from PRAGMA lookups.

Verified schema gotchas handled here:
  * source_ids is NOT uniform:
      - joinable on languages/libraries/patterns/tutorials/methodologies
        (split ';' -> sources.id integers)
      - vulnerabilities -> ';'-joined EXTERNAL advisory keys (nvd:CVE-.. / osv:GHSA-..)
      - code_reviews    -> a provenance tag (e.g. 'independent-reviewer-subagent')
  * security_tools has no source_ids col; it has source_id (FK -> sources.id)
  * vulnerabilities.severity is polluted: label rows (HIGH/LOW/CRITICAL/
    MODERATE/unknown, mixed case) + raw CVSS vector strings (CVSS:3.1/..).
    normalize_severity() maps to LOW|MEDIUM|HIGH|CRITICAL|UNKNOWN|VECTOR.
  * JSON-ish != JSON: methodologies.steps = newline TEXT; review_queue.payload
    = unvalidated TEXT (try json, fallback plain).
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import sqlite3

# Tables whose `source_ids` is genuinely ';'-joined sources.id integers.
JOINABLE_SOURCE_IDS = {
    "languages",
    "libraries",
    "patterns",
    "tutorials",
    "methodologies",
}

_TEXT_TYPES = {"TEXT"}


def get_db_path() -> Path:
    """Absolute DB path from KB_DB_PATH env, else repo-relative default."""
    env = os.environ.get("KB_DB_PATH")
    if env:
        return Path(env)
    # dashboard/server.py -> dashboard/ -> repo root -> kb/kb.db
    here = Path(__file__).resolve().parent
    return here.parent / "kb" / "kb.db"


def connect() -> sqlite3.Connection:
    """Open the KB SQLite file in read-only mode.

    Read-only URI mode (?mode=ro) is the correct way to consume a SQLite
    file over a network share (NFS/SMB): the driver never creates a -wal/-shm
    sidecar, so there is no write/lock hazard on the NAS mount.
    """
    path = get_db_path()
    if not path.exists():
        raise FileNotFoundError(
            f"KB store not found at {path}. Mount the NAS share / set KB_DB_PATH, "
            "or run kb/init.py to create it."
        )
    uri = path.as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def list_tables() -> list[str]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [r[0] for r in rows]


def list_columns(table: str) -> list[dict]:
    _ensure_table(table)
    with connect() as conn:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [
        {
            "name": r["name"],
            "type": r["type"],
            "nullable": not r["notnull"],
        }
        for r in rows
    ]


def normalize_severity(raw) -> str:
    """Map the polluted severity column to a normalized token."""
    if raw is None:
        return "UNKNOWN"
    s = str(raw).strip()
    if s.upper().startswith("CVSS:"):
        return "VECTOR"
    up = s.upper()
    if up == "MODERATE":
        return "MEDIUM"
    if up in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return up
    if up == "UNKNOWN":
        return "UNKNOWN"
    # Anything else (unrecognized label) collapses to UNKNOWN.
    return "UNKNOWN"


def _ensure_table(table: str) -> None:
    if table not in list_tables():
        raise ValueError(f"unknown table: {table}")


def _text_columns(table: str) -> list[str]:
    return [c["name"] for c in list_columns(table) if c["type"] in _TEXT_TYPES]


def summary() -> dict:
    with connect() as conn:
        tables = []
        for name in list_tables():
            total = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            tables.append({"name": name, "total": total})

        vuln_sev: dict[str, int] = {}
        for (sev,) in conn.execute("SELECT severity FROM vulnerabilities"):
            key = normalize_severity(sev)
            vuln_sev[key] = vuln_sev.get(key, 0) + 1

        tool_cat: dict[str, int] = {}
        for cat, n in conn.execute(
            "SELECT category, COUNT(*) FROM security_tools GROUP BY category"
        ):
            tool_cat[cat] = n

    return {
        "tables": tables,
        "vuln_severity": vuln_sev,
        "tool_category": tool_cat,
    }


def _encode_cursor(sort_val, row_id) -> str:
    payload = json.dumps([sort_val, row_id], ensure_ascii=False)
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str):
    raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    sort_val, row_id = json.loads(raw)
    return sort_val, row_id


def _severity_rank(raw) -> int:
    """Numeric rank matching SEVERITY_RANK_CASE, so keyset cursors stay consistent
    when sorting vulnerabilities by severity. CRITICAL=4 .. UNKNOWN=0, VECTOR=1."""
    s = normalize_severity(raw)
    return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "VECTOR": 1, "LOW": 1, "UNKNOWN": 0}[s]


# SQL expression that maps the polluted `severity` column to a sortable rank.
# Used only when sorting vulnerabilities by severity (raw text sort is lexical nonsense).
SEVERITY_RANK_CASE = (
    "CASE "
    "WHEN UPPER(severity) LIKE 'CVSS:%' THEN 1 "
    "WHEN UPPER(severity) = 'CRITICAL' THEN 4 "
    "WHEN UPPER(severity) = 'HIGH' THEN 3 "
    "WHEN UPPER(severity) IN ('MEDIUM','MODERATE') THEN 2 "
    "WHEN UPPER(severity) = 'LOW' THEN 1 "
    "ELSE 0 END"
)


def query_rows(
    table: str,
    sort: str = "id",
    dir: str = "desc",
    limit: int = 50,
    after: str | None = None,
    q: str | None = None,
    filters: dict | None = None,
) -> dict:
    _ensure_table(table)
    cols = list_columns(table)
    col_names = {c["name"] for c in cols}
    if sort not in col_names:
        raise ValueError(f"cannot sort by unknown column: {sort}")
    if dir not in ("asc", "desc"):
        raise ValueError(f"dir must be asc or desc, got: {dir}")
    limit = max(1, min(int(limit), 500))
    # Cap search term length to prevent LIKE-parameter amplification (DoS edge).
    if q:
        q = q[:256]

    # When sorting vulnerabilities by severity, sort by the normalized rank, not
    # the raw (lexically meaningless) text column.
    sort_expr = (
        SEVERITY_RANK_CASE
        if (table == "vulnerabilities" and sort == "severity")
        else sort
    )

    text_cols = _text_columns(table)
    search_where: list[str] = []
    search_params: list = []

    # substring search across text columns
    if q:
        like = [f"{c} LIKE ?" for c in text_cols]
        if like:
            search_where.append("(" + " OR ".join(like) + ")")
            search_params += [f"%{q}%"] * len(like)

    # equality filters on known columns
    if filters:
        for k, v in filters.items():
            if k not in col_names:
                continue
            if table == "vulnerabilities" and k == "severity":
                # Compare against the NORMALIZED severity (MODERATE->MEDIUM,
                # CVSS:...->VECTOR) so ?severity=MEDIUM also matches raw 'MODERATE'
                # and ?severity=VECTOR matches raw 'CVSS:...' vectors. The CASE
                # below emits exactly these tokens, so the bound param must too.
                sv = str(v).strip().upper()
                if sv.startswith("CVSS:"):
                    sev_param = "VECTOR"
                elif sv == "MODERATE":
                    sev_param = "MEDIUM"
                else:
                    sev_param = sv
                search_where.append(
                    "(CASE WHEN UPPER(severity) LIKE 'CVSS:%' THEN 'VECTOR' "
                    "WHEN UPPER(severity)='MODERATE' THEN 'MEDIUM' "
                    "ELSE UPPER(severity) END) = ?"
                )
                search_params.append(sev_param)
            else:
                search_where.append(f"{k} = ?")
                search_params.append(v)

    # Cursor (keyset) predicate — composite (sort_expr, id), NULL-safe.
    # Column name (sort) is whitelisted from PRAGMA lookups, so interpolated
    # directly; only values are bound. NULLs sort first for ASC, last for DESC
    # (SQLite default), and the comparator mirrors that exactly.
    cursor_pred = ""
    cursor_params: list = []
    if after is not None:
        sort_val, row_id = _decode_cursor(after)
        # Compare against sort_expr (NOT the raw column): when sorting
        # vulnerabilities by severity, sort_expr is the numeric SEVERITY_RANK_CASE
        # while the bound param is the numeric rank. Comparing the raw TEXT
        # `severity` column against an INTEGER rank is always false/true in
        # SQLite (storage-class order INTEGER < TEXT) -> broken keyset paging.
        # For non-severity sorts sort_expr == sort, so this is a no-op.
        if dir == "desc":
            cursor_pred = (
                f" AND ( (? IS NULL AND ? IS NOT NULL) "  # R NULL, C not NULL -> R later
                f" OR (? IS NULL AND ? IS NULL AND id < ?) "  # both NULL -> id desc
                f" OR (? IS NOT NULL AND ? IS NOT NULL "
                f"     AND ({sort_expr} < ? OR ({sort_expr} = ? AND id < ?))) )"
            )
        else:
            cursor_pred = (
                f" AND ( (? IS NOT NULL AND ? IS NULL) "  # R not NULL, C NULL -> R later
                f" OR (? IS NULL AND ? IS NULL AND id > ?) "  # both NULL -> id asc
                f" OR (? IS NOT NULL AND ? IS NOT NULL "
                f"     AND ({sort_expr} > ? OR ({sort_expr} = ? AND id > ?))) )"
            )
        # 10 placeholders: pattern is (csv,csv, csv,csv,rid, csv,csv, csv,csv,rid)
        cursor_params = [sort_val] * 4 + [row_id] + [sort_val] * 4 + [row_id]

    search_sql = (" WHERE " + " AND ".join(search_where)) if search_where else ""
    # If there's no search/filter clause, the cursor predicate needs its own WHERE.
    cursor_sql = cursor_pred.replace(" AND (", " WHERE (", 1) if (cursor_pred and not search_where) else cursor_pred
    with connect() as conn:
        # total = rows matching search+filters ONLY (cursor position must not shrink it)
        total = conn.execute(
            f"SELECT COUNT(*) FROM {table}{search_sql}", search_params
        ).fetchone()[0]

        sql = (
            f"SELECT * FROM {table}{search_sql}{cursor_sql} "
            f"ORDER BY {sort_expr} {dir.upper()}, id {dir.upper()} "
            f"LIMIT ?"
        )
        rows = conn.execute(sql, search_params + cursor_params + [limit]).fetchall()

    items = [dict(r) for r in rows]
    next_cursor = None
    if len(items) == limit and items:
        last = items[-1]
        # Encode the *sort expression* value, not a raw text cell, for consistency.
        if sort_expr == SEVERITY_RANK_CASE:
            sort_val = _severity_rank(last.get("severity"))
        elif sort_expr == sort:
            sort_val = last.get(sort)
        else:
            sort_val = last.get(sort)
        next_cursor = _encode_cursor(sort_val, last["id"])

    return {"items": items, "next_cursor": next_cursor, "total": total}


def row_detail(table: str, row_id: int) -> dict:
    _ensure_table(table)
    with connect() as conn:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE id = ?", (row_id,)
        ).fetchone()
        if row is None:
            raise LookupError(f"no row {row_id} in {table}")
        row = dict(row)

        sources: list[dict] = []
        advisory_keys: list[str] = []
        provenance_tags: list[str] = []

        if table in JOINABLE_SOURCE_IDS and row.get("source_ids"):
            # isascii() guards against unicode "digits" (e.g. '\u00b2'.isdigit()==True)
            # which int() would reject and 500 the request.
            ids = [
                int(x) for x in str(row["source_ids"]).split(";")
                if x.strip().isascii() and x.strip().isdigit()
            ]
            if ids:
                ph = ",".join("?" * len(ids))
                for r in conn.execute(
                    f"SELECT title, url FROM sources WHERE id IN ({ph})", ids
                ):
                    sources.append({"title": r["title"], "url": r["url"]})
        elif table == "vulnerabilities" and row.get("source_ids"):
            advisory_keys = [x for x in str(row["source_ids"]).split(";") if x.strip()]
        elif table == "code_reviews" and row.get("source_ids"):
            provenance_tags = [x for x in str(row["source_ids"]).split(";") if x.strip()]
        elif table == "security_tools" and row.get("source_id"):
            r = conn.execute(
                "SELECT title, url FROM sources WHERE id = ?", (row["source_id"],)
            ).fetchone()
            if r:
                sources.append({"title": r["title"], "url": r["url"]})

    return {
        "row": row,
        "sources": sources,
        "advisory_keys": advisory_keys,
        "provenance_tags": provenance_tags,
    }


def make_fixture_db(path) -> Path:
    """Build a tiny synthetic KB mirroring kb/schema.sql (no real data).

    Used by tests so they never touch the live kb/kb.db. `path` is the
    sqlite file to create.
    """
    import sqlite3 as _sqlite

    repo_root = Path(__file__).resolve().parent.parent
    schema_sql = (repo_root / "kb" / "schema.sql").read_text(encoding="utf-8")
    path = Path(path)
    conn = _sqlite.connect(path)
    conn.executescript(schema_sql)
    cur = conn.cursor()

    cur.executemany(
        "INSERT INTO sources(kind,title,url,tier,last_ok) VALUES (?,?,?,?,?)",
        [
            ("blog", "B1", "https://ex/b1", 3, 1),
            ("docs", "D1", "https://ex/d1", 3, 1),
            ("github", "G1", "https://ex/g1", 3, 1),
            ("reddit", "R1", "https://ex/r1", 2, 1),
            ("advisory", "A1", "https://ex/a1", 3, 1),
            ("blog", "B2", "https://ex/b2", 1, 0),
        ],
    )
    cur.executemany(
        "INSERT INTO languages(name,version,role,source_ids,confidence) VALUES (?,?,?,?,?)",
        [
            ("Python", "3.11", "scripting", "1;2", 5),
            ("C", "C17", "systems", "3", 4),
            ("Rust", "1.0", "systems", None, 3),
        ],
    )
    cur.executemany(
        "INSERT INTO libraries(language_id,name,category,ecosystem,version,source_ids,confidence) VALUES (?,?,?,?,?,?,?)",
        [
            (1, "fastapi", "web-framework", "pip", "0.115", "1;2;3", 5),
            (1, "requests", "http", "pip", "2.31", "1;2;3", 4),
            (2, "openssl", "crypto", "vcpkg", "3.0", "4", 3),
            (3, "serde", "ser", "cargo", "1.0", "5", 4),
            (1, "pytest", "test", "pip", "8.0", "1;2;3", 5),
        ],
    )
    cur.executemany(
        "INSERT INTO patterns(domain,title,problem,solution,anti_pattern,snippet,source_ids,confidence) VALUES (?,?,?,?,?,?,?,?)",
        [
            ("python", "EAFP", "p", "s", "a", "x", "1;2;3;4", 5),
            ("web", "CSP", "p", "s", "a", "x", "5;6", 4),
            ("security", "least-priv", "p", "s", "a", "x", None, 3),
            ("devops", "immutable", "p", "s", "a", "x", "1;2", 4),
        ],
    )
    cur.executemany(
        "INSERT INTO tutorials(title,url,domain,level,summary,source_ids,confidence) VALUES (?,?,?,?,?,?,?)",
        [
            ("T1", "https://ex/t1", "python", "beginner", "s", "1;2", 4),
            ("T2", "https://ex/t2", "web", "intermediate", "s", "3", 4),
            ("T3", "https://ex/t3", "c_cpp", "advanced", "s", "4", 3),
        ],
    )
    cur.executemany(
        "INSERT INTO methodologies(name,domain,summary,steps,source_ids,confidence) VALUES (?,?,?,?,?,?)",
        [
            ("M1", "python", "s", "a\nb\nc", "1;2", 4),
            ("M2", "web", "s", "d\ne\nf", "3", 4),
            ("M3", "security", "s", "g\nh\ni", "4", 3),
        ],
    )
    cur.executemany(
        "INSERT INTO vulnerabilities(cve,ecosystem,package,severity,summary,fixed_in,source_ids,confidence) VALUES (?,?,?,?,?,?,?,?)",
        [
            ("CVE-2024-0001", "pip", "x", "HIGH", "s", "1.0", "nvd:CVE-2024-0001", 4),
            ("CVE-2024-0002", "pip", "y", "MODERATE", "s", "2.0", "osv:GHSA-test", 4),
            ("CVE-2024-0003", "pip", "z", "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H", "s", "3.0", "nvd:CVE-2024-3", 4),
            ("CVE-2024-0004", "npm", "w", "LOW", "s", "1.1", "osv:GHSA-w", 4),
            ("CVE-2024-0005", "pip", "v", "unknown", "s", None, "nvd:CVE-2024-5", 3),
        ],
    )
    cur.executemany(
        "INSERT INTO security_tools(name,category,subcategory,kali_pkg,blackarch_pkg,availability,niche_use,source_url,source_id,added_at,confidence) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("GoPhish", "red_team", "phish", "gophish", "", "verified", "n", "https://github.com/gophish/gophish", 1, "2024-01-01", 4),
            ("Evilginx2", "red_team", "mitm", "evilginx2", "", "verified", "n", "https://github.com/kgretzky/evilginx2", 2, "2024-01-01", 4),
            ("Nmap", "recon", "scan", "nmap", "", "verified", "n", "https://nmap.org", 3, "2024-01-01", 5),
            ("Amass", "osint", "enum", "amass", "", "verified", "n", "https://github.com/owasp-amass", 4, "2024-01-01", 4),
        ],
    )
    cur.executemany(
        "INSERT INTO code_reviews(task,lang,file_path,finding,severity,resolution,verified_by,source_ids) VALUES (?,?,?,?,?,?,?,?)",
        [
            ("t1", "python", "a.py", "f1", "high", "r1", "model:gpt", "independent-reviewer-subagent"),
            ("t2", "c", "b.c", "f2", "low", "r2", "operator", "1;2"),
        ],
    )
    cur.executemany(
        "INSERT INTO errors(lang,error_sig,cause,fix,recurrence,verified_by) VALUES (?,?,?,?,?,?)",
        [
            ("python", "e1", "c1", "f1", 1, None),
            ("c", "e2", "c2", "f2", 2, None),
        ],
    )
    cur.execute(
        "INSERT INTO research_runs(ran_at,mode,model,items_new,notes) VALUES ('2024-01-01','deterministic',NULL,0,'n')"
    )
    cur.executemany(
        "INSERT INTO review_queue(kind,payload,status) VALUES (?,?,?)",
        [
            ("vuln", '{"ok": true}', "pending"),
            ("synthesis", "not json at all", "pending"),
        ],
    )
    conn.commit()
    conn.close()
    return path
