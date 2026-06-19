# PARAM — Persistent Agentic Reasoning Automation Mesh

Autonomous orchestration layer fusing Oh-My-OpenCode and Hermes Agent.

**PARAM** = **P**ersistent **A**gentic **R**easoning **A**utomation **M**esh

---

## Architecture

```
                         ┌─────────────────────────┐
                         │     Telegram / API      │
                         │   (2-way agent surface) │
                         └───────────┬─────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │     PARAM Core       │
                          │  ┌────────────────┐  │
                          │  │ Scheduler/Cron │  │
                          │  ├────────────────┤  │
                          │  │ Memory Engine  │  │
                          │  ├────────────────┤  │
                          │  │ Router & Auth  │  │
                          │  └────────────────┘  │
                          └──┬───────────────┬───┘
                             │               │
              ┌──────────────▼──┐   ┌────────▼──────────┐
              │ Oh-My-OpenCode  │   │   Hermes Agent    │
              │ (full MCP tools)│   │ (conversation/DM) │
              └─────────────────┘   └───────────────────┘
```

PARAM sits between user-facing chat/API surfaces and agent runtimes, routing requests through a self-evolving memory layer and a proactive cron scheduler. Both Oh-My-OpenCode and Hermes Agent expose their full MCP tool surfaces to the mesh.

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/gajendravaradhan/persistent-agentic-reasoning-automation-mesh.git
cd persistent-agentic-reasoning-automation-mesh

# Configure Hermes/PARAM
cp configs/hermes-env.tmpl ~/.hermes/.env
chmod 600 ~/.hermes/.env
# Add TELEGRAM_BOT_TOKEN from @BotFather and TELEGRAM_ALLOWED_USERS.
# Provider routing is in configs/hermes-config.yaml.tmpl; default routes via TokenEye/OpenCode Go.

# Check status
./scripts/param-status.sh
```

PARAM requires a running Hermes Agent instance and an Oh-My-OpenCode session. See [specs/](specs/) for detailed setup guides.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **2-way Telegram bridge** | Send and receive messages through a dedicated Telegram bot. PARAM can be triggered by DM, respond directly, and push proactive notifications. |
| **Generic provider routing** | Configure any Hermes provider or OpenAI-compatible proxy in `model.*`. Default template routes through TokenEye/OpenCode Go so token usage is sniffed and recorded. |
| **Self-evolving memory** | Interactions are indexed and stored. The memory engine surfaces relevant context from past exchanges automatically. |
| **Proactive cron** | Scheduled tasks fire on configurable intervals. PARAM checks conditions, runs actions, and reports results without being asked. |
| **Full MCP tool surface** | All Model Context Protocol tools from both Oh-My-OpenCode and Hermes Agent are available through a unified router. |
| **Multi-agent routing** | Requests are dispatched to the appropriate agent based on intent classification. |

---

## Requirements

- **Python**: 3.11+ for Hermes Agent integration
- **Hermes Agent**: running instance with MCP server enabled
- **Oh-My-OpenCode**: configured with your API keys and MCP tools
- **Telegram Bot**: token from @BotFather for the primary chat surface
- **OS**: macOS primary; Linux supported for unattended runtime

---

## Project Structure

```
persistent-agentic-reasoning-automation-mesh/
├── AGENTS.md                  # PARAM session behavior
├── SOUL.md                    # PARAM/Jarvis persona
├── param_hermes_mcp.py        # Hermes MCP bridge
├── commands/                  # Slash commands
├── configs/                   # Environment/config templates
├── scripts/                   # Setup and status checks
├── specs/                     # Architecture and operations docs
└── tests/                     # MCP bridge tests
```

---

## Documentation

Detailed specifications live in the [specs/](specs/) directory:

- [Assessment](specs/ASSESSMENT.md) — honest gap analysis of current vs planned capabilities
- [Roadmap](specs/ROADMAP.md) — implementation plan with 99-task checklist across 12 phases
- [Architecture](specs/ARCHITECTURE.md) — system design, data flow, component interactions
- [Extensions](specs/EXTENSIONS.md) — MCP and future integration model
- [Troubleshooting](specs/TROUBLESHOOTING.md) — operational checks and fixes

---

## License

MIT — see [LICENSE](LICENSE) for details.
