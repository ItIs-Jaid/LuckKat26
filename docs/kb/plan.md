# DevSecLoc KB — Plan (compact)

```
status     : DESIGN — pending operator approval
posture    : local-first
live store : SQLite (single offline file) = operational DB
export     : kb/export/*.md + *.csv = AGENT-REVIEW-ONLY mirror (NOT the DB, NOT dev code)
future     : GitHub repo (git remote add on approval); no cloud writes until then
```

## purpose
Local reference DB for languages / libraries / patterns / tutorials / vulnerabilities /
methodologies + code-review & error capture. Auto-updates via deterministic daily research
+ gated LLM synthesis. Consulted on demand when coding questions arise.

## storage
- SQLite = real store (one file, offline, no server). Swaps to Postgres-in-Docker later w/ no schema change.
- kb/export/ = humanized markdown + CSV, generated for easy review. Source of truth stays SQLite.
- Local commits now; .gitignore secrets. Remote+pull later only on approval.

## schema (sqlite tables)
languages, libraries, patterns, tutorials, sources, vulnerabilities,
methodologies, code_reviews, errors, research_runs, review_queue
EVERY row: source_ids + accessed_at + confidence_tier  -> nothing unsourced.

## layered research (all agents)
L0  ME      : own schema, master DB, scheduler def, model-gate
L1  5 SUPs  (parallel): Python · C/C++ · Web(JS/TS) · DevOps/Docker · Sec/AppSec
                    each fans to 3-6 leaves, aggregates + normalizes to schema
L2  LEAFs   : one narrow topic each via web_search / web_extract
                    returns: sources, patterns, anti-patterns, snippets, gotchas
MERGE -> SQLite + regenerate export

## deterministic daily updater
scripts/kb_daily_update.py via Hermes cronjob, FIXED daily schedule (deterministic recur)
- DETERMINISTIC (no LLM): poll NVD / GitHub Advisory / OSV for in-scope ecosystems;
  re-validate stored URLs via hash + change-detect; deduped diffs -> vulnerabilities + research_runs
- LLM (GATED): new items / weekly synthesis -> summarize + classify
  MODEL GATE: updater PAUSES + asks the operator to pick the model each LLM run;
  no reply -> deterministic-only fallback (logs, no synthesis)
  pre-approved now; per-run model pick at run time

## code-review + error capture
scripts/kb_capture.py CLI + AGENTS.md convention: log code_reviews / errors w/ structured
fields; verified_by set only after the operator/LLM verifies; feeds patterns + libraries -> KB self-improves.

## build + verify order (post-approval)
A schema + export + updater + capture CLI + cron def + AGENTS.md
B spawn 5 supervisors -> leaves -> merge -> SQLite + export
C run updater deterministically once; validate DB + export; summary to the operator

## github readiness
local commits now; remote+pull later on approval. No cloud writes before.
```
