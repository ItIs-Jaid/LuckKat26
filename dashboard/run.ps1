# PowerShell launcher for the local-first KB dashboard.
# Equivalent of run.sh. Requires uv on PATH.
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

uv venv --no-project
uv pip install --no-project -r requirements.txt

if (-not $env:KB_DB_PATH) {
    $env:KB_DB_PATH = "$PSScriptRoot/../kb/kb.db"
}

uv run --no-project uvicorn server:app --host 127.0.0.1 --port 8000 --reload
