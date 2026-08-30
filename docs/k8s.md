# localhostops — Kubernetes / k3s deployment

The SQL store is the **product**. k3s (via k3d) is the deployment harness that
runs it as a single source of truth and serves your projector app. Local-first:
no egress; everything stays on the Dell.

## Topology

```
                ┌──────────────────── k3d / k3s (localhostops) ───────────────────┐
                │                                                                 │
   Postgres ────┤  postgres (StatefulSet, PVC 5Gi)  ←  SINGLE SOURCE OF TRUTH     │
   (DB)         │        ▲                                   ▲                     │
                │        │ writes                            │ reads (read-only)   │
                │  ingestion CronJob (demo loop, */15)   display (projector app)  │
                │                                         api (read-only API)    │
                └─────────────────────────────────────────────────────────────────┘
                          ▲
   Windows-only adapters (bluetooth_audio via Get-PnpDevice) run HOST-NATIVE on the
   Dell on a schedule, writing into the in-cluster Postgres over the cluster service.
```

Postgres is the primary store; SQLite is only a local-dev fallback (no k8s).

## Prereqs (one-time, on the Dell)
- Docker Desktop 29.6.2 (WSL2 backend) — already installed.
- `k3d` + `kubectl`: `choco install k3d kubernetes-cli` (or `winget`).
- GHCR images built + pushed (see §Build). Until then, the manifests reference
  `ghcr.io/it-is-jaid/localhostops-*:latest` — replace the repo owner with yours,
  or build locally and import into k3d (see §Local images).

## Build images (GHCR — needs your approval + token)
The `.github/workflows/build-push-ghcr.yml` auto-builds on push to `main` /
`tools-indevolopmetn`. It requires `permissions: packages: write` and pushes to
`ghcr.io`. Per the local-first boundary, **do not run a GHCR push until Jaid
approves** (it's a cloud write). One-off local push:
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u <user> --password-stdin
docker build -t ghcr.io/<user>/localhostops-display:latest -f display/Dockerfile .
docker push  ghcr.io/<user>/localhostops-display:latest   # repeat for api, pipeline
```

## Local images (no registry — fastest dev path)
```bash
docker build -t localhostops-display  -f display/Dockerfile  .
docker build -t localhostops-api      -f api/Dockerfile      .
docker build -t localhostops-pipeline -f pipeline/Dockerfile .
k3d image import localhostops-display localhostops-api localhostops-pipeline -c localhostops
# then edit k8s/base/* image names to localhostops-*:latest (drop the ghcr.io/... prefix)
```

## Bring the cluster up
```bash
bash scripts/setup-k3d.sh
# → creates cluster, applies k8s/base, waits for Postgres, runs init_db into PG
```
Projector board: **http://localhost:8000/** (k3d loadbalancer port-forward).

## Verify
```bash
kubectl -n localhostops get pods
kubectl -n localhostops exec deploy/display -- curl -s localhost:8000/api/board | head
kubectl -n localhostops logs job/ingestion-...   # confirms ETL wrote rows
```

## Validate manifests without a cluster
```bash
kubectl kustomize k8s/base            # renders all YAML
docker compose -f docker-compose.yml config   # original postgres-only compose
```

## Hybrid ingestion note
`bluetooth_audio` calls Windows `Get-PnpDevice` — it **cannot** run in a Linux pod.
Run it host-native (Task Scheduler / a small loop on the Dell) with
`DATABASE_URL` pointed at the cluster Postgres service
(`postgres.localhostops.svc.cluster.local:5432`). Other portable adapters
(demo, future cross-platform ones) run in the `ingestion` CronJob.

## Tear down
```bash
k3d cluster delete localhostops
```
