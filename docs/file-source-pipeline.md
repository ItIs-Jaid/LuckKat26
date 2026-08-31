# File-Source Pipeline — Tutorial (flip sim roots to real mounts)

Audience: <operator>. Action-oriented. No fluff.

## (a) What this pipeline does

The file-source pipeline watches folders for new `*.csv` / `*.json` files, validates each one through a locked-down security gate (no traversal, no symlinks, size + type + magic check, zero outbound network), and loads clean records into a local SQLite/Postgres landing DB. One universal adapter (`FileSourceAdapter`) drives all three sources — local, NAS, and Pixel-9 — from a single code path.

## (b) The three source roots — why ONE code path

All three sources live in `data/device_inventory.json` as `filesource` objects. They differ only by `root` (where files appear) and `pattern` (`*.csv` vs `*.json`). The `FileSourceAdapter` reads the configured `root`, globs matching files, validates, and yields records — so local / NAS / Pixel-9 are literally the same code, just pointed at different folders:

- `local` — `data/drop` (real local path; no mount needed). Pattern `*.csv`.
- `nas-pc` — sim stand-in `data/sim_nas`; `intended_root` = `\\YOUR-NAS\localhostops\drop`. Pattern `*.csv`.
- `pixel9` — sim stand-in `data/sim_pixel`; `intended_root` = `\\PIXEL9\adsb`. Pattern `*.json`.

Until the NAS/Pixel mounts are live, the sim folders (`data/sim_nas`, `data/sim_pixel`) are placeholders so the pipeline runs end-to-end today.

## (c) How to flip sim to real

You change **only one key** in `data/device_inventory.json` — `config_json.root`. No code change, ever.

**local** — already real.
1. Drop a `*.csv` file into `data/drop`.
2. `uv run python tools/ingest/run_ingest.py --source local --once`

**nas-pc** — mount then flip the root.
1. Mount the NAS SMB share so it appears at a Windows path/drive letter, e.g.:
   - `net use Z: \\YOUR-NAS\localhostops\drop /user:YOUR-NAS\youruser`  (Windows)
   - or `/etc/fstab`: `//YOUR-NAS/localhostops/drop /mnt/nas cifs ...`  (Linux)
2. Edit `data/device_inventory.json`: change `nas-pc.config_json.root` from `data/sim_nas` to the real mounted path — the `intended_root` value (`\\YOUR-NAS\localhostops\drop`, or the `Z:\` equivalent).
3. `uv run python tools/ingest/run_ingest.py --source nas-pc --once`

**pixel9** — same pattern.
1. Mount the Pixel's SMB/adb share (or use `adb pull` to drop a file into the root), e.g. `adb pull /sdcard/adsb .` into `data/sim_pixel`, or mount `\\PIXEL9\adsb`.
2. Edit `data/device_inventory.json`: change `pixel9.config_json.root` to the real share path (`\\PIXEL9\adsb`).
3. `uv run python tools/ingest/run_ingest.py --source pixel9 --once`

## (d) The security gate (plain language)

`pipeline/security.py` — `FileIngestGuard` + `NoEgress` + `IngestRejected`. No network code anywhere.
- **Allowed roots only** — a file must sit under an approved source `root`; anything outside is rejected.
- **No traversal / symlinks** — `..`, absolute escapes, and symlink tricks are blocked.
- **Size + type + magic check** — file size and content magic (real CSV/JSON bytes) are verified; junk is dropped.
- **NO outbound network** — `NoEgress` guarantees the ingest path never phones home.
- **Schema-validated records** — CSV to `measurement`, JSON to `measurement` or `device_state`; unknown shapes become `rejected`.

Tests: `pipeline/test_security.py` (10 tests, all green).
Run them: `uv run python -m pytest pipeline/test_security.py -v`

## (e) Common commands cheat-sheet

```
# Init the landing DB (SQLite by default; --engine postgres optional)
uv run python tools/ingest/run_ingest.py --source <name> --once   # one-shot ingest
uv run python tools/ingest/run_ingest.py --source <name> --loop   # poll every poll_seconds
# Source names: local | nas-pc | pixel9
```

Views (in `analysis/source_views.sql`, wired into `init_db.py`):
- `latest_per_source` — most recent record per source.
- `daily_ingest_volume` — files/records per day per source.
- `source_health` — freshness/health per source.

Run the gate: `uv run python -m pytest pipeline/test_security.py -v`

## (f) Deferred / not built (future)

- **Network transport** — `scp` / `adb pull` that populates a `root` automatically. Today you drop files manually or mount the share.
- **Stratux GDL90 decoder** — not built. The adapter already accepts a gdl90 root, so a future decoder can just drop a file there and the same `FileSourceAdapter` ingests it.
- **k3s manifests** — not built yet; the local-first landing DB is the current target.
