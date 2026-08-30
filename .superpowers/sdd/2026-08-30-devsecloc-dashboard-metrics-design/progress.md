# SDD ledger — plan: docs/superpowers/specs/2026-08-30-devsecloc-dashboard-metrics-design.md

Structure: Lead (Astrid) → 3 Supervisor orchestrators (A backend / B GUI / C hygiene) → leaf workers.
Baseline: 14 existing KB dashboard tests GREEN (uv run --no-project pytest -q, dashboard/).

Rulings (Lead):
- Ruling: scope = dashboard core + NEW metrics layer only; foreign "localhostops" tree stays gitignored & excluded — why: approved by Jaid + avoids PII leak; cost if wrong: rework to fold in api/display/pipeline safely.
- Ruling: store = dedicated metrics.db (kb/kb.db stays read-only) — why: approved; cost if wrong: revert to mixed-purpose KB writes.
- Ruling: bind 127.0.0.1 only; HMAC-signed HttpOnly cookie; no PII — why: security model; cost if wrong: local info leak on LAN.
- Ruling: GitHub README presentation = ONE cohesive local-running dashboard app, 3 factual sections: (1) SQL backend (kb/kb.db read-only + metrics.db writable, schema, separation), (2) Python middle (FastAPI: KB read-only serve, metrics router, HMAC-signed cookie, localhost bind, parameterized SQL), (3) JS GUI (single-file cyberpunk, virtualized table, metrics panel, track() round-trip). Show how they connect: GUI fetch → Python reads KB / logs to metrics.db via cookie → renders back. No fluff, professional, quantified.

Tasks:
- Task A (Supervisor A — backend): metrics.py + server.py router + test_metrics.py. status: COMPLETE (deleg_7962f1df) — reported DONE, all green; Lead to verify metrics.py/server.py/conftest.py on disk at integration.
- Task B (Supervisor B — GUI): index.html panel + track() + GUI tests. status: COMPLETE (deleg_78cc82a6) — reported DONE, 28 pass; Lead to verify index.html on disk at integration.
- Task C (Supervisor C — hygiene/docs): .gitignore + README + run.sh + CONTINUE.md + git add -A -n proof. status: COMPLETE (deleg_80722fa0) — reported DONE; Lead to verify on disk at integration.
- Task L (Lead — integration & verification): test_integration.py cohesive boot test, full pytest, live curl cookie→log→summary, KB read-only check, finalize CONTINUE.md. status: PENDING (after A/B/C)
- Task P (Lead — GitHub publish): repo = github.com/ItIs-Jaid/LuckKat26 (public, master). 1 commit (KB docs snapshot). NO dashboard/ yet → entire dashboard+metrics is net-new. Existing README is old KB-docs one → extend, not overwrite. status: PENDING (awaiting A/B completion + Jaid push confirmation)

Conflict scan (before dispatch): files are disjoint by ownership (A=metrics.py/server.py/test_metrics.py; B=static/index.html; C=.gitignore/README/run.sh/CONTINUE.md; shared=test_integration.py coordinated via append convention). No shared mutable interface beyond the locked API contract. Clean.
