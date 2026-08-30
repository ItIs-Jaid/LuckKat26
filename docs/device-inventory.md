# Device Inventory — JetBrains Tooling (local-first)

> Source of truth for the `agentic DevSecLocHostOps` stack.
> Captured: 2026-08-29 (US MST) on the operator's Windows 11 host (Dell 16, 32GB / Ultra 7, Arc 140V).

## Installed JetBrains products

| Product | Version | Role in stack | Install path |
|---|---|---|---|
| PyCharm | 2026.2 | Python dev — agents, automation, tooling | `C:\Program Files\JetBrains\PyCharm 2026.2` |
| CLion | 2026.2.1 | C/C++ systems dev — native + embedded | `C:\Program Files\JetBrains\CLion 2026.2.1` |
| DataGrip | 2026.2.4 | DB / data-ops — local + remote datasources | `C:\Program Files\JetBrains\DataGrip 2026.2.4` |

## Supporting tooling (non-JetBrains)

| Tool | Version | Role in stack | Install path |
|---|---|---|---|
| Docker Desktop | installed (not running at capture) | Host/Ops — containerized services, local infra | `C:\Program Files\Docker\Docker\Docker Desktop.exe` |

> Docker fills the **Host/Ops** pillar: containerized local services (databases, agents, build runners) without cloud dependency.

## Curated launcher folder

The operator keeps the working set of tool shortcuts in a folder sharing the project name:

```
C:\Users\<user>\OneDrive\Desktop\DevSecLocHostOps\
├── CLion 2026.2.1.lnk
├── DataGrip 2026.2.4.lnk
├── PyCharm 2026.2.lnk
├── Docker Desktop.lnk
└── desktop.ini
```

All four `.lnk` files resolve to the 64-bit executables listed above. This is the project "tool dock" — the on-disk entry point to the local-first stack. (The documentation repo lives separately at `C:\Users\<user>\agentic-DevSecLocHostOps\`.)

Notes:
- Installed **standalone** — no JetBrains Toolbox (per-app launchers, fully offline-capable).
- CLion was mid-first-launch at capture time (two `CLion-2026.2.1.exe` processes live) — suite was being completed.
- Registry: `HKLM\Software\JetBrains\{DataGrip,PyCharm}` present; `HKCU\Software\JetBrains` not yet written (no project opened yet).
- `AppData\Local\JetBrains\Daemon` present (shared IntelliJ platform daemon).
- **Edition caveat (PyCharm):** the install ships both `pycharm.community.jar` and `pycharm.pro.jar` on the classpath (normal even for Pro), so the edition cannot be read from disk alone. The **IDE-as-MCP-Server** plugin targets paid editions; if `Settings | Tools | MCP Server` is present, it is Pro. Verify once via **Help ▸ About** (shows "PyCharm Professional" or "Community"). CLion and DataGrip have no Community edition, so they qualify.

## Why this toolset maps to "DevSecLocHostOps"

- **Dev** — PyCharm (scripting/automation) + CLion (native/systems).
- **Sec** — local-first, no-cloud posture; secrets in `.env`/OS vault, not IDE cloud.
- **Loc / Host** — all run fully local on the Windows 11 host (Dell 16, 32GB, Ultra 7, Arc 140V); Docker Desktop adds containerized local infra.
- **Ops** — DataGrip for data pipelines + Docker for containerized services + the agent layer drives the IDEs headlessly.

## Change log

| Date | Change |
|---|---|
| 2026-08-29 | Initial capture: PyCharm 2026.2, CLion 2026.2.1, DataGrip 2026.2.4 |
