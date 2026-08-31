# Review Lens 2 — K3S / NAS Deploy (`deploy/`, `k8s/base/`)

**Scope:** Try to BREAK the k3s+NAS deployment of the KB dashboard and the sibling
`localhostops` projector stack. Read-only review — no files edited.

**In-scope (committed intent):** `deploy/RUNBOOK.md`, `deploy/k8s/dashboard.yaml`
(KB dashboard, SQLite-over-NFS, read-only).
**Referenced/foreign (gitignored):** `k8s/base/*` + `docker-compose*.yml` (the
`localhostops` projector app, Postgres-backed) — reviewed for cross-checks only.

---

## Verdict

**`changes-requested`** — The read-only SQLite-over-NFS contract is *structurally sound*
(no data-corruption path, no committed secret, probes are DB-aware). But there are
fixable hardening gaps: the in-scope deploy manifest is accidentally untracked, the
liveness probe is coupled to data availability (crash-loops on a perms/NAS blip), the
container UID hard-couples to a specific NAS squash config, and imaging uses `:latest`.
0 critical, 1 high, 4 medium, 3 low.

---

## Findings

### CRITICAL
_None._ No path that corrupts the NAS file, no RCE, no broken read-only mount mismatch.

### HIGH

**H1 — `deploy/k8s/` is swallowed by the over-broad `k8s/` gitignore rule (deploy manifest not version-controlled).**
`deploy/k8s/dashboard.yaml` is the artifact `RUNBOOK.md §7` tells you to apply
(`kubectl apply -k deploy/k8s`), but `.gitignore:23` `k8s/` matches *any* `k8s/` dir at
any depth, so `deploy/k8s/dashboard.yaml` is ignored (`git check-ignore` confirms). Only
`deploy/RUNBOOK.md` is tracked (`git check-ignore` → NOT ignored). Result: a fresh clone
has the runbook but **not** the manifest it references → the documented apply path fails.
Fix: narrow the ignore to `/k8s/` (top-level foreign project only) or add
`!deploy/k8s/` exception, then commit the manifest.

### MEDIUM

**M1 — Liveness probe is DB-aware → crash-loops on any data-access failure.**
`deploy/k8s/dashboard.yaml:102-107` livenessProbe hits `/health`, and `dashboard/server.py:28-36`
returns **503** when the KB store can't be opened (NAS down / uid-perms denied). So a
mount that *succeeds* but yields an unreadable `kb.db` (e.g. wrong NAS `anonuid`) drives
`/health`→503 → liveness kills the pod (default `failureThreshold:3`, 60s) → restart →
same 503 → **CrashLoopBackOff**. The pod correctly *never serves broken data* (fails
safe), but the real cause (permission/NAS) is masked and the node burns cycles.
Best practice: liveness = process-only (`/healthz` or TCP:8000, no FS touch); readiness =
DB-aware `/health`. Decouple them.

**M2 — Container UID hard-couples to a specific NAS squash config (no verification gate).**
`deploy/k8s/dashboard.yaml:78` `runAsUser: 10001`. `RUNBOOK.md §3:68-79` admits this only
works if the NAS export uses `all_squash,anonuid=10001` (or `chmod o+r`). With default
`root_squash` and a `0600` file owned by another uid, the read fails. There is no CI
check or startup assertion for this cross-system dependency; it fails safe (503, see M1)
but is a real runtime break if the NAS isn't matched. Also `securityContext` sets no
`runAsGroup`/`fsGroup` (fine for RO NFS, but document the expected gid 10001).

