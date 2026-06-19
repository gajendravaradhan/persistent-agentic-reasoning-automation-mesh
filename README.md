# PARAM — Persistent Agentic Reasoning Automation Mesh

Autonomous orchestration layer fusing Oh-My-OpenCode and Hermes Agent.

**PARAM** = **P**ersistent **A**gentic **R**easoning **A**utomation **M**esh

---

## Architecture

```
                      Telegram User
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│  Cloudflare Tunnel (*.aiforges.app)                 │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  UGREEN NAS (Docker, 24/7 always-on)               │
│  ┌─────────────────────────────────────────────┐   │
│  │ Hermes Gateway: Telegram, cron, memory,     │   │
│  │ kanban, skills                              │   │
│  ├─────────────────────────────────────────────┤   │
│  │ TokenEye: load-balanced LLM proxy + metrics │   │
│  └─────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  MacBook (worker node)                              │
│  ┌─────────────────────────────────────────────┐   │
│  │ OpenCode + OMO Agents (10 agents, 8 cats)   │   │
│  │ team_mode: 4 parallel, 8 max                │   │
│  ├─────────────────────────────────────────────┤   │
│  │ PARAM MCP Bridge: OMO ↔ Hermes tools        │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

PARAM runs 24/7 on NAS (Docker). Telegram messages handled instantly regardless of MacBook state. Complex code tasks delegated to OMO agents when MacBook is active.

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/gajendravaradhan/persistent-agentic-reasoning-automation-mesh.git
cd persistent-agentic-reasoning-automation-mesh

# Option A: Local Hermes (MacBook only, needs active session)
cp configs/hermes-env.tmpl ~/.hermes/.env
chmod 600 ~/.hermes/.env
./scripts/param-status.sh

# Option B: NAS 24/7 deployment (recommended)
cd deploy/nas
./deploy.sh prepare
# Edit hermes-data/.env with TELEGRAM_BOT_TOKEN and provider keys
HERMES_UID=$(id -u) HERMES_GID=$(id -g) ./deploy.sh start
./cloudflared-setup.sh  # For remote access via *.aiforges.app
```

PARAM requires a running Hermes Agent instance (local or NAS) and an Oh-My-OpenCode session for complex code work. For 24/7 Telegram availability, deploy to NAS. See [specs/ROADMAP.md](specs/ROADMAP.md) for the full implementation plan.

---

## Key Features

| Feature | Status | Description |
|---------|--------|-------------|
| **2-way Telegram bridge** | ✅ Working | 24/7 Telegram bot via Hermes gateway long-polling. Proven: messages received, processed, responded. |
| **TokenEye proxy** | ✅ Working | Load-balanced LLM proxy with 2 opencode-go accounts. Pass-through for Claude Pro + ChatGPT Plus. 197+ requests tracked. |
| **MCP bridge** | ✅ Working | 111-line Python bridge exposing 64 Hermes tools to OMO via `hermes__` prefix. |
| **OMO agent pool** | ✅ Working | 10 specialized agents + 8 categories. team_mode: 4 parallel, 8 max. Model + fallback chains per agent. |
| **Cron automation** | ✅ Working | 5 active cron jobs. Telegram-delivered results. |
| **3-layer memory** | 🔧 Planned | Honcho (dialectic) + Hindsight/pgvector (semantic) + Obsidian (human). Phase 1. |
| **Self-evolving skills** | 🔧 Planned | Automated skill creation from task outcomes, failure-driven improvement. Phase 2. |
| **NAS 24/7 deployment** | 🔧 Planned | Docker Compose on UGREEN NAS with Cloudflare tunnel. Phase 0. |
| **Multi-channel gateway** | 🔧 Planned | Discord, Email, Webhook beyond Telegram. Phase 5. |

See [specs/ASSESSMENT.md](specs/ASSESSMENT.md) for the honest gap analysis and [specs/ROADMAP.md](specs/ROADMAP.md) for the 82-task implementation plan.

---

## Requirements

- **Hermes Agent**: running instance (local or NAS Docker)
- **Oh-My-OpenCode**: configured OpenCode session with OMO plugin
- **Telegram Bot**: token from @BotFather for the primary chat surface
- **For 24/7**: UGREEN NAS (or any Docker host) + Cloudflare domain for tunnel
- **Python**: 3.11+ (for MCP bridge)

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

- [Assessment](specs/ASSESSMENT.md) — honest gap analysis of current vs planned capabilities
- [Roadmap](specs/ROADMAP.md) — 82-task implementation plan across 10 phases
- [Architecture](specs/ARCHITECTURE.md) — system design, data flow, component interactions
- [Reddit Analysis](specs/REDDIT-ANALYSIS.md) — patterns from production Hermes setups
- [Extensions](specs/EXTENSIONS.md) — MCP and future integration model
- [Troubleshooting](specs/TROUBLESHOOTING.md) — operational checks and fixes

---

## License

MIT — see [LICENSE](LICENSE) for details.
