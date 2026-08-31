"""Boot the dashboard against a throwaway synthetic KB and leave the server up.

Local-first safe: writes a fixture DB to %LOCALAPPDATA%/kb_fixture.db (NEVER the real
kb/kb.db) and points KB_DB_PATH at it, so the screenshot shows a populated app without
mutating the live NAS/KB store. Prints the bound URL.

Exit: keep serving (Ctrl-C to stop).
"""
from __future__ import annotations
import os
from pathlib import Path

import db

local = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
fixture = Path(local) / "kb_fixture.db"
if fixture.exists():
    fixture.unlink()
db.make_fixture_db(fixture)
os.environ["KB_DB_PATH"] = str(fixture)

import uvicorn
from server import app  # noqa: F401  (ensure importable under uvicorn)

print(f"KB_DB_PATH={fixture}")
uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
