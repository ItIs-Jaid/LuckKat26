# Integration Map — agentic DevSecLocHostOps

> How Layer 1 (Hermes) ⇄ Layer 2b (JetBrains IDEs) ⇄ Layer 2c (Google agent) actually connect.
> Every claim below is tagged `[verified]` (from device/registry), `[official]` (JetBrains/Hermes docs, sourced), or `[TBD]` (pending research layer).
> Research layers: JetBrains ✅ · Hermes ACP/MCP ⏳ · Google agent ⏳

---

## Layer 2b — JetBrains IDEs (verified + official)

All three installed IDEs are **2026.2.x** (PyCharm 2026.2 / build 262.8665.309, CLion 2026.2.1, DataGrip 2026.2.4) — all ≥ 2025.3.2, so they support **all three** connection mechanisms below. [verified]

JetBrains exposes **two complementary MCP surfaces** plus an ACP host. This is the backbone of the whole stack:

### (A) IDE as MCP **Server** — Hermes drives the IDE
- Bundled plugin **"MCP Server" (id 26071)**, enabled by default since **2025.2** in all IntelliJ-based IDEs. [official]
- **Enable:** `Settings | Tools | MCP Server` → toggle **Enable MCP Server**.
- Exposes ~29 tools (2026.1): `get_file_problems`, `build_project`, `analyze_calls`, `get_symbol_info`, `rename_refactoring`, `execute_run_configuration`, `execute_terminal_command`, `open_file_in_editor`, `create_new_file`, `replace_text_in_file`, plus 9 DB tools (`execute_sql_query`, `list_database_schemas`, …). [official]
- "**Brave mode**" (`Run shell commands or run configurations without confirmation`) lets an external agent run commands unprompted — trust-gated, **off by default**. [official]
- Requires the IDE to be **running** (not standalone). [official]
- **Use here:** Hermes (Layer 1) connects as an MCP client to PyCharm/CLion/DataGrip and can open files, run build/terminal, read inspections — i.e. agentic control of the local dev surface.

### (B) IDE as MCP **Client** — IDE pulls in external tools
- Native MCP client lives in the **AI Assistant plugin** (since **IntelliJ/PyCharm 2025.1**). [official]
- **Add a server:** `Settings | Tools | AI Assistant | Model Context Protocol (MCP)` → **Add** → "As JSON" → paste `mcpServers` snippet (stdio `command`/`args`, or `url` for remote; remote added 2025.3 / AI Assistant 2026.1). [official]
- Tools are invoked from AI Assistant Chat in **Codebase / edit mode** via `/` slash commands. [official]
- **Use here:** point the IDE at a Hermes-exposed MCP server or the Google agent's MCP endpoint so the in-IDE assistant can call them.

### (C) ACP host — IDE runs external agents
- **ACP** = "LSP for agents" (JSON-RPC 2.0 over stdio; co-created by **Zed + JetBrains**; ACP Registry launched Jan 2026). [official]
- Native support requires **IDE ≥ 2025.3.2 + AI Assistant plugin ≥ 253.30387.147** (no JetBrains AI subscription needed; agent provider handles its own auth). [official]
- **Add an agent:** `Settings | Tools | AI Assistant | Agents` → pick from ACP Registry (Claude Agent, Codex, **Gemini CLI**, Cursor, …) or **Add Custom Agent** → `~/.jetbrains/acp.json`. [official]
- **Use here:** register Hermes (or the Google agent) as a custom ACP agent so it appears in the IDE's agent picker. ACP = editor↔agent; MCP = agent↔tools. [official]

### (D) Junie — JetBrains' own autonomous agent (context only)
- GA **April 16, 2025**; in-IDE + standalone CLI; modes **Ask** / **Code**. Listed as a bundled ACP agent. Also consumes MCP via `.junie/mcp/mcp.json` (project) or `~/.junie/mcp/mcp.json` (user). [official]
- Not the orchestrator here, but can coexist alongside Hermes/Google agents.

### Capability matrix (what's actually wireable on this device)

| Mechanism | Path | PyCharm 2026.2 | CLion 2026.2.1 | DataGrip 2026.2.4 |
|---|---|---|---|---|
| MCP client (AI Assistant) | `Tools ▸ AI Assistant ▸ MCP` | ✅ (Pro) | ✅ | ✅ |
| IDE as MCP server (id 26071) | `Tools ▸ MCP Server` | ✅ (Pro) | ✅ | ✅ |
| ACP host | `Tools ▸ AI Assistant ▸ Agents` | ✅ (≥2025.3.2) | ✅ | ✅ |

---

## Layer 1 — Hermes Agent (verified from live docs)

Hermes (Nous Research) is the orchestrator. It speaks **both** sides of the integration: it can run **as an ACP server** (so the IDE drives it) and as an **MCP client/server** (so it consumes/exposes tools). [official: hermes-agent docs]

### (A) Hermes as an ACP server → registers in JetBrains' agent picker
- **Prereq (one-time):** the ACP extra is optional. Install it from the Hermes checkout:
  `cd ~/.hermes/hermes-agent && uv pip install -e '.[acp]'`
  This enables the `hermes acp` command. Verify with `hermes acp --check`.
