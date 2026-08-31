# Build Prompt — Deferred File-Source Work (local-first, security-first)

> Self-contained prompt. Hand this to an agent/swarm to build the deferred
> pieces from `docs/ROLE.md` (the file-source pipeline task). The security
> layer and the universal `FileSourceAdapter` already exist and are verified
> (10/10 security gate tests green). This prompt builds ON TOP of them — it
> must not weaken the security posture.

## TL;DR
Build three deferred capabilities, in order, reusing everything that exists:
1. **Stratux/GDL90 decoder** — parse GDL90 frames the adapter already drops into a `gdl90-raw` `raw_landing` row, into typed `measurement` / `device_state` / `device_identity` rows.
2. **Network-transport reader (file-drop pattern only)** — a reader that pulls a file from a device (adb-pull / scp) into a source root; the existing `FileSourceAdapter` then ingests it. **No live UDP/socket server.** Egress happens ONLY inside the reader, never inside the ingest/normalize path (which stays wrapped in `NoEgress`).
3. **k3s manifest** — run the adapter as a pod reading an NFS-mounted NAS root. Pipeline code does NOT change; this is a deploy artifact only.

## HARD CONSTRAINTS (non-negotiable)
- **Local-first / no cloud.** Honor `561.md`. No cloud writes. No GHCR push without explicit operator approval (see `docs/k8s.md` §Build).
- **Security before network is already proven.** The ingest/normalize path MUST keep running inside `NoEgress` (see `pipeline/security.py`). Reject any design that opens sockets during `extract()`/`normalize()`.
- **Reuse, don't reimplement.** Use `pipeline/runner.py` helpers (`get_conn`, `_ph`, `ensure_tables`, `resolve_source_id`, `upsert_device_identity`, `connection_transition`, `log_etl_run`). Use `pipeline/security.FileIngestGuard` + `NoEgress`. Reuse `analysis/source_views.sql` (no schema change — keep the 7 tables).
- **One code path.** Devices differ only by `config_json` (root/pattern/transport). Do not special-case per device in the adapter.
- **act-back stays OUT OF SCOPE** unless the operator explicitly asks. `BaseAdapter.act()` stays `NotImplementedError`.
- **No schema break.** If you need columns, prefer `config_json` / `state_json` TEXT. Get operator sign-off before any DDL change.

## EXISTING RESEARCH TO REUSE
- `pipeline/adapters/file_source.py`
  - `:116` allowed_ext already includes `.gdl90`.
  - `:142-144` `.gdl90` → `format="gdl90-raw"`, `payload_json` = base64 of raw bytes (stored in `raw_landing`).
  - `:219-223` `normalize()` currently raises `IngestRejected("gdl90-raw decoding is not implemented...")` — **this is the hook you replace** with real decoding.
  - `extract()` is format-agnostic and already security-gated; leave it alone.
- `docs/k8s.md` — k3s topology. Postgres is primary store; SQLite is local-dev fallback. Portable adapters run in the `ingestion` CronJob. Windows-only adapters (bluetooth_audio) run host-native. The adapter can read an NFS-mounted NAS root inside a pod — pipeline code unchanged.
- `data/device_inventory.json` — three sources (`local`/`nas-pc`/`pixel9`); add new sources here, never hardcode. MACs are PLACEHOLDERS (`LOCAL:DELL16`, `NAS:PC-PLACEHOLDER`, `PIXEL9:PLACEHOLDER`) — keep the placeholder convention; real MACs get filled when mounts go live.

## BUILD ORDER (dependencies)
Phase 1 (decoder) → Phase 2 (reader) → Phase 3 (manifest). Each phase gates green before the next starts.

### Phase 1 — Stratux / GDL90 decoder
**File:** `pipeline/adapters/gdl90_decoder.py` (new) OR extend `file_source.py` `normalize()`.
Recommendation: **new module** `gdl90_decode(raw_bytes: bytes) -> List[dict]` returning rows with `kind` in {measurement, device_state, device_identity}. Wire it into `FileSourceAdapter.normalize()` at the `gdl90-raw` branch (replace the `IngestRejected` at `:219-223`) by base64-decoding `raw.payload_json` and calling `gdl90_decode`.
- Parse at least: Heartbeat (0x00), Ownership Report (0x0A / 0x1E), Traffic Report (0x14), Status (0x65). Map to:
  - `measurement`: e.g. `own_lat`, `own_lon`, `own_alt_ft`, `own_speed_kt`, `own_track`, `traffic_lat`, `traffic_lon`, `traffic_alt_ft` (per traffic target) — metric naming is yours, keep `value_num` finite, `ts` from frame time, `quality="ok"`.
  - `device_identity`: upsert the Stratux/ownship device by MAC (leave MAC as placeholder if unknown, but DO populate `name="stratux"`, `model="gdl90"`, `first_seen/last_seen`).
  - `device_state`: a periodic snapshot `{source, frames_seen, last_msg_id, ...}` into `state_json`.
