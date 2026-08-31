# KB Dashboard — Agentic Multi-Layer Review Findings (VERIFIED)

**Date:** 2026-08-30 (second wave) · **Swarm:** 5 parallel subagents (security / k3s-NAS /
data-layer / frontend-GUI / devops) · **Lead QA:** every HIGH/critical self-report
re-verified against code + disk + live PoC (not trusted blindly).

**Verdict:** SHIP-READY (local-first, ClusterIP/LAN). One CRITICAL data bug found and
**fixed** this wave (C-1). Three swarm "HIGH" claims were **false positives** caught in
Lead QA (see §3). 14/14 pytest green; C-1 regression test added.

---

## 1. Findings register (severity · status — VERIFIED)

| # | Sev | Lens | Issue | File:line | Status |
|---|-----|------|-------|-----------|--------|
| C-1 | CRITICAL | Data | Severity-sort keyset cursor compares raw TEXT `severity` vs numeric rank → DESC drops rows, ASC infinite-loops | `db.py:252-264` | ✅ FIXED — cursor now uses `sort_expr`; regression test added |
| F4 | HIGH | Frontend | Summary-card keys via `innerHTML` unescaped (claimed) | `index.html:277,293` | ❌ FALSE POSITIVE — already `esc(k)`; Lens-1 confirmed safe |
| F1 | HIGH | DevOps | `git add -A` leaks foreign localhostops tree | `.gitignore` | ❌ FALSE POSITIVE — `git add -A -n` proves `display/ k8s/ docker-compose.*.yml requirements*.txt` are ignored |
| F2 | HIGH | DevOps | uv walks up to foreign `../pyproject.toml` | `run.sh/run.ps1` | ❌ FALSE POSITIVE — already use `uv ... --no-project` |
| F20 | LOW | DevOps | stray `dashboard/None` junk file | — | ❌ FALSE POSITIVE — not present in tree |
| M1 | MED | Data | Documented `cd dashboard && uv run pytest -q` fails at collect (`import db`) | `conftest.py` | ✅ FIXED — added `dashboard/pytest.ini` (`pythonpath=.`) |
| F6 | MED | Security | No auth → full LAN KB dump via keyset walk | `server.py` | ⚪ ACCEPTED — local-first LAN; ClusterIP only, never NodePort |
| F7 | MED | k3s | Pod lacks `securityContext` | `dashboard.yaml` | ⚠️ DOC'D — runAsNonRoot/drop-ALL/seccomp in RUNBOOK |
| F8 | MED | Security | Malformed `after` cursor → 500 | `server.py:83` | ✅ CLOSED — broad `except` → 400 (PoC verified) |
| F9 | MED | Data | Raw `severity` sort lexical nonsense | `db.py:199-203` | ✅ CLOSED — normalized rank CASE |
| F10 | MED | Data | `total` shrank per page | `db.py:273-275` | ✅ CLOSED — COUNT excludes cursor |
| F11 | MED | Data | NULL sort value dropped rows | `db.py:247-270` | ✅ CLOSED — NULL-safe keyset |
| F12 | MED | k3s | `/health` not DB-aware | `server.py:28-36` | ✅ CLOSED — opens DB, 503 on failure |
| F15/F16 | MED | DevOps | Floating `>=` deps / unpinned base | `requirements.txt`,`Dockerfile` | ⚠️ DOC'D — pin+hash + Trivy in CI (future) |
| F17 | MED | k3s | NFS UID/gid for non-root | `Dockerfile:20` | ⚠️ DOC'D — `anonuid=10001` on NAS export |
| F18 | LOW | Security | `q` length unbounded (claimed) | `db.py` | ❌ FALSE POSITIVE — already capped at 256 (`db.py:194-195`) |
| F19 | LOW | Security | No max-fetch cap (claimed) | `index.html` | ❌ FALSE POSITIVE — `ENSURE_MAX_DEPTH=256` exists |
| F21 | LOW | Data | `severity` *filter* ignores normalization (claimed) | `db.py:221-238` | ❌ FALSE POSITIVE — already compares NORMALIZED token |
| F22 | LOW | Data | unicode `isdigit` crash (claimed) | `db.py:319` | ❌ FALSE POSITIVE — already guarded by `isascii()` |
| F13/F14/F23 | MED | k3s | image name / `:latest` rollout / `intr` mountOption | `dashboard.yaml` | ⚠️ DOC'D in RUNBOOK |

