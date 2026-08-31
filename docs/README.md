# Docs index — agentic DevSecLocHostOps

| File | What it is |
|---|---|
| `device-inventory.md` | Verified local toolchain (JetBrains 2026.2.x, Docker Desktop) and how it maps to the "DevSecLocHostOps" checklist |
| `integration-map.md` | Exact wiring of the agent ↔ IDE stack over MCP / ACP — settings paths, commands, and config snippets |
| `tool-reference.md` | Concise, interview-ready inventory of the stack and how to describe it |
| `kb/plan.md` | Compact KB design: schema, layered agent research, deterministic daily updater, model-approval gate |
| `kb/plan.human.txt` | Plain-English version of the same plan |
| `../dashboard/README.md` | KB bulk-info dashboard (local-first FastAPI over `kb/kb.db`) |

Start at the top-level [`README.md`](../README.md) for the human overview, and
see [`../AGENTS.md`](../AGENTS.md) for the conventions agents follow when
editing this repo.