- Every produced measurement dict MUST pass `FileIngestGuard.validate_records()` (mirror `file_source._landing`). Unknown/unparseable frames → skip with WARN, never crash the run.
- **Tests (`pipeline/test_gdl90.py`):** build a small synthetic GDL90 byte stream (CRC-included; you may use a minimal frame builder) → assert expected measurement/device_state/device_identity rows; assert garbage frame is skipped; assert `raw_landing` still holds the base64 raw.

### Phase 2 — Network-transport reader (file-drop pattern ONLY)
**New module:** `pipeline/transports/__init__.py` + `pipeline/transports/pull_reader.py`.
- A `PullReader` with `pull(source_cfg) -> Path` that, based on `config_json.transport`:
  - `"adb-pull"`: runs `adb pull <remote> <root>` (subprocess) to drop the file into the source `root`.
  - `"scp"`: runs `scp <user@host:remote> <root>` (subprocess) — host/key from `config_json`, **no secrets in code** (read from env/`561.md`-approved vault).
  - absence of `transport` → no-op (local/NAS/mobile already-mounted roots just use the existing adapter).
- **CRITICAL isolation:** the reader executes OUTSIDE `NoEgress`. The ingest step (`FileSourceAdapter.extract/normalize`) stays INSIDE `NoEgress` (as today). Prove this with a test: `socket.socket()` is allowed while the reader runs, but `socket.socket()` raises inside `FileSourceAdapter` extract/normalize (existing `test_egress_blocked` already covers ingest; add one asserting the reader's `subprocess` egress is NOT blocked).
- The reader does NOT parse — it only lands a file; the existing adapter ingests it. This is exactly the `NETWORK NOTE` from the role: "a network source just becomes another root that a reader populates."
- CLI: extend `tools/ingest/run_ingest.py --source <name> --once` so that, if the source has `transport`, it calls `PullReader.pull()` before `adapter.extract()`. Keep `--engine`/`--loop`/`--max-cycles` behavior.
- **Tests:** mock the subprocess (no real device needed) to confirm a file lands in `root` and is then ingested; confirm a failed pull is logged and does not crash.

### Phase 3 — k3s manifest (deploy artifact only)
**New:** `k8s/base/ingestion-file-source.yaml` (CronJob or Deployment) + a patch referencing the NAS NFS mount.
- Reuse the topology in `docs/k8s.md`: portable adapters run in the `ingestion` CronJob; point `DATABASE_URL` at the in-cluster Postgres service.
- The manifest mounts the NAS root via an NFS `PersistentVolume`/`Volume` at the same `root` path the inventory declares for `nas-pc`. **Pipeline code unchanged.**
- Add a `scripts/setup-file-source-cron.sh` (optional) that applies the manifest + runs one cycle for smoke.
- **Validate without a cluster:** `kubectl kustomize k8s/base` must render; `bash -n` on any shell script; `uv run python -m py_compile` on any python. Do NOT require a live cluster to merge.
- No GHCR push. Note in a comment the image is `localhostops-pipeline` (build locally + `k3d image import` per `docs/k8s.md` §Local images).

## VERIFICATION GATE (all must be GREEN before "done")
- `uv run python -m pytest pipeline/test_security.py pipeline/test_gdl90.py pipeline/test_transports.py -v` → 0 failures (security gate stays 10/10 + new tests pass).
- `uv run python -m py_compile pipeline/adapters/*.py pipeline/transports/*.py tools/ingest/run_ingest.py` → clean.
- `uv run python data/init_db.py --engine sqlite` → `INIT_DB_OK tables=7`.
- End-to-end (sqlite): drop a sample `.gdl90` into a source root → `run_ingest --source <gdl90-source> --once` → `measurement` rows present, `raw_landing` holds base64 raw, `device_identity` has the ownship device, `daily_ingest_volume` returns a real number.
- Transport: a mocked adb-pull lands a file → ingested (measurement rows present). Reader egress NOT blocked; ingest egress blocked (assert both).
- `kubectl kustomize k8s/base` renders with no error.
- `analysis/source_views.sql` still applies; `latest_per_source` / `daily_ingest_volume` / `source_health` return real rows after the runs.

## OUT OF SCOPE (do not build unless told)
- Live UDP/socket ingest server (Stratux UDP broadcast). The decoder reads DROPPED GDL90 FILES, not a live socket. If live UDP is later wanted, it becomes a reader that writes a `.gdl90` file (same file-drop pattern).
- act-back / write-back to any device.
- Cloud sync, auth on services, GHCR push.
- Any schema DDL change without operator sign-off.

## HANDOFF
- Add new sources to `data/device_inventory.json` (e.g. `stratux` with `config_json.root` pointing at the GDL90 drop dir, `pixel9` transport `"adb-pull"`).
- Append a `docs/device-inventory.md` changelog row describing what shipped.
- Leave `docs/learning-queue.md` Stratus/ADS-B item noted as "decoder built" once Phase 1 lands.
- No `git commit` / `git push` unless the operator approves (local-first boundary).
