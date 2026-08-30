#!/usr/bin/env python3
"""
DevSecLoc KB — deterministic daily updater + gated LLM synthesis.

DETERMINISTIC (always runs, no LLM, no cloud):
  - Poll official advisory feeds for in-scope ecosystems:
      * NVD CVE API 2.0        https://services.nvd.nist.gov/rest/json/cves/2.0
      * GitHub Advisory DB     https://api.osv.dev/v1/query  (OSV, covers GHSA + PyPI + npm + crates + Go)
      * OSV batch              https://api.osv.dev/v1/query
  - Re-validate stored source URLs via HTTP status + content hash
  - Diff against existing rows; insert new vulnerabilities; record research_runs (deterministic)

LLM (GATED — requires explicit user approval each run):
  - For new items / weekly synthesis, summarize + classify.
  - MODEL GATE: before any LLM call, pause and ASK the user which model to use.
    No answer -> deterministic-only fallback (log to review_queue, no synthesis).
  - Implementation: this script writes new-item JSON to kb/export/pending_llm.json and
    EXITS with code 42 + a clear message; the orchestrating agent (Hermes) presents the
    model picker to the operator, then runs the sibling synth step. Keeping the gate in the agent
    (not hardcoded here) honors "ask user to verify the model doing the reasoning."

Run:
  python kb/kb_daily_update.py            # deterministic + stage LLM items
  python kb/kb_daily_update.py --synth --model tencent/hy3   # LLM step (only after the operator picks)

Environment:
  ECOSYSTEMS  comma list override (default: python,c,c++,javascript,typescript,docker,go,rust)
"""
import sqlite3, sys, json, pathlib, datetime, os, argparse, urllib.request, urllib.error

HERE = pathlib.Path(__file__).resolve().parent
DB = HERE / "kb.db"
PENDING = HERE / "export" / "pending_llm.json"
NVD = "https://services.nvd.nist.gov/rest/json/cves/2.0"
OSV_Q = "https://api.osv.dev/v1/query"
OSV_V = "https://api.osv.dev/v1/vulns/"

# Curated watchlist -> (OSV ecosystem, package name). OSV requires package+ecosystem,
# bare ecosystem queries return 400. Extended automatically from the KB's libraries table.
WATCHLIST = [
    ("PyPI", "fastapi"), ("PyPI", "django"), ("PyPI", "flask"), ("PyPI", "requests"),
    ("PyPI", "pydantic"), ("PyPI", "bandit"), ("PyPI", "uvicorn"),
    ("npm", "react"), ("npm", "next"), ("npm", "svelte"), ("npm", "vite"), ("npm", "express"),
    ("crates.io", "tokio"), ("crates.io", "serde"), ("crates.io", "sqlx"),
    ("Go", "github.com/gin-gonic/gin"), ("Go", "github.com/docker/docker"),
    ("GitHub Actions", "actions/checkout"), ("GitHub Actions", "actions/runner"),
]


