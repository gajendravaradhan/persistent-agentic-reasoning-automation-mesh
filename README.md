# PARAM — Persistent Agentic Reasoning Automation Mesh

Autonomous orchestration layer fusing Oh-My-OpenCode and Hermes Agent.

**PARAM** = **P**ersistent **A**gentic **R**easoning **A**utomation **M**esh

---

## Architecture

```
                         ┌─────────────────────────┐
                         │      WhatsApp / API      │
                         │   (2-way message bridge)  │
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

PARAM sits between messaging surfaces and agent runtimes, routing requests through a self-evolving memory layer and a proactive cron scheduler. Both Oh-My-OpenCode and Hermes Agent expose their full MCP tool surfaces to the mesh.

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/your-org/param.git
cd param

# Install dependencies
bun install                     # or: npm install

# Configure your environment
cp .env.example .env
# Edit .env with your WhatsApp credentials, Hermes endpoint, and OpenCode config

# Launch PARAM
bun run src/index.ts
```

PARAM requires a running Hermes Agent instance and an Oh-My-OpenCode session. See [specs/](specs/) for detailed setup guides.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **2-way WhatsApp bridge** | Send and receive messages via WhatsApp. PARAM can be triggered by text, respond in threads, and push proactive notifications. |
| **Self-evolving memory** | Interactions are indexed and stored. The memory engine surfaces relevant context from past exchanges automatically. |
| **Proactive cron** | Scheduled tasks fire on configurable intervals. PARAM checks conditions, runs actions, and reports results without being asked. |
| **Full MCP tool surface** | All Model Context Protocol tools from both Oh-My-OpenCode and Hermes Agent are available through a unified router. |
| **Multi-agent routing** | Requests are dispatched to the appropriate agent based on intent classification. |

---

## Requirements

- **Runtime**: [Bun](https://bun.sh) (>= 1.0) or Node.js (>= 20)
- **Python**: 3.11+ (for Hermes Agent integration)
- **Hermes Agent**: running instance with MCP server enabled
- **Oh-My-OpenCode**: configured with your API keys and MCP tools
- **OS**: macOS (primary target; Linux works with minor adjustments)

---

## Project Structure

```
param/
├── README.md
├── .gitignore
├── .env.example
├── package.json
├── bun.lockb
├── src/
│   ├── index.ts              # Entry point
│   ├── core/
│   │   ├── memory.ts         # Memory engine
│   │   ├── scheduler.ts      # Cron / proactive triggers
│   │   └── router.ts         # Intent-based agent routing
│   ├── bridges/
│   │   ├── whatsapp.ts       # WhatsApp message bridge
│   │   └── api.ts            # HTTP API surface
│   ├── agents/
│   │   ├── opencode.ts       # Oh-My-OpenCode integration
│   │   └── hermes.ts         # Hermes Agent integration
│   └── mcp/
│       └── unified.ts        # Unified MCP tool surface
├── commands/
│   ├── exit-param.md         # /exit-param slash command
│   └── ...                   # Additional slash commands
├── configs/
│   └── default.json          # Default configuration
├── specs/
│   ├── architecture.md       # Architecture deep dive
│   ├── memory-engine.md      # Self-evolving memory design
│   ├── scheduler.md          # Cron scheduler spec
│   ├── whatsapp-bridge.md    # WhatsApp integration docs
│   └── mcp-surface.md        # MCP tool surface specification
├── scripts/
│   ├── setup.sh              # Environment setup script
│   └── dev.sh                # Development launcher
└── tests/
    ├── unit/
    └── integration/
```

---

## Documentation

Detailed specifications live in the [specs/](specs/) directory:

- [Architecture](specs/architecture.md) — system design, data flow, component interactions
- [Memory Engine](specs/memory-engine.md) — vector indexing, context retrieval, evolution loop
- [Scheduler](specs/scheduler.md) — cron syntax, task definitions, proactive triggers
- [WhatsApp Bridge](specs/whatsapp-bridge.md) — message format, session management, retry logic
- [MCP Surface](specs/mcp-surface.md) — unified tool catalog, routing rules, auth model

---

## License

MIT — see [LICENSE](LICENSE) for details.
