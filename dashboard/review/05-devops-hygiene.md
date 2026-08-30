# 05 — DevOps / Docker / Repo-Hygiene Review (Red Hat / enterprise-k8s lens)

**Reviewer:** subagent #5 · **Lens:** DevOps, Docker, repo hygiene, Windows+uv pitfalls, Red Hat/UBI/OCP sensibility
**Scope:** `dashboard/*`, `deploy/k8s/*`, root `.gitignore`/`README.md`/`docs/README.md`; localhostops exclusion check.
**Method:** READ-ONLY. Verified on disk via `git status`, `git check-ignore -v`, and a definitive `git add -A -n` (dry-run) against the worktree at `C:/Users/Jaide/agentic-DevSecLocHostOps/.worktrees/tools-indevolopmetn`.

> Evidence note: `git check-ignore` in this **nested worktree** resolves ignore rules against the *parent* repo's `.gitignore` (the worktree lives under `.worktrees/...` inside the main repo). Those results are misleading. The authoritative test is `git add -A -n` — used throughout below.

---

### [HIGH] Foreign localhostops tree leaks via `git add -A`
**file:** `.gitignore:15-24` (localhostops exclude block is incomplete)
**Evidence (dry-run `git add -A -n`, filtered):** would stage 16 out-of-scope files —
`display/Dockerfile`, `display/server.py`, `display/static/index.html`,
`docker-compose.display.yml`, `docker-compose.stack.yml`,
`k8s/base/{api,display,ingestion-cronjob,kustomization,namespace,postgres-secret,postgres}.yaml`,
`requirements.txt`, `requirements-api.txt`, `requirements-display.txt`, `requirements-pipeline.txt`.
**Impact:** A naive `git add -A` publishes the entire out-of-scope foreign project — including a Kubernetes `Secret` manifest (`k8s/base/postgres-secret.yaml`) and localhostops infra — into the public/dashboard repo. Violates the local-first governance boundary in `AGENTS.md`/`README.md`.
**Fix:** Extend the localhostops block to cover the full surface actually present:
```
display/
k8s/
docker-compose.display.yml
docker-compose.stack.yml
requirements*.txt
```
(and any other localhostops manifests at root). Re-verify with `git add -A -n` until zero foreign paths appear.
**Good news:** the *explicit* confirm list — `api/ pipeline/ data/ analysis/ docker-compose.yml docs/pipeline.md .env.example kb/kb.db 561.md` — IS correctly excluded (confirmed: none appear in the dry-run). Only the *unnamed* localhostops surface leaks.

---

### [HIGH] uv upward-discovery pollution in run scripts (Windows/uv pitfall)
**file:** `dashboard/run.sh:4-5` (`uv venv` + `uv pip install -r requirements.txt`); `dashboard/run.ps1:6-7` (same)
**Evidence:** `dashboard/` has **no** `pyproject.toml`, but the worktree root does: `pyproject.toml` is the localhostops project (`name = "localhostops-pipeline"`, deps `sqlalchemy>=2.0`, `fastapi>=0.140`, `psycopg2-binary`, `python-dotenv`, …). `uv` discovers the project by walking **up** from `dashboard/`.
**Impact:** `uv pip install -r requirements.txt` (and `uv venv`) resolve against the *foreign* `../pyproject.toml`, either failing or silently installing localhostops deps (sqlalchemy/psycopg2/python-dotenv) into the dashboard `.venv` — corrupting the dev environment. This is the exact Windows+uv breakage reported earlier.
**Fix:** Make uv ignore the parent project:
```sh
uv venv --no-project
uv pip install --no-project -r requirements.txt
# or pin the interpreter explicitly:
uv pip install --python "$PWD/.venv/bin/python" -r requirements.txt
```
Apply the same `--no-project` to `run.ps1`. (The Dockerfile already avoids this — it uses `pip`, not `uv`: `dashboard/Dockerfile:13`.)

---

### [MED] Non-reproducible dependency pins in image build
**file:** `dashboard/requirements.txt:3-8` (all `>=`); `dashboard/Dockerfile:13` (`pip install --no-cache-dir -r requirements.txt`)
**Impact:** Loose `>=` ranges + `pip` (unhashed) mean two `docker build`s on different k3s nodes can resolve different transitive versions → drift, non-deterministic CVE posture, unreproducible rollbacks.
**Fix:** Pin exact versions and adopt hash-pinning: `pip install --require-hashes -r requirements.txt` (generate with `pip-compile --generate-hashes`), or commit a `uv.lock` and build with `uv pip install --frozen`. Document the supply-chain source.

---

