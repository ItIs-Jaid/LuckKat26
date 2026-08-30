#!/usr/bin/env python3
"""
Seed the DevSecLoc KB `security_tools` table from security-tools-reference.md.

- Parses the four tool categories (red_team, recon, cloud, osint) out of the
  reference markdown (pipe tables: name | kali_pkg | blackarch_pkg | niche | url).
- Cleans package cells (strips backticks + emoji markers).
- Inserts each tool's source_url into `sources` so the daily updater's URL
  re-validation keeps links fresh (self-improving KB).
- Idempotent: INSERT OR IGNORE on the (name, category) unique key and on sources.url.

Run:
  python kb/seed_security_tools.py
  python kb/seed_security_tools.py --ref /path/to/security-tools-reference.md
"""
import sqlite3, re, pathlib, sys, argparse, unicodedata

HERE = pathlib.Path(__file__).resolve().parent
DB = HERE / "kb.db"
DEFAULT_REF = HERE.parent / "security-tools-reference.md"

CATEGORY_BY_SECTION = {
    "1": "red_team",
    "2": "recon",
    "3": "cloud",
    "4": "osint",
}
# emoji / formatting we strip from package cells
STRIP_CHARS = "`* \t"


def clean(cell: str) -> str:
    """Remove backticks, asterisks, and whitespace from a package cell.

    Keeps the ⚠️ marker so storage records whether the tool is native or external
    (⚠️ = absent from that distro's default repo; install via pip/git).
    """
    return "".join(ch for ch in cell if ch not in STRIP_CHARS).strip()


def is_url(cell: str) -> bool:
    return bool(re.search(r"https?://", cell))


def parse_ref(path: pathlib.Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    cat = None
    sub = None
    rows = []
    for ln in lines:
        m = re.match(r"^##\s+(\d+)\.", ln)
        if m:
            cat = CATEGORY_BY_SECTION.get(m.group(1))
            sub = None
            continue
        m3 = re.match(r"^###\s+(.+)$", ln)
        if m3:
            sub = clean(m3.group(1))
            continue
        if not ln.startswith("|"):
            continue
        if cat is None:
            continue
        # split("|") yields ['', c1, c2, c3, c4, c5, ''] for a 5-col table.
        # Drop the leading/trailing empties from the outer pipes but KEEP inner
        # blank cells, so a tool row with an empty package cell is not collapsed
        # below 5 entries and silently dropped.
        cells = [c.strip() for c in ln.split("|")[1:-1]]
        if len(cells) < 5:
            continue
        name = clean(cells[0])
        kali = clean(cells[1])
        blackarch = clean(cells[2])
        niche = clean(cells[3])
        url = cells[4].strip()
        if not name or not is_url(url):
            continue  # skip header/separator rows
        # availability: native if BOTH distro cells lack the ⚠️ external marker,
        # else unverified (external pip/git install).
        both_external = ("⚠️" in cells[1]) and ("⚠️" in cells[2])
        avail = "verified" if not both_external else "unverified"
        rows.append({
            "name": name, "category": cat, "subcategory": sub,
            "kali_pkg": kali, "blackarch_pkg": blackarch,
            "availability": avail, "niche_use": niche, "source_url": url,
        })
    return rows


def ensure_table(con):
    con.execute("""
    CREATE TABLE IF NOT EXISTS security_tools (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT,
        kali_pkg TEXT,
        blackarch_pkg TEXT,
        availability TEXT,
        niche_use TEXT,
        source_url TEXT,
        source_id INTEGER REFERENCES sources(id),
        added_at TEXT DEFAULT (datetime('now')),
        confidence INTEGER DEFAULT 3
    )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_sectools_cat ON security_tools(category)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_sectools_name ON security_tools(name)")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sectools_uniq ON security_tools(name, category)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=str(DEFAULT_REF), help="path to security-tools-reference.md")
    args = ap.parse_args()
    ref = pathlib.Path(args.ref)
    if not ref.exists():
        print(f"[seed] reference not found: {ref}", file=sys.stderr); return 1
    if not DB.exists():
        print(f"[seed] {DB} missing — run kb/init.py first", file=sys.stderr); return 1

    rows = parse_ref(ref)
    con = sqlite3.connect(DB)
    ensure_table(con)
    n_tool, n_src = 0, 0
    for r in rows:
        cur = con.execute("SELECT id FROM sources WHERE url=?", (r["source_url"],))
        sid = cur.fetchone()
        if sid is None:
            con.execute("INSERT INTO sources(kind,title,url,tier,last_ok) VALUES('github',?,?,3,1)",
                        (r["name"], r["source_url"]))
            n_src += 1
            sid = (con.execute("SELECT id FROM sources WHERE url=?", (r["source_url"],)).fetchone()[0],)
        sid = sid[0]
        con.execute(
            "INSERT OR IGNORE INTO security_tools"
            "(name,category,subcategory,kali_pkg,blackarch_pkg,availability,niche_use,source_url,source_id)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (r["name"], r["category"], r["subcategory"], r["kali_pkg"], r["blackarch_pkg"],
             r["availability"], r["niche_use"], r["source_url"], sid))
        if con.execute("SELECT changes()").fetchone()[0]:
            n_tool += 1
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM security_tools").fetchone()[0]
    con.close()
    print(f"[seed] parsed {len(rows)} tool rows; inserted tools={n_tool}, new sources={n_src}; total tools={total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