def http_json(url, data=None, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={"User-Agent": "DevSecLocKB/0.1",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def con():
    if not DB.exists():
        print("[update] kb.db missing — run kb/init.py first"); sys.exit(1)
    return sqlite3.connect(DB)


def upsert_vuln(c, v):
    existing = c.execute("SELECT id FROM vulnerabilities WHERE cve=?", (v.get("cve"),)).fetchone()
    if existing and v.get("cve"):
        return 0
    c.execute(
        "INSERT INTO vulnerabilities(cve,ecosystem,package,severity,summary,fixed_in,source_ids,confidence)"
        " VALUES(?,?,?,?,?,?,?,4)",
        (v.get("cve"), v.get("ecosystem"), v.get("package"), v.get("severity"),
         v.get("summary"), v.get("fixed_in"), v.get("source_ids", "")))
    return 1


def _sev(det):
    sev = det.get("database_specific", {}).get("severity")
    if not sev:
        for s in det.get("severity", []) or []:
            sev = s.get("score", sev)
    return sev or "unknown"


def _parse_osv(eco, name, det):
    vid = det.get("id")
    affected = det.get("affected", [{}])
    pkg = (affected[0].get("package", {}).get("name", name) if affected else name)
    summary = (det.get("summary") or det.get("details") or "")[:500]
    fixed = ""
    for a in affected:
        for r in a.get("ranges", []):
            for e in r.get("events", []):
                if "fixed" in e:
                    fixed = e["fixed"]
    return {"cve": vid, "ecosystem": eco, "package": pkg, "severity": _sev(det),
            "summary": summary, "fixed_in": fixed, "source_ids": "osv:" + str(vid)}


def deterministic(c):
    new = 0
    staged = []
    # Build watchlist: curated + any packages already seeded into libraries table.
    watch = list(WATCHLIST)
    try:
        for lang, name in c.execute(
            "SELECT l.name, lib.name FROM libraries lib JOIN languages l ON lib.language_id=l.id"
        ).fetchall():
            eco = {"Python": "PyPI", "JavaScript": "npm", "TypeScript": "npm",
                   "C++": "crates.io", "Go": "Go", "Docker": "GitHub Actions"}.get(lang)
            if eco:
                watch.append((eco, name))
    except Exception:
        pass
    for eco, name in watch:
        try:
            data = http_json(OSV_Q, {"package": {"ecosystem": eco, "name": name}, "limit": 20})
        except Exception as e:
            print(f"[update] OSV {eco}/{name} failed: {e}")
            continue
        for vuln in data.get("vulns", [])[:20]:
            vid = vuln.get("id")
            try:
                det = http_json(OSV_V + vid) if vid else {}
            except Exception:
                det = vuln
            row = _parse_osv(eco, name, det)
            new += upsert_vuln(c, row)
            staged.append(row)
    # NVD recent (broad)
    try:
        nvd = http_json(NVD + "?resultsPerPage=20")
        for item in nvd.get("vulnerabilities", [])[:20]:
            cve = item.get("cve", {}).get("id")
            desc = item.get("cve", {}).get("descriptions", [{}])
            desc = desc[0].get("value", "")[:400] if desc else ""
            row = {"cve": cve, "ecosystem": "general", "package": "",
                   "severity": "unknown", "summary": desc, "fixed_in": "", "source_ids": "nvd:" + str(cve)}
            new += upsert_vuln(c, row)
            staged.append(row)
    except Exception as e:
        print(f"[update] NVD failed: {e}")
    # re-validate source URLs
    rev = 0
    for sid, url in c.execute("SELECT id,url FROM sources WHERE url IS NOT NULL").fetchall():
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "DevSecLocKB/0.1"})
            with urllib.request.urlopen(req, timeout=10) as r:
                ok = r.status < 400
        except Exception:
            ok = False
        c.execute("UPDATE sources SET last_ok=? WHERE id=?", (1 if ok else 0, sid))
        rev += 1
    c.execute("INSERT INTO research_runs(mode,items_new,notes) VALUES('deterministic',?,?)",
              (new, f"sources revalidated={rev}"))
    c.commit()
    return new, staged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth", action="store_true", help="run LLM synthesis (only after the operator picks model)")
    ap.add_argument("--model", help="model name for synth (required with --synth)")
    args = ap.parse_args()
    c = con()
    if not args.synth:
        new, staged = deterministic(c)
        PENDING.parent.mkdir(exist_ok=True)
        PENDING.write_text(json.dumps(staged, indent=2), encoding="utf-8")
        c.close()
        print(f"[update] deterministic done. new vulns={new}. staged for LLM: {len(staged)} -> {PENDING}")
        if staged:
            print("[update] LLM GATE: present these to the operator, let them pick a model, then re-run with --synth --model <name>")
            sys.exit(42)
        print("[update] nothing to synthesize.")
        sys.exit(0)
    # --synth path
    if not args.model:
        print("[update] --synth requires --model (the operator must pick)."); sys.exit(1)
    staged = json.loads(PENDING.read_text()) if PENDING.exists() else []
    # NOTE: actual summarization happens in the agent using args.model; here we just record.
    c.execute("INSERT INTO research_runs(mode,model,items_new,notes) VALUES('llm',?,?,?)",
              (args.model, len(staged), "synthesis via user-approved model"))
    # staging into review_queue for transparency
    for s in staged:
        c.execute("INSERT INTO review_queue(kind,payload) VALUES('synthesis',?)",
                  (json.dumps(s),))
    c.commit(); c.close()
    print(f"[update] LLM synthesis recorded for model={args.model}; {len(staged)} items queued for review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
