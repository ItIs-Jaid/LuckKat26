#!/usr/bin/env python3
"""Universal file-source ingest CLI.

Runs the same ``FileSourceAdapter`` for every source declared in
``data/device_inventory.json`` (local / NAS / phone). A single
``FileIngestGuard`` is built from the UNION of all source roots, and the whole
run executes inside the ``NoEgress`` context manager, so no source can egress
and every source is forced through the identical security gate.

Reuses the helpers in ``pipeline/runner.py`` — it does NOT re-implement the
DB/upsert/connection logic.

Usage:
  uv run python tools/ingest/run_ingest.py --source local --once
  uv run python tools/ingest/run_ingest.py --source nas-pc --once
  uv run python tools/ingest/run_ingest.py --source pixel9 --once
  uv run python tools/ingest/run_ingest.py --source local --loop --max-cycles 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.adapters.file_source import FileSourceAdapter  # noqa: E402
from pipeline.runner import (  # noqa: E402
    _ph,
    ensure_tables,
    get_conn,
    log_etl_run,
    resolve_source_id,
    upsert_device_identity,
    connection_transition,
)
from pipeline.security import FileIngestGuard, NoEgress  # noqa: E402

INVENTORY = REPO_ROOT / "data" / "device_inventory.json"


def load_inventory() -> list:
    if not INVENTORY.exists():
        sys.exit(f"ERROR: inventory not found at {INVENTORY}")
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def build_guard(inventory: list) -> FileIngestGuard:
    roots = []
    for entry in inventory:
        root = (entry.get("config_json") or {}).get("root")
        if root:
            roots.append(root)
    if not roots:
        sys.exit("ERROR: no source roots found in inventory")
    return FileIngestGuard(roots)


def run_once(name: str, engine: str, inventory: list, guard: FileIngestGuard) -> int:
    ensure_tables(engine)
    conn = get_conn(engine)
    try:
        sid = resolve_source_id(conn, engine, name)

        entry = next((e for e in inventory if e["name"] == name), None)
        if entry is None:
            sys.exit(f"ERROR: source {name!r} not in inventory")
        now = datetime.now()
        upsert_device_identity(
            conn,
            engine,
            {
                "mac": entry.get("mac"),
                "name": entry.get("name"),
                "vendor": entry.get("role"),
                "model": entry.get("kind"),
                "first_seen": now,
                "last_seen": now,
            },
        )

        adapter = FileSourceAdapter(
            source={**entry, "source_id": sid}, guard=guard
        )

        raw_rows = measurement_rows = 0
        for raw in adapter.extract():
            conn.cursor().execute(
                f"INSERT INTO raw_landing(source_id, domain, payload_json, format) "
                f"VALUES ({_ph(engine)}, {_ph(engine)}, {_ph(engine)}, {_ph(engine)})",
                (sid, raw.domain, raw.payload_json, raw.format),
            )
            raw_rows += 1
            # A wholly-unparseable payload (e.g. headerless/empty CSV) is
            # rejected at the file level so one bad file cannot abort the
            # entire ingest run (per-record rejects are handled inside normalize).
            try:
                normalized = adapter.normalize(raw)
            except IngestRejected as exc:
                print(
                    f"WARN[{name}] normalize rejected {raw.format} payload: {exc}",
                    file=sys.stderr, flush=True,
                )
                continue
            for rec in normalized:
                kind = rec.get("kind")
                if kind == "measurement":
                    conn.cursor().execute(
                        f"INSERT INTO measurement(source_id, metric, ts, value_num, "
                        f"value_str, unit, quality) "
                        f"VALUES ({_ph(engine)}, {_ph(engine)}, {_ph(engine)}, "
                        f"{_ph(engine)}, {_ph(engine)}, {_ph(engine)}, {_ph(engine)})",
                        (
                            sid,
                            rec.get("metric"),
                            rec.get("ts"),
                            rec.get("value_num"),
                            rec.get("value_str"),
                            rec.get("unit"),
                            rec.get("quality"),
                        ),
                    )
                    measurement_rows += 1
                elif kind == "device_state":
                    conn.cursor().execute(
                        f"INSERT INTO device_state(source_id, state_json, ts) "
                        f"VALUES ({_ph(engine)}, {_ph(engine)}, {_ph(engine)})",
                        (sid, rec.get("state_json"), rec.get("ts")),
                    )

        for ev in adapter.collected_events:
            connection_transition(conn, engine, ev)
        for st in adapter.collected_states:
            conn.cursor().execute(
                f"INSERT INTO device_state(source_id, state_json, ts) "
                f"VALUES ({_ph(engine)}, {_ph(engine)}, {_ph(engine)})",
                (sid, st.get("state_json"), st.get("ts")),
            )
        adapter.save_state()
        conn.commit()
        log_etl_run(conn, engine, name, "ok", measurement_rows, None)
        conn.commit()

        print(
            f"INGEST_OK source={name} engine={engine} "
            f"raw_rows={raw_rows} measurement_rows={measurement_rows}"
        )
        return 0
    except Exception as exc:  # clean failure, still audit-logged
        try:
            conn.rollback()
            log_etl_run(conn, engine, name, "error", 0, str(exc)[:300])
            conn.commit()
        except Exception:  # pragma: no cover
            pass
        print(f"INGEST_ERROR source={name}: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="Source name from inventory.")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--once", action="store_true", help="Run a single cycle (default).")
    group.add_argument("--loop", action="store_true", help="Poll in a loop.")
    ap.add_argument("--engine", choices=["sqlite", "postgres"], default="sqlite")
    ap.add_argument("--max-cycles", type=int, default=5, help="Hard cap on loop cycles.")
    args = ap.parse_args()

    inventory = load_inventory()
    entry = next((e for e in inventory if e["name"] == args.source), None)
    if entry is None:
        sys.exit(
            f"ERROR: unknown source {args.source!r}. "
            f"Known: {sorted(e['name'] for e in inventory)}"
        )
    guard = build_guard(inventory)

    # No network egress permitted for the entire ingest run.
    with NoEgress():
        if args.loop:
            poll = int((entry.get("config_json") or {}).get("poll_seconds", 30))
            cycles = 0
            cap = max(1, min(args.max_cycles, 1000))  # hard cap so nothing runs away
            while cycles < cap:
                rc = run_once(args.source, args.engine, inventory, guard)
                if rc != 0:
                    return rc
                cycles += 1
                if cycles >= cap:
                    break
                time.sleep(poll)
            return 0
        return run_once(args.source, args.engine, inventory, guard)


if __name__ == "__main__":
    sys.exit(main())
