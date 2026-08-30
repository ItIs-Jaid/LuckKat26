# CONTINUE — DevSecLocHostOps Dashboard + Interaction Metrics

> Paste this into a NEW chat to resume the build if the current session is interrupted.
> Local-first boundary: do NOT push to GitHub unless the operator explicitly approves.

## What this is
A local-first FastAPI dashboard over the DevSecLoc knowledge base (`kb/kb.db`, read-only),
plus a **new localhost-interaction-metrics layer** backed by a dedicated SQLite `metrics.db`.
One cohesive local app, push-ready to public GitHub with the foreign `localhostops` tree excluded.

## Locked design contract (READ FIRST — it is binding)
`docs/superpowers/specs/2026-08-30-devsecloc-dashboard-metrics-design.md`
- API contract, cookie scheme (`METRICS_VISITOR` = `<vid>.<sig>`, HMAC-SHA256 with `METRICS_SECRET`),
  DB schema (`visitors` + `events`), security rules, and test evidence requirements are all LOCKED.
- Build every tier against those exact values. Do not change the contract; change code to match it.

## Approved scope
- **In scope:** dashboard core (FastAPI + `kb/kb.db` read-only + virtualized GUI) **and** the metrics layer
  (a dedicated writable `metrics.db`, signed-cookie visitor tracking, `POST /api/metrics`, `GET /api/metrics/summary`).
- **Out of scope / never published:** the foreign `localhostops` tree (`api/`, `pipeline/`, `data/`, `analysis/`,
  `display/`, `k8s/`, `docker-compose*.yml`, `requirements*.txt`, `docs/pipeline.md`, `.env.example`) — excluded by `.gitignore`.
- `dashboard/` itself IS committable. Never commit a live `*.db`.

## 3-tier execution structure used
- **Lead** → 3 **Supervisors** (disjoint file ownership) → **Leaf** workers. Each tier verifies with real tests before returning.
- **Supervisor A (backend):** `dashboard/metrics.py`, `dashboard/server.py` (router + cookie), `dashboard/tests/test_metrics.py`.
- **Supervisor B (GUI):** `dashboard/static/index.html` (metrics panel + `track()`), GUI parts of `dashboard/tests/test_integration.py`.
- **Supervisor C (hygiene/docs):** `.gitignore` scrub, `dashboard/README.md` metrics section, `dashboard/run.sh` env defaults, this continue prompt, final `git status` / `git add -A -n` scrub check.
- **Lead (after A/B/C):** cohesive boot test in `dashboard/tests/test_integration.py`, full suite, live boot + curl cookie→log→summary, verify KB read-only, finalize this prompt.

## Status (TODO — fill in as tiers complete)
- [ ] Supervisor A: `metrics.py` + `server.py` router + `test_metrics.py` — **status: ___**
- [ ] Supervisor B: `index.html` metrics panel + `track()` + integration GUI tests — **status: ___**
- [ ] Supervisor C: `.gitignore` scrub + README section + `run.sh` env + `CONTINUE.md` — **DONE** (this file)
- [ ] Lead: cohesive boot test + full suite green + live curl verification + finalize — **status: ___**
- [ ] Foreign tree + `*.db` confirmed unstaged (`git add -A -n`) — **status: ___**
- [ ] Operator-approved push — **NOT DONE (local-first boundary)**

## Verification gate (must pass before declaring done)
1. **Full pytest green:** `cd dashboard && uv run --no-project pytest -q` — existing 14 KB tests **and** the new
   `test_metrics.py` + `test_integration.py` all pass. `test_metrics.py` uses a temp `metrics.db` (never the live file).
2. **Live curl proof:** boot `./run.sh`, then
   `curl -c /tmp/j -b /tmp/j -s -X POST localhost:8000/api/metrics -H 'content-type: application/json' -d '{"event":"page_view"}'`
   → returns `{"ok":true,"id":1}`; then
   `curl -b /tmp/j -s localhost:8000/api/metrics/summary` → reflects the logged event
   (`events` ≥ 1, `unique_visitors` ≥ 1). Missing/invalid cookie → `401`; unknown event → `400`.
3. **KB read-only:** confirm `kb/kb.db` is opened read-only (mode=ro) and `metrics.db` is the only writable store.
4. **Scrub check:** `git add -A -n` lists only safe files (`dashboard/`, `docs/`, root `README.md`, `pyproject.toml`,
   `uv.lock`, and similar) — NOT `api/`, `pipeline/`, `data/`, `analysis/`, `display/`, `k8s/`, `docker-compose*.yml`, or any `*.db`.

## How to run
```bash
cd dashboard
./run.sh          # http://127.0.0.1:8000 (binds 127.0.0.1 only)
```
Env: `KB_DB_PATH` (default `../kb/kb.db`), `METRICS_DB_PATH` (default `metrics.db`),
`METRICS_SECRET` (passed through from env; unset → dev fallback + warning).

## Key documentation
- `dashboard/README.md` — run instructions, endpoints (KB + metrics), security model, metrics schema.
- `docs/superpowers/specs/2026-08-30-super-c-hygiene.md` — Supervisor C brief.
- `docs/superpowers/specs/2026-08-30-devsecloc-dashboard-metrics-design.md` — locked design (source of truth).
