#!/usr/bin/env python3
"""Capture code reviews & errors into the KB (AGENTS.md convention).

Deterministic logging — no LLM. `verified_by` stays NULL until the operator or an
approved model verifies it.

Examples:
  python kb/kb_capture.py review --task "fix auth bug" --lang python \
      --file path/to/x.py --finding "..." --severity medium --resolution "..."
  python kb/kb_capture.py error --lang python --sig "KeyError: 'x'" \
      --cause "..." --fix "..."
  python kb/kb_capture.py verify review 7 --by jaid
  python kb/kb_capture.py verify error 3 --by "model:tencent/hy3"
"""
import sqlite3, argparse, sys, pathlib, datetime

HERE = pathlib.Path(__file__).resolve().parent
DB = HERE / "kb.db"


def con():
    if not DB.exists():
        print("[capture] kb.db missing — run kb/init.py first"); sys.exit(1)
    return sqlite3.connect(DB)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    rv = sub.add_parser("review")
    for a in ("task", "lang", "file", "finding", "resolution"):
        rv.add_argument("--" + a, required=True)
    rv.add_argument("--severity", default="low")
    rv.add_argument("--source")
    er = sub.add_parser("error")
    for a in ("lang", "sig", "cause", "fix"):
        er.add_argument("--" + a, required=True)
    er.add_argument("--source")
    vf = sub.add_parser("verify")
    vf.add_argument("table", choices=["review", "error"])
    vf.add_argument("id", type=int)
    vf.add_argument("--by", required=True, help="<operator> | model:<name>")
    args = ap.parse_args()

    c = con()
    if args.cmd == "review":
        src = args.source or ""
        c.execute(
            "INSERT INTO code_reviews(task,lang,file_path,finding,severity,resolution,verified_by,source_ids)"
            " VALUES(?,?,?,?,?,?,NULL,?)",
            (args.task, args.lang, args.file, args.finding, args.severity, args.resolution, src))
        print(f"[capture] review logged id={c.execute('SELECT last_insert_rowid()').fetchone()[0]}")
    elif args.cmd == "error":
        row = c.execute("SELECT id,recurrence FROM errors WHERE error_sig=?", (args.sig,)).fetchone()
        if row:
            c.execute("UPDATE errors SET recurrence=recurrence+1, cause=?, fix=?, verified_by=NULL WHERE id=?",
                      (args.cause, args.fix, row[0]))
            print(f"[capture] error recurrence bumped id={row[0]} (n={row[1]+1})")
        else:
            c.execute(
                "INSERT INTO errors(lang,error_sig,cause,fix,recurrence,verified_by,source_ids)"
                " VALUES(?,?,?,?,1,NULL,?)",
                (args.lang, args.sig, args.cause, args.fix, args.source or ""))
            print(f"[capture] error logged id={c.execute('SELECT last_insert_rowid()').fetchone()[0]}")
    elif args.cmd == "verify":
        tbl = "code_reviews" if args.table == "review" else "errors"
        c.execute(f"UPDATE {tbl} SET verified_by=? WHERE id=?", (args.by, args.id))
        print(f"[capture] {tbl}#{args.id} verified_by={args.by}")
    c.commit(); c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