### [MED] Unpinned base image + mutable `:latest` tag + no CVE scan
**file:** `dashboard/Dockerfile:3` (`FROM python:3.11-slim`, no `@sha256` digest); `deploy/k8s/dashboard.yaml:74` (`image: localhost/kb-dashboard:latest`, `imagePullPolicy: IfNotPresent`)
**Impact:** Floating Debian-based base + mutable `:latest` tag → builds are not byte-reproducible, rollback is impossible by tag, and there is no declared CVE-scan posture. `:latest` with `IfNotPresent` also defeats pull-on-change expectations.
**Fix:** Pin the base by digest (`python:3.11-slim@sha256:…`); tag the built image immutably (`kb-dashboard:1.0.0` or `@sha256:…`); add a Trivy/Grype scan gate in CI before `k3s ctr images import`. For Red Hat shops, document `registry.access.redhat.com/ubi9/ubi-minimal` as the RHEL/UBI alternative (note: UBI uses `microdnf`; `uv` can install Python there).

---

### [MED] k8s Deployment lacks securityContext — not OCP/Red Hat ready
**file:** `deploy/k8s/dashboard.yaml:72-103` (container has no `securityContext`)
**Impact:** Today on k3s there is no OpenShift SCC, so this runs. But if migrated to OpenShift, the default `restricted-v2` SCC requires `runAsNonRoot`, `allowPrivilegeEscalation:false`, `seccompProfile: RuntimeDefault`, and dropped capabilities — none are set, so the Pod would be rejected. The image *does* run as `uid 10001` non-root (`dashboard/Dockerfile:20-21`) — a good baseline — but the Pod declares nothing.
**Fix (add to container spec):**
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  allowPrivilegeEscalation: false
  seccompProfile: { type: RuntimeDefault }
  capabilities: { drop: [ "ALL" ] }
# optional hardening (app is stateless, DB is read-only mount):
# readOnlyRootFilesystem: true
```

---

### [MED] Machine-specific hardcoded Windows path in run scripts (portability + minor PII)
**file:** `dashboard/run.sh:6` (`KB_DB_PATH="…C:/Users/Jaide/agentic-DevSecLocHostOps/kb/kb.db"`); `dashboard/run.ps1:10` (same)
**Impact:** Hardcodes the operator's Windows user dir. Breaks on any other machine and commits the operator username (`Jaide`) into the deliverable repo (minor PII / hygiene). k8s (`dashboard.yaml:79-80`) and the Dockerfile (`Dockerfile:7`) correctly override to `/data/kb.db` — the *local* default is the only issue.
**Fix:** Default to a repo-relative path resolved from the script dir, e.g. `KB_DB_PATH="${KB_DB_PATH:-$SCRIPT_DIR/../kb/kb.db}"` (bash) / `$PSScriptRoot/../kb/kb.db` (ps1), or make it env-only.

---

### [LOW] Stray empty file `dashboard/None` would be committed
**file:** `dashboard/None` (0-byte file; name is literally `None`)
**Impact:** Junk artifact ships in the dashboard deliverable; suggests a `str(None)` filename bug somewhere. Cosmetic but unprofessional in a committed tree.
**Fix:** Delete `dashboard/None`. Trace the code that wrote it.

---

### [LOW/INFO] `k8s/base/postgres-secret.yaml` is localhostops infra (covered by #1)
**file:** `k8s/base/postgres-secret.yaml:13-16`
**Evidence:** Currently holds only placeholders (`POSTGRES_PASSWORD: changeme`, `DATABASE_URL: …***…`). **No real secret is exposed today.**
**Note:** It leaks *as localhostops infra* via #1. If a real password is ever pasted in, this becomes a **CRITICAL** secret-leak. Keep it excluded and never commit real creds (use `kubectl create secret` at runtime, per the file's own comment).

---

## PASS (verified, no action)
- **No secret/`.env` copied into image** — `dashboard/Dockerfile:12-17` COPYs only `requirements.txt`, `server.py`, `db.py`, `static`. `.dockerignore` excludes `.venv/ __pycache__/ tests/ .env` (item #5 PASS).
- **HEALTHCHECK present & aligned** — `Dockerfile:24-25` probes `/health`; k8s readiness/liveness also hit `/health` (`dashboard.yaml:85-96`). `server.py:28-30` serves `{"status":"ok"}` (item #1 partial PASS).
- **Explicit localhostops exclude list works** — api/ pipeline/ data/ analysis/ docker-compose.yml docs/pipeline.md .env.example kb/kb.db 561.md all absent from `git add -A -n` output (item #4 PASS for that subset).
- **`dashboard/` itself stays committable** — only its intended files stage; foreign tree is separated by #1 fix.

## Red Hat / enterprise-k8s summary
Image is a reasonable local-first start (non-root uid 10001, HEALTHCHECK, read-only NAS mount, `ReadOnlyMany`). To meet Red Hat / OCP enterprise bar: (1) pin base+image by digest and scan (Trivy/Grype); (2) add the `securityContext` block above (or it fails `restricted-v2` on OCP); (3) consider `ubi9/ubi-minimal` for RHEL shops; (4) hash-pin deps for reproducible k3s builds; (5) **fix the `.gitignore` gap (#1) before any `git add -A`** — that is the single highest-risk item found.
