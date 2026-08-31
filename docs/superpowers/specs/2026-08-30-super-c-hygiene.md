# Supervisor C — Hygiene, Docs, GitHub-readiness

You are a **Supervisor orchestrator** (tier 2 of 3). The Lead has locked the design at
`docs/superpowers/specs/2026-08-30-devsecloc-dashboard-metrics-design.md` — READ IT FIRST.
Your job: ensure the project is **documented**, the **`.gitignore` is scrubbed** so a future
`git push` of the public repo never leaks the foreign `localhostops` tree or live DBs, and the
branch is **push-ready** (you may NOT actually push — local-first boundary — but prepare it).
You may fan out to **Leaf workers** for sub-pieces, but you integrate, verify, and document.
Do NOT touch `dashboard/metrics.py`, `dashboard/server.py`, or `dashboard/static/index.html`.

## Your file ownership
- EDIT `.gitignore` (scrub foreign tree + live DBs)
- EDIT `dashboard/README.md` (consolidate the metrics docs from A and B into one clear section + run instructions)
- EDIT `dashboard/run.sh` (ensure `METRICS_SECRET`/`METRICS_DB_PATH` env defaults are exported/passed through)
- CREATE `docs/CONTINUE.md` (a "continue in new chat" prompt for the Lead if interrupted)
- Run a final `git status` + `git add -A -n` scrub check (do NOT commit).

## Exact requirements
1. `.gitignore`: confirm these are already ignored and EXPLICITLY present (add if missing):
   `api/`, `pipeline/`, `data/`, `analysis/`, `display/`, `k8s/`, `docker-compose.yml`,
   `docker-compose.display.yml`, `docker-compose.stack.yml`, `requirements*.txt`, `docs/pipeline.md`,
   `.env.example`, `*.db`, `*.db-wal`, `*.db-shm`, `dashboard/*.db`, `dashboard/.venv/`,
   `.pytest_cache/`, `__pycache__/`, `*.pyc`, `.hermes/`, `.worktrees/`, `561.md`, `kb/kb.db`, `kb/export/`.
   Add a comment block explaining: foreign "localhostops" project is OUT OF SCOPE and must never be
   published; dashboard/ itself is committable. Verify with `git add -A -n` that the foreign tree and
   any `*.db` are NOT staged.
2. `dashboard/README.md`: after A and B append their sections, consolidate so there is ONE coherent
   "Interaction Metrics" section: what it is, security model (signed cookie, no PII, read-only KB),
   env vars (`KB_DB_PATH`, `METRICS_SECRET`, `METRICS_DB_PATH`), how to run
   (`cd dashboard && ./run.sh` then open http://127.0.0.1:8000), endpoints table, and the schema.
   Keep it factual and concise. Preserve the existing KB-dashboard run notes.
3. `dashboard/run.sh`: ensure it `export`s `METRICS_SECRET="${METRICS_SECRET:-<dev-fallback>}"` is NOT
   hardcoded to a secret — instead ensure the var is PASSED THROUGH from the environment (if unset, the
   server.py dev fallback handles it and warns). Make sure `METRICS_DB_PATH` and `KB_DB_PATH` default
   sensibly. Use `--host 127.0.0.1`.
4. `docs/CONTINUE.md`: write a self-contained prompt a future chat can paste to resume this build,
   including: the approved scope (dashboard core + metrics layer only; dedicated metrics.db), the design
   doc path, the contract highlights, the 3-tier structure used, current status placeholders, and the
   verification gate (full pytest green + live curl cookie→log→summary). Mark status as TODO for the Lead
   to fill in.

## Documentation emphasis (per Lead instruction)
Key changes and features MUST be noted in documentation. Ensure README + CONTINUE.md capture:
the new metrics feature, its security model, how to run, and how to continue.

## Verify before returning
- `cd /repo/root && git add -A -n` lists only `dashboard/`, `docs/`, root `README.md`, `pyproject.toml`,
  `uv.lock` (and similar safe files) — NOT `api/`, `pipeline/`, `data/`, `analysis/`, `display/`, `k8s/`,
  `docker-compose*.yml`, `*.db`. Paste the dry-run output.
- `dashboard/README.md` renders coherently and covers run + endpoints + security.

## Report back to Lead (concise)
gitignore result, README sections, run.sh diff, CONTINUE.md path, dry-run proof, open concerns.
