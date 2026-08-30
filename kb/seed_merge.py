#!/usr/bin/env python3
"""
Merge supervisor seed JSON from kb/seed_inbox/*.json into the KB.

Each supervisor wrote one file: kb/seed_inbox/<domain>.json
Shape (all arrays optional):
{
  "domain": "python",
  "sources":   [{"kind":..., "title":..., "url":..., "tier":...}],
  "languages": [{"name":..., "version":..., "role":..., "notes":...}],
  "libraries": [{"language":..., "name":..., "category":..., "purpose":..., "ecosystem":..., "version":...}],
  "patterns":  [{"title":..., "problem":..., "solution":..., "anti_pattern":..., "snippet":...}],
  "tutorials": [{"title":..., "url":..., "level":..., "summary":...}],
  "methodologies":[{"name":..., "summary":..., "steps":...}]
}
All get source linking via the file's sources. Deterministic inserts only (no LLM).
"""
import sqlite3, json, sys, pathlib, glob

HERE = pathlib.Path(__file__).resolve().parent
DB = HERE / "kb.db"
INBOX = HERE / "seed_inbox"


def con():
    if not DB.exists():
        print("[merge] kb.db missing — run kb/init.py first"); sys.exit(1)
    return sqlite3.connect(DB)


def lang_id(c, name):
    r = c.execute("SELECT id FROM languages WHERE name=?", (name,)).fetchone()
    return r[0] if r else None


def main():
    files = sorted(glob.glob(str(INBOX / "*.json")))
    if not files:
        print("[merge] no inbox files"); return 0
    c = con()
    tot = {"sources": 0, "languages": 0, "libraries": 0, "patterns": 0,
           "tutorials": 0, "methodologies": 0}
    for fp in files:
        data = json.loads(pathlib.Path(fp).read_text(encoding="utf-8"))
        domain = data.get("domain", "general")
        src_ids = []
        for s in data.get("sources", []):
            url = s.get("url")
            if url:
                existing = c.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
                if existing:
                    src_ids.append(str(existing[0])); continue
            cur = c.execute("INSERT INTO sources(kind,title,url,tier) VALUES(?,?,?,?)",
                      (s.get("kind", "docs"), s.get("title", ""), url, s.get("tier", 3)))
            src_ids.append(str(cur.lastrowid))
            tot["sources"] += 1
        src_str = ";".join(src_ids)
        for l in data.get("languages", []):
            if not lang_id(c, l.get("name", "")):
                c.execute("INSERT INTO languages(name,version,role,notes,source_ids) VALUES(?,?,?,?,?)",
                          (l.get("name"), l.get("version", ""), l.get("role", ""),
                           l.get("notes", ""), src_str))
                tot["languages"] += 1
        for lib in data.get("libraries", []):
            lid = lang_id(c, lib.get("language", ""))
            c.execute("INSERT INTO libraries(language_id,name,category,purpose,ecosystem,version,source_ids) VALUES(?,?,?,?,?,?,?)",
                      (lid, lib.get("name"), lib.get("category", ""), lib.get("purpose", ""),
                       lib.get("ecosystem", ""), lib.get("version", ""), src_str))
            tot["libraries"] += 1
        for p in data.get("patterns", []):
            c.execute("INSERT INTO patterns(domain,title,problem,solution,anti_pattern,snippet,source_ids) VALUES(?,?,?,?,?,?,?)",
                      (domain, p.get("title"), p.get("problem", ""), p.get("solution", ""),
                       p.get("anti_pattern", ""), p.get("snippet", ""), src_str))
            tot["patterns"] += 1
        for t in data.get("tutorials", []):
            c.execute("INSERT INTO tutorials(title,url,domain,level,summary,source_ids) VALUES(?,?,?,?,?,?)",
                      (t.get("title"), t.get("url", ""), domain, t.get("level", ""),
                       t.get("summary", ""), src_str))
            tot["tutorials"] += 1
        for m in data.get("methodologies", []):
            c.execute("INSERT INTO methodologies(name,domain,summary,steps,source_ids) VALUES(?,?,?,?,?)",
                      (m.get("name"), domain, m.get("summary", ""), m.get("steps", ""), src_str))
            tot["methodologies"] += 1
        print(f"[merge] {pathlib.Path(fp).name}: +{len(src_ids)} sources")
    c.commit(); c.close()
    print("[merge] totals:", json.dumps(tot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