- **Run Hermes in ACP mode** (any of these — stdout is reserved for ACP JSON-RPC; logs go to stderr):
  ```
  hermes acp
  hermes-acp
  python -m acp_adapter
  ```
- ACP exposes a curated `hermes-acp` toolset tuned for editors: `read_file`, `write_file`, `patch`, `search_files`, `terminal`, `process`, `web/browser`, `memory`, `todo`, `session search`, `skills`, `execute_code`, `delegate_task`, `vision`. (Messaging + cron excluded — not editor-UX fit.)
- **Register in JetBrains** (your IDEs are ≥ 2025.3.2, so ACP host is available): `Settings | Tools | AI Assistant | Agents` → **Add Custom Agent** → point its JSON (`~/.jetbrains/acp.json`) at:
  ```json
  { "hermes-agent": { "command": "hermes", "args": ["acp"] } }
  ```
  (Same shape VS Code and Zed use; JetBrains reads the same custom-agent JSON.) Hermes then appears in the IDE's agent picker, keeping its own identity, memory, skills, and provider setup while the IDE owns the conversation transport.

### (B) Hermes as MCP client → consumes the JetBrains MCP Server (L2b)
- Add a server to `~/.hermes/config.yaml`:
  ```yaml
  mcp_servers:
    clion:
      command: "..."   # JetBrains MCP server stdio command (see L2b Enable MCP Server)
    pycharm:
      url: "..."       # or remote URL once IDE exposes HTTP
  ```
- Or use the curated catalog (disabled by default; install only what you want):
  `hermes mcp` (interactive) · `hermes mcp catalog` · `hermes mcp install <name>`
- Per-server tool filtering via `tools.include` so Hermes only sees the tools you want.

### (C) Hermes as MCP server → external agents/IDE drive Hermes
- `hermes mcp serve` (stdio-only today) exposes conversation/session tools: `messages_read`, `events_poll`, `events_wait`, `permissions_list_open`, `permissions_respond`, `messages_send`. An external agent or the IDE could call these to push tasks into Hermes.

### (D) A2A (agent↔agent) — Hermes ↔ other agents
- Hermes ships an A2A (Agent-to-Agent) capability (`/user-guide/messaging/a2a`). This is the agent↔agent layer — complements MCP (agent→tools). Relevant if Layer 2c ever becomes a real ADK agent. [official]

> **Verification step for the operator (manual, needs consent):** run `hermes acp --check` to confirm the ACP extra is installed on your machine before relying on the ACP path above. The rest of the wiring is documented from official docs and not yet executed against a live IDE connection.
>
> **Note (verified, both direct + subagent research):** there is **no `--mode rpc` flag**. The three ways to drive Hermes from outside are: (1) **ACP** (`hermes acp`) for editor/agent hosts, (2) the **TUI-gateway JSON-RPC**, and (3) the **OpenAI-compatible HTTP API server** (`hermes ... api-server`). ACP is the right one for JetBrains.

## Layer 2c — Google "Spark agent" → **MANUAL COMPANION (not wired)**

**Decision (2026-08-29):** The operator confirmed this is the **consumer Gemini Spark** (inside the Gemini app, $100/mo Ultra, US-only). It has **no developer API**, so it is kept as a *manual* companion tool — **not programmatically integrated** into the agentic stack. This also preserves the **local-first, cloud-deferred** posture.

- Gemini Spark remains a human-in-the-loop sidekick (research, drafting, queries) — the operator drives it directly in the Gemini app.
- No MCP server, no A2A endpoint, no ACP registration for it. The agentic layers (L1 Hermes, L2a subagents, L2b IDEs) do **not** call it.
- *If this ever changes* (e.g. Google ships a Spark developer API, or you stand up a Google ADK agent), the integration paths below are pre-researched and ready — but they are **out of scope for the current build**:
  - **MCP:** expose a Google ADK agent as an MCP server → consumed by Hermes (L1) + JetBrains (`Settings ▸ Tools ▸ AI Assistant ▸ MCP`).
  - **A2A:** expose an A2A server (Agent Card at `/.well-known/agent-card.json`); Hermes as A2A client/server.
  - **REST / function-calling:** direct Gemini API / Vertex AI.
  - A2A v1.0 stable Apr 9 2026, Linux Foundation, 150+ orgs — complements MCP (agent→agent vs agent→tools).

---

## Connection summary (as it stands)

```
Hermes (L1) ──MCP client──▶ JetBrains MCP Server (L2b)      [ready to wire]
Hermes (L1) ──ACP server───▶ JetBrains Agents picker (L2b)  [ready to wire]
Hermes (L1) ──MCP server────▶ external agents / IDE         [hermes mcp serve]
Hermes (L1) ──A2A───────────▶ other agents (incl. future L2c) [capability documented]
IDE (L2b) ───MCP client────▶ Hermes MCP server / Google     [pending L2c]
Google (L2c) ─MANUAL────────▶ the operator in Gemini app (not wired) [decision 2026-08-29]
```
