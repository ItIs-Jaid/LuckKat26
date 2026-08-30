# agentic DevSecLocHostOps

*A local-first way to let your AI agent team live inside your IDE — without giving up control, privacy, or your offline workflow.*

---

## What this is

This folder is the documentation hub for a setup I call **agentic DevSecLocHostOps** — a personal, on-device stack where a reasoning agent (Hermes) and its subagent team plug directly into my JetBrains IDEs over standard protocols, so the agent can read my code, run builds, and drive the editor the same way I would — but I stay in the driver's seat.

The "DevSecLocHostOps" name is a mouthful on purpose. It's a checklist, not a buzzword:

- **Dev** — real development work, in PyCharm and CLion
- **Sec** — secrets and logic stay local; nothing is forced into a cloud
- **Loc** — *local-first*: the whole thing runs on my machine
- **Host** — my Windows box, plus Docker for containerized local services
- **Ops** — DataGrip for data, Docker for infra, agents for the repetitive parts

The deeper point: most "AI coding" tools are someone else's server, deciding what your agent can see and do. This stack flips that. The agent runs here, the IDE runs here, and the connection between them is an open protocol (MCP / ACP) I can inspect, limit, and unplug.

---

## The layers

```
YOU  ── directs ──▶  Hermes Agent (orchestrator)
                         │  delegates
                         ├──▶ Hermes subagent fan-out (research / solutions / vetting)
                         │
                         ├──▶ JetBrains IDEs (PyCharm · CLion · DataGrip)   [MCP + ACP]
                         │
                         └──▶ Gemini Spark  ── manual companion, not wired

Docker Desktop  ── local containers for DBs, build runners, agent sidecars
```

Four moving parts, all on-host:

1. **Hermes Agent** — the orchestrator. It has skills, memory, and can spin up subagents. It speaks both MCP and ACP.
2. **The JetBrains suite** — PyCharm (Python), CLion (C/C++), DataGrip (databases). All 2026.2.x, all recent enough to natively support agent protocols.
3. **Docker Desktop** — local, reproducible infra. No cloud account required to run a database or a build container.
4. **Gemini Spark** — my *human-driven* research sidekick in the Gemini app. Deliberately **not** wired in, so the local-first boundary holds.

---

## How the connection actually works

Two open protocols do the heavy lifting. Both are documented in `docs/integration-map.md` with exact settings paths and commands — this is the human version.

**MCP (Model Context Protocol) = agent ↔ tools.**
Think of it as USB-C for AI tools. The IDE can *expose* its internals as an MCP server (so Hermes can open files, run the terminal, read error inspections). Hermes can *consume* that server, or *expose* its own. One connection pattern, reused everywhere.

**ACP (Agent Client Protocol) = editor ↔ agent.**
This is how the IDE *hosts* an agent. Hermes runs in ACP mode (`hermes acp`) and shows up in the IDE's agent picker next to JetBrains' own Junie. The IDE owns the chat window; Hermes keeps its own memory, skills, and identity.

The mental model: **MCP is what the agent uses; ACP is where the agent sits.**

---

## Use cases

These are things this stack makes *natural* — not hypothetical, but the actual shape of work it enables.

### 1. "Open the file with the auth bug and fix it"
Hermes connects to the IDE's MCP server, reads `get_file_problems` (the full IntelliJ inspection engine), opens the offending file, and edits it through the same refactoring tools I'd use. I review the diff. Nothing leaves the machine.

### 2. "Run the test suite and tell me what broke"
The agent calls `execute_run_configuration` / `execute_terminal_command` in the IDE, captures output, and summarizes failures — or dispatches a *subagent* to diagnose while the main agent keeps context. Parallel reasoning, one laptop.

### 3. "Refactor this C++ module against the Python caller"
Because CLion and PyCharm are both wired, the agent can cross-reference native and scripting layers in one session — `analyze_calls` on one side, symbol lookup on the other. Hard to do by hand across two IDEs; trivial when both are MCP surfaces.

### 4. "Query the staging database and patch the migration"
DataGrip's 2026.1 release added DB tools to its MCP surface (`execute_sql_query`, `list_database_schemas`, …). The agent can read schema, run a query, and propose a migration — all local against a Dockerized DB.

### 5. "Stand up a local service and point the agent at it"
Docker gives me a Postgres or a build runner in one command. The agent connects to it over MCP. Reproducible environment, zero cloud dependency, easy to tear down.

### 6. "Research spike, then implement"
I can fan a research question out to several Hermes subagents (each its own context), get back vetted findings, then hand the synthesis to the IDE-connected agent to implement. That's the "agentic" part — a small team, not a single chatbot.

### 7. "Keep Spark for the human questions"
When I want a different model's take — drafting, open-ended research — I use Gemini Spark in the Gemini app, manually. It's a companion, not a cog. The boundary is intentional: the automated, code-touching work stays local and inspectable.

---

## Possibilities this unlocks

- **A portable, inspectable agent setup.** Because everything rides on MCP/ACP (open standards), I'm not locked to one vendor. Swap the IDE, swap the agent — the wiring pattern survives.
- **Local-first by default, cloud by choice.** Nothing here *requires* the internet. If I later add a cloud agent, it's an explicit, documented layer — not a hidden dependency.
- **Auditable automation.** MCP servers expose a known set of tools. I can see exactly what the agent can do, filter it per server, and pull the plug.
- **Interview-ready story.** This isn't "I use AI." It's "I architected a local-first agentic dev environment using open agent protocols" — which is a different, stronger sentence. See `docs/tool-reference.md` for the resume phrasing.

---

## What's wired vs. what's documented

Honest status, because this matters:

- ✅ **Verified:** the tools are installed (PyCharm/CLion/DataGrip 2026.2.x, Docker Desktop); the protocols are supported by those versions; the exact commands and settings paths are confirmed against official docs.
- 🟡 **Documented, not yet executed:** the actual IDE↔agent connection (registering `hermes acp` in the JetBrains agent picker, adding the IDE's MCP server to Hermes' config). The steps are written down; they just haven't been run live yet.
- ⚠️ **One manual check:** confirm PyCharm is the Pro edition (Community lacks the IDE-as-MCP-server plugin) via `Help ▸ About`, and run `hermes acp --check` to confirm the ACP extra is installed.

---

## Where to look next

- `docs/device-inventory.md` — what's actually installed, with paths
- `docs/integration-map.md` — the precise how-to (settings paths, commands, config)
- `docs/tool-reference.md` — the resume / interview version, with a one-liner bullet

*Local-first. Open protocols. You hold the keys.*