**M3 — Plaintext credentials live in tree, protected only by `.gitignore` (fragile).**
`k8s/base/postgres-secret.yaml:14` commits `POSTGRES_PASSWORD: changeme` in `stringData`,
and `docker-compose.stack.yml:16,33,44,55` hardcode `devsecloc:devsecloc` in
`DATABASE_URL`/env. These are **not committed** (`git check-ignore` → ignored under
`k8s/` / `docker-compose*.yml`), so the *committed-tree* criterion ("no plaintext secrets
committed") is met today. BUT the plaintext sits in the working tree and `.gitignore:15-17`
itself warns "`git add -A` would publish it." A single `git add -A`/`-f` or a loosened
ignore ships real credentials. Add a pre-commit secret scanner and/or move to a
SealedSecret / external secret so plaintext never rests in-tree.

**M4 — Image uses `:latest` (immutable-tag anti-pattern).**
`deploy/k8s/dashboard.yaml:74` `localhost/kb-dashboard:latest` + `imagePullPolicy: IfNotPresent`.
Re-importing a newer `:latest` tar does **not** roll the pod (k8s sees the same ref) →
must `kubectl rollout restart` (RUNBOOK §2:58-64 notes this). Rollbacks can't be pinned.
Use an immutable version tag (e.g. `kb-dashboard:1.0.0`) + digest pin.

### LOW

**L1 — Doc/manifest drift: `intr` still present.** `RUNBOOK.md:82` says "Drop `intr`
(removed from NFSv4 client; harmless warning)" yet `deploy/k8s/dashboard.yaml:31` still
lists `intr` in `mountOptions`. Harmless, but drift between runbook and manifest.

**L2 — Probes have no `timeoutSeconds`.** `deploy/k8s/dashboard.yaml:96-107` omit
`timeoutSeconds` (defaults to 1s). Under a `hard` NFS hang, `db.connect()` can block the
single uvicorn worker past the probe timeout. Add `timeoutSeconds` and/or `soft,timeo=30,
retrans=3` (RUNBOOK §4 suggests `timeo/retrans`), and prefer a non-FS `/healthz` for liveness.

**L3 — `?immutable=1` not used on the read-only open.** `dashboard/db.py:64-65` opens
`?mode=ro` (correct, prevents `-wal/-shm` writes). For a NAS updated out-of-band, adding
`&immutable=1` is the most defensive choice (skips all locking/shm, tolerates the intended
~60s staleness). Current design relies on the writer honoring DELETE journal (RUNBOOK §1),
which works but `immutable=1` removes the last residual WAL-sidecar risk.

---

## Verified OK (the contract holds)

- **PV/PVC read-only binding matches the URI mode (lens 1).** `ReadOnlyMany` PV +
  PVC (`deploy/k8s/dashboard.yaml:22-48`), `volumeMount.readOnly: true` (`:93`), and
  `db.py:64` `?mode=ro` are consistent. Mount path `/data` + `KB_DB_PATH=/data/kb.db` (`:89`)
  line up with PV `nfs.path: /volume1/kb`. No mismatch.
- **NFS WAL/`-shm` sidecar hazard avoided (lens 5).** App `?mode=ro` + `nolock` mount
  (`:29`) + writer-side `journal_mode=DELETE` enforcement (RUNBOOK §1:21-33) = safe.
  No `-wal/-shm` write sidecar on the RO share.
- **No write path can corrupt the NAS file (lens 6).** `readOnlyRootFilesystem: true`
  (`:80`), `?mode=ro` open, `PYTHONDONTWRITEBYTECODE=1` (`dashboard/Dockerfile:6`), and the
  only writable mounts are `/tmp` (emptyDir, `:94-95`) and the RO NAS. No write endpoints in
  `server.py`; `make_fixture_db` is test-only.
- **`/health` is correctly DB-aware (lens 4).** `server.py:28-36` returns 503 when the store
  is missing/unreadable → readiness removes pod from Service. (Liveness coupling is M1.)
- **Image distribution path is correct (lens 3).** `localhost/` ref matches the imported
  ref after `docker tag`+`k3s ctr images import` (RUNBOOK §2:42-56); the `docker.io/library/...`
  mismatch trap is documented.
- **Exposure guard in place.** Service is `ClusterIP` (`deploy/k8s/dashboard.yaml:128`);
  NodePort block is commented out (RUNBOOK §6:96-101).
- **Container hardened.** `runAsNonRoot`, `drop:[ALL]`, `seccompProfile:RuntimeDefault`,
  `allowPrivilegeEscalation:false` (`:76-84`).

---

## Compact JSON

```json
{
  "critical": [],
  "high": ["H1: deploy/k8s/dashboard.yaml untracked — over-broad .gitignore k8s/ (line 23) swallows in-scope deploy manifest; RUNBOOK apply path fails on fresh clone"],
  "medium": [
    "M1: livenessProbe=/health (dashboard.yaml:102-107 + server.py:28-36) DB-aware -> crash-loops on perm/NAS blip; decouple liveness from data",
    "M2: runAsUser:10001 (dashboard.yaml:78) hard-couples to NAS all_squash anonuid=10001; no CI/startup check (RUNBOOK §3)",
    "M3: plaintext POSTGRES_PASSWORD in k8s/base/postgres-secret.yaml:14 + devsecloc:devsecloc in docker-compose.stack.yml:16,33,44,55; gitignored (not committed) but fragile",
    "M4: image :latest (dashboard.yaml:74) + IfNotPresent blocks rollout on re-import; use immutable version/digest"
  ],
  "low": [
    "L1: intr mountOption still in dashboard.yaml:31 though RUNBOOK.md:82 says drop it",
    "L2: probes lack timeoutSeconds (defaults 1s); hard-NFS hang can wedge single worker",
    "L3: db.py:64 opens ?mode=ro but not &immutable=1; add for max NFS-safe read"
  ],
  "ok": [
    "PV/PVC ReadOnlyMany + readOnly mount matches ?mode=ro URI (dashboard.yaml:22-93, db.py:64)",
    "NFS WAL/-shm sidecar avoided via ?mode=ro + nolock + writer DELETE journal (RUNBOOK §1)",
    "no write path can corrupt NAS file (readOnlyRootFilesystem + ?mode=ro + only /tmp writable)",
    "/health DB-aware 503 when store unreadable (server.py:28-36)",
    "image distro via localhost import correctly documented (RUNBOOK §2)",
    "Service ClusterIP only; NodePort commented (RUNBOOK §6)",
    "securityContext hardened: nonroot, drop ALL, seccomp RuntimeDefault"
  ],
  "verdict": "changes-requested"
}
```
