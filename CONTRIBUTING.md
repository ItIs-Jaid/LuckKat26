# Contributing to agentic DevSecLocHostOps

Thanks for the interest. This is a **local-first** knowledge base + design-docs
repo — it is meant to run fully offline, with no required cloud or OAuth
dependency.

## What lives here

| Path | What it is |
|---|---|
| `README.md` | Human overview of the DevSecLocHostOps concept |
| `AGENTS.md` | Working conventions for agents editing this repo |
| `docs/` | The design: device inventory, integration map, tool reference, KB plan |
| `kb/` | SQLite KB scripts (`init`, `export`, `capture`, `daily_update`) + `seed_inbox/` JSON |
| `security-tools-reference.md` | Offline red-team / recon / cloud / OSINT tooling matrix (Black Arch vs Kali) |
| `install_security_tools.sh` | Dry-run installer that reads the matrix above |
| `ops_patterns_research.json` | Mined dev/ops patterns (libraries, methodologies) |

## How to contribute

1. Fork and branch.
2. **Keep secrets out.** Never commit `.env`, `kb/kb.db`, or `kb/export/*`.
   `.gitignore` already excludes them; exports are *generated*, not source.
3. For KB data, prefer the scripts (`python kb/...`) over hand-editing exports.
4. After schema/data changes, run `python kb/kb_export.py` so the review mirror
   stays current.
5. Open a PR — `master` is protected (requires PR, force-push blocked).

## Local-first note

The whole point of this stack is that the agent, the IDE, and the data stay on
your machine. Don't introduce cloud/OAuth couplings without explicit discussion.