✅ = fixed in code · ❌ = false positive (Lead QA) · ⚠️ = deploy-side, documented in `deploy/RUNBOOK.md` · ⚪ = accepted.

---

## 2. C-1 root cause + fix (the one real bug)

`query_rows()` builds ORDER BY from `sort_expr` (= `SEVERITY_RANK_CASE`, numeric 0–4),
but the keyset cursor predicate interpolated the **raw** `{sort}` column (`severity`, TEXT)
while binding the numeric rank. In SQLite `TEXT < INTEGER` is always FALSE and `>` always
TRUE (storage-class order), so DESC pagination silently stopped after page 1 and ASC
re-returned the top rows forever (verified PoC: DESC lost rows 3,4,5; ASC repeated `[5,3]`).

**Fix:** cursor predicate now compares `{sort_expr}` (not `{sort}`); for non-severity sorts
`sort_expr == sort` so it's a no-op. `_encode/_decode_cursor` already carry the numeric rank,
so binding stays consistent.

---

## 3. False positives caught by Lead QA (why the swarm alone is not enough)

- **Card XSS (Lens 4 HIGH):** code at `index.html:277,293` uses `esc(k)`; Lens 1's grep
  confirmed all 12 `innerHTML` sinks are escaped or `textContent`-bound. NOT vulnerable.
- **git foreign-tree leak (Lens 5 HIGH):** authoritative `git add -A -n` in the worktree
  stages only `dashboard/`, `docs/`, `deploy/`, `.github/`, `scripts/`, `tools/`, root
  `pyproject.toml`/`uv.lock`/`README.md` — **not** `display/`, `k8s/`, `docker-compose.*.yml`,
  `requirements*.txt`. `.gitignore` already excludes the foreign tree.
- **uv pollution (Lens 5 HIGH):** `run.sh:4-5` / `run.ps1:6-7` already pass `--no-project`.
- **`dashboard/None` (Lens 5 LOW):** not present.
- Plus the Lens-5 "OPEN" items F18/F19/F21/F22 are actually already implemented (q cap,
  fetch depth cap, normalized severity filter, isascii guard).

---

## 4. GUI design spec (from Lens 4 — not yet built)

**What to keep:** the LOCKED backend contract (GET /health, /api/tables, /api/summary,
/api/rows, /api/row/{table}/{id}) and the virtualized-windowing table (28px row, spacer cap,
rAF-throttled render). **What to add in WebStorm:** cyberpunk tokens (CDN-free inline CSS,
`--bg:#0a0a12`, neon cyan `#00f0ff` + magenta `#ff2bd6`, scanline/grid/glow, monospace stack);
a left "FILE EXPLORER" panel that references local/NAS files via read-only `/api/fs/*`
endpoints (allowlisted roots, `resolve().commonpath` traversal guard); keyboard nav + Esc
drawer-close for a11y; a prefetch-progress guard. See `dashboard/review/04-frontend-gui.md`.

---

## 5. Verification evidence

- `cd dashboard && uv run pytest -q` → **14 passed** (13 prior + new `test_query_rows_severity_sort_keyset_correct`).
- PoC (re-run after fix): DESC walks `[1,2,4,3,5]`, ASC walks `[5,3,4,2,1]` — full coverage,
  no drops, no loops, in both directions.
- Security Lens PoC: `?after=garbage` → 400; SQLi in `sort`/`dir`/`filters` → 400 (whitelisted).

## 6. Outstanding (future)

- Pin+hash deps; base-image digest; Trivy scan in CI (F15/F16).
- Apply WAL/import/UID/NFS runbook on the real NAS + k3s node.
- Build cyberpunk GUI + `/api/fs/*` file-explorer (§4).
