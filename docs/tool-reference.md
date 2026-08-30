# Tool Reference — agentic DevSecLocHostOps

> Interview- and resume-ready inventory of the local-first agentic dev/security/ops toolchain.
> Verified on-device 2026-08-29. Each entry: what it is, the role it plays in the stack, and how to speak about it.
> Companion docs: `device-inventory.md` (verified installs) · `integration-map.md` (how layers connect).

---

## 1. JetBrains IDE suite (primary dev surface)

### PyCharm 2026.2 — Python development
- **What:** JetBrains Python IDE (full 2026.2 line, build 262.8665.309).
- **Role:** Python automation, agent tooling, scripting for the agentic workflows.
- **Agent integration (2026.2 ≥ 2025.3.2):** native MCP client (AI Assistant), IDE-as-MCP-server, and ACP host — all available. (Edition: confirm Pro vs Community via Help ▸ About; MCP-Server plugin ships on paid editions.)
- **Interview phrasing:** *"Primary Python environment; I connect it to my local AI agent stack over MCP so the agent can open files, run the terminal, and read inspections."*

### CLion 2026.2.1 — C/C++ systems development
- **What:** JetBrains C/C++ IDE (no Community edition — qualifies for all agent features).
- **Role:** Native / systems-level work, embedded, performance-critical code.
- **Agent integration:** same MCP client + IDE-as-MCP-server + ACP host as PyCharm.
- **Interview phrasing:** *"For native code, CLion is the surface my agent drives the same way — one MCP connection pattern across the whole suite."*

### DataGrip 2026.2.4 — Database / data operations
- **What:** JetBrains standalone DB IDE (no Community edition).
- **Role:** Local + remote datasource management, query/data pipelines for Ops.
- **Agent integration:** 2026.1 added 9 DB tools to the IDE's MCP server surface (`execute_sql_query`, `list_database_schemas`, …), so the agent can run queries and introspect schemas.
- **Interview phrasing:** *"DataGrip exposes its DB tooling to the agent over MCP — the agent can execute SQL and read schemas as part of automated ops."*

## 2. Docker Desktop — Host / Ops runtime
- **What:** Container platform (installed at `C:\Program Files\Docker\Docker\Docker Desktop.exe`; not running at capture — start on demand).
- **Role:** Containerized **local** services (databases, build runners, agent sidecars) with no cloud dependency — fills the Host/Ops pillar.
- **Interview phrasing:** *"I keep local infra in Docker containers so the whole stack stays on-host and reproducible — no cloud lock-in for the runtime layer."*

## 3. Curated launcher folder ("tool dock")
```
C:\Users\<user>\OneDrive\Desktop\DevSecLocHostOps\
├── CLion 2026.2.1.lnk
├── DataGrip 2026.2.4.lnk
├── PyCharm 2026.2.lnk
└── Docker Desktop.lnk
```
- All shortcuts resolve to the 64-bit executables above. This is the on-disk entry point to the stack.

## 4. Agent / orchestration layer (summary — see `integration-map.md` for wiring)
- **Hermes Agent** (Nous Research) — orchestrator; skills, memory, subagent fan-out, MCP client/server. *(Connection specifics pending live research.)*
- **Hermes subagent fan-out** — research / solutions / vetting agents dispatched in parallel.
- **Gemini Spark** (Google) — **manual companion only**, not programmatically wired (consumer product, no developer API; preserves local-first posture).

## The one-liner (resume bullet)
> **Local-first "agentic DevSecLocHostOps" stack:** JetBrains IDE suite (PyCharm / CLion / DataGrip 2026.2.x) + Docker Desktop, wired to a personal AI agent (Hermes) via the Model Context Protocol and ACP so the agent drives the IDEs headlessly — all on-host, no cloud dependency.

## Caveats (don't overclaim in interviews)
- PyCharm edition (Pro vs Community) not yet confirmed from disk — verify via Help ▸ About before stating MCP-server capability for PyCharm specifically.
- Cloud/OAuth deferred per standing posture; Gemini Spark is manual-only.
- Agent↔IDE wiring is documented design, not yet executed (IDE not yet opened with the agent connected).
