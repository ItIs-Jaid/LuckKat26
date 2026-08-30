#!/usr/bin/env python3
"""Initialize the DevSecLoc KB SQLite store from schema.sql."""
import sqlite3, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
DB = HERE / "kb.db"
SCHEMA = HERE / "schema.sql"


def main() -> int:
    if DB.exists():
        print(f"[init] {DB} already exists; leaving as-is.")
        return 0
    sql = SCHEMA.read_text(encoding="utf-8")
    con = sqlite3.connect(DB)
    con.executescript(sql)
    con.commit()
    con.close()
    print(f"[init] created {DB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
