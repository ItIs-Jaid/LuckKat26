#!/usr/bin/env python3
"""DevSecLoc KB -> humanized review mirror (markdown + CSV).

The SQLite file (kb.db) is the live store. This generates kb/export/*.md and
*.csv for easy human review ONLY. It does NOT modify the database.
Run:  python kb/kb_export.py
"""
import sqlite3, csv, pathlib, sys, datetime

HERE = pathlib.Path(__file__).resolve().parent
DB = HERE / "kb.db"
OUT = HERE / "export"
OUT.mkdir(exist_ok=True)

TABLES = ["languages", "libraries", "patterns", "tutorials", "sources",
          "vulnerabilities", "methodologies", "code_reviews", "errors",
          "research_runs", "review_queue", "security_tools"]

TITLES = {
    "languages": "Languages", "libraries": "Libraries", "patterns": "Patterns",
    "tutorials": "Tutorials", "sources": "Sources", "vulnerabilities": "Vulnerabilities",
    "methodologies": "Methodologies", "code_reviews": "Code Reviews",
    "errors": "Errors", "research_runs": "Research Runs", "review_queue": "Review Queue",
 "security_tools": "Security Tools",
 }


def q(con, sql, args=()):
    return con.execute(sql, args).fetchall()


def cols(con, table):
    return [r[1] for r in con.execute(f"PRAGMA table_info({table})")]


def main() -> int:
    if not DB.exists():
        print("[export] kb.db missing — run kb/init.py first")
        return 1
    con = sqlite3.connect(DB)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # single combined markdown
    md = [f"# DevSecLoc KB — review mirror\n", f"_generated {ts} · source of truth: kb.db (SQLite)_\n"]
    counts = {}
    for t in TABLES:
        rows = q(con, f"SELECT * FROM {t} ORDER BY id")
        c = cols(con, t)
        counts[t] = len(rows)
        md.append(f"\n## {TITLES[t]} ({len(rows)})\n")
        if not rows:
            md.append("_empty_\n")
            continue
        # markdown table
        md.append("| " + " | ".join(c) + " |")
        md.append("| " + " | ".join(["---"] * len(c)) + " |")
        for r in rows:
            cells = [str(x).replace("\n", " ⏎ ").replace("|", "\\|")[:200] for x in r]
            md.append("| " + " | ".join(cells) + " |")
        # CSV sidecar
        with open(OUT / f"{t}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(c)
            w.writerows(rows)
    con.close()

    md.append("\n## Counts\n")
    for t in TABLES:
        md.append(f"- {TITLES[t]}: {counts[t]}")
    (OUT / "kb.md").write_text("\n".join(md), encoding="utf-8")
    print(f"[export] wrote {OUT/'kb.md'} + {len(TABLES)} csv files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
