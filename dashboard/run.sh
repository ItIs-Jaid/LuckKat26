#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# --no-project: avoid uv walking UP to the foreign ../pyproject.toml (localhostops)
uv venv --no-project
uv pip install --no-project -r requirements.txt

# KB store (read-only by the server). Override with KB_DB_PATH for the NAS mount.
export KB_DB_PATH="${KB_DB_PATH:-$PWD/../kb/kb.db}"

# Metrics store (writable). Dedicated *.db, gitignored. Override if desired.
export METRICS_DB_PATH="${METRICS_DB_PATH:-$PWD/metrics.db}"

# METRICS_SECRET is PASSED THROUGH from the environment only. Do NOT hardcode a
# secret here. If unset, the metrics layer falls back to an ephemeral dev secret
# and logs a warning (the secret is never logged). Set METRICS_SECRET in production.
export METRICS_SECRET="${METRICS_SECRET:-}"

# Bind localhost only — never 0.0.0.0.
exec uv run --no-project uvicorn server:app --host 127.0.0.1 --port 8000 --reload
