# PARAM — Persistent Agentic Reasoning Automation Mesh

**Callsign Jarvis.** A unified reasoning mesh weaving OhMyOpenCode's agent framework and Hermes's personal automation layer through a bidirectional MCP bridge. Not a collection of tools. A single identity that routes intent to the best available subsystem, absorbs new integrations without drift, and maintains persistent context across sessions, channels, and time.

---

## What PARAM Is (and Isn't)

PARAM is the marriage of two systems: **OhMyOpenCode** (OMO) provides a structured agent runtime with 10 specialized agents, team-mode parallel execution, and a full LSP/static-analysis tool surface. **Hermes** provides persistent-world connectivity: Telegram messaging, cron scheduling, kanban task management, a memory engine, and a skill system. A 93-line Python MCP bridge (`param_hermes_mcp.py`) connects them, exposing all 64 Hermes tools to OMO under the `hermes__` prefix.

PARAM is **not** a stand-alone daemon. It is a configuration layer, an identity system, and an integration bridge that makes OMO + Hermes greater than the sum of their parts. It runs wherever Hermes runs (NAS 24/7 in Docker, or a MacBook session) and extends through OMO's OpenCode sessions.

The project lives at [github.com/gajendravaradhan/persistent-agentic-reasoning-automation-mesh](https://github.com/gajendravaradhan/persistent-agentic-reasoning-automation-mesh).

---

## Architecture

```
                         Telegram User
                              |
                              v
   +--------------------------------------------------+
   |  Cloudflare Tunnel (*.aiforges.app)               |
   +-------------------------+------------------------+
                             |
   +-------------------------v------------------------+
   |  UGREEN NAS (Docker, 24/7 always-on)              |
   |                                                    |
   |  Hermes Gateway + TokenEye + Honcho Memory         |
   |  Langfuse Observability + Intent Router            |
   |  15 Docker containers on nas_param-net bridge      |
   +-------------------------+------------------------+
                             |
                    SSH health probe
                             |
   +-------------------------v------------------------+
   |  MacBook (worker node, on-demand)                  |
   |                                                    |
   |  OpenCode + OMO Agent Pool (10 agents, 8 cats)     |
   |  Team Mode: 4 parallel, 8 max                     |
   |  PARAM MCP Bridge: OMO <-> Hermes tools           |
   +--------------------------------------------------+
```

The NAS tier runs 24/7 regardless of MacBook state. It handles all messaging, memory, cron, observability, and intent routing. When the MacBook is online (detected by SSH health probe), OMO agents pick up kanban tasks for heavy code work. When offline, PARAM falls back to direct LLM calls through Hermes and TokenEye.

---

## What Works Today

| Component | Status | Detail |
|-----------|--------|--------|
| **MCP Bridge** | Production | 93-line Python server. Discovers all Hermes tools, wraps with `hermes__` prefix, dispatches calls. Tested with 59 unit/integration tests. |
| **Identity System** | Production | SOUL.md (392 lines, persona) + AGENTS.md (184 lines, operational protocol). Dual-file design: personality and mechanics evolve independently. |
| **Telegram Bridge** | Production | Two-way messaging through Hermes gateway. 24/7 on NAS via long-polling. Tested with latency measurement script. |
| **Intent Router** | Production | `src/router/` with rule-based classifier (10 intent types, 2+ patterns each), confidence scoring, guard layer, and audit logging. |
| **TokenEye Proxy** | Production | Load-balanced LLM proxy across two opencode-go accounts. 197+ requests tracked. |
| **Cron Automation** | Production | 13 autonomous cron jobs running on NAS. Telegram-delivered results. Covers health checks, kanban flow, worker detection, notifications. |
| **OMO Agent Pool** | Production | 10 specialized agents + 8 categories with model/fallback chains. Team mode for parallel execution. |
| **Test Suite** | Production | 59 tests across 5+ test files. Line coverage target: 90%. Branch coverage target: 70%. Mutation testing configured via mutmut. |
| **NAS Deployment** | Production | Docker Compose with 15 containers on bridge network. Cloudflare tunnel. .env validator. Health checks. |
| **Observability** | Production | Langfuse tracing via Hermes native plugin. Cloud Hobby tier. |
| **Three-Layer Memory** | Phase 1 | Honcho (dialectic reasoning) deployed. Hindsight/pgvector (semantic) and Obsidian vault (human-readable) planned. |
| **Verification System** | Production | `scripts/verify-roadmap.py` programmatically checks roadmap completion against NAS state. No manual checkboxes. |

---

## Quick Start

### Prerequisites

- **Hermes Agent**: running instance (local or NAS Docker)
- **OhMyOpenCode**: configured OpenCode session with OMO plugin
- **Telegram Bot**: token from @BotFather
- **For 24/7 deployment**: a Docker host (UGREEN NAS or equivalent) + Cloudflare domain for tunnel
- **Python**: 3.11+ (for MCP bridge and test suite)

### Local Setup (MacBook)

```bash
git clone https://github.com/gajendravaradhan/persistent-agentic-reasoning-automation-mesh.git
cd persistent-agentic-reasoning-automation-mesh

# Create and activate virtual environment
python3 -m venv .venv && source .venv/bin/activate

# Configure Hermes environment
cp configs/hermes-env.tmpl ~/.hermes/.env
chmod 600 ~/.hermes/.env
# Edit ~/.hermes/.env with your TELEGRAM_BOT_TOKEN and provider keys

# Run status check
./scripts/param-status.sh

# Run tests
python -m pytest tests/ -v
```

### NAS 24/7 Deployment (Recommended)

```bash
cd deploy/nas

# Stage 1: Prepare environment
./deploy.sh prepare

# Stage 2: Configure secrets
# Edit hermes-data/.env with TELEGRAM_BOT_TOKEN and provider keys

# Stage 3: Validate before starting
./validate-env.sh

# Stage 4: Start the stack
HERMES_UID=$(id -u) HERMES_GID=$(id -g) ./deploy.sh start

# Stage 5: Set up Cloudflare tunnel for remote access
./cloudflared-setup.sh
```

---

## Project Structure

```
persistent-agentic-reasoning-automation-mesh/
├── AGENTS.md                    # Operational protocol, gates, tool awareness
├── SOUL.md                      # Persona definition: voice, imperatives, playbook
├── README.md                    # This file
├── param_hermes_mcp.py          # MCP bridge server (93 lines)
├── pyproject.toml               # Pytest, coverage, and mutmut configuration
├── .gitignore                   # Secrets, caches, state files
├── commands/                    # Slash command definitions
│   └── exit-param.md            # Graceful shutdown protocol
├── configs/                     # Environment and configuration templates
│   ├── hermes-env.tmpl          # Required environment variables
│   ├── hermes-config.yaml.tmpl  # Hermes configuration template
│   ├── mcp.json.tmpl            # MCP server registration
│   ├── cron-jobs.yaml           # Cron job definitions
│   └── skill-whitelist.yaml     # Skill enablement list
├── src/router/                  # Intent router (rule-based + guard layer)
│   ├── classifier.py            # 10 intent types, confidence scoring
│   ├── guard.py                 # Safety and policy checks
│   ├── routes.py                # Intent-to-subsystem mapping
│   ├── types.py                 # Intent enum and data types
│   └── audit.py                 # Audit logging for routing decisions
├── scripts/                     # Operational scripts
│   ├── param-status.sh          # Health check dashboard
│   ├── param-setup.sh           # First-run setup
│   ├── verify-roadmap.py        # Programmatic roadmap verification
│   ├── test-telegram-latency.sh # Telegram bridge latency test
│   ├── skill-tracker.py         # Skill usage tracking
│   └── purge-secrets.sh         # Secrets cleanup utility
├── tests/                       # Test suite
│   ├── conftest.py              # Shared fixtures and mock setup
│   ├── test_mcp_bridge.py       # MCP bridge unit tests (schema, dispatch)
│   ├── test_mcp_server.py       # MCP server integration tests
│   ├── test_mcp_integration.py  # End-to-end MCP tool lifecycle
│   ├── test_config.py           # Configuration validation
│   ├── test_memory_provider.py  # Memory provider tests
│   └── test_router/             # Intent router tests
├── deploy/nas/                  # NAS deployment
│   ├── docker-compose.yml       # 15-container stack definition
│   ├── deploy.sh                # Staged deployment script
│   ├── validate-env.sh          # Environment validation
│   ├── cloudflared-setup.sh     # Tunnel setup
│   ├── configs/                 # Container-specific configs
│   ├── patches/                 # Migration patches
│   ├── scripts/                 # NAS runtime scripts
│   └── hermes-data/             # Mounted data directory
├── specs/                       # Architecture and planning documents
│   ├── ARCHITECTURE.md          # Comprehensive architecture reference
│   ├── ASSESSMENT.md            # Honest gap analysis (MVP vs. vision)
│   ├── ROADMAP.md               # 82-task implementation plan, 10 phases
│   ├── EXTENSIONS.md            # MCP integration and extension guide
│   ├── TROUBLESHOOTING.md       # Operational checks and fixes
│   ├── INTENT_ROUTER_ARCHITECTURE.md  # Router design document
│   ├── INTENT_ROUTER_ROADMAP.md       # Router implementation plan
│   └── verification-report.json # Machine-generated completion evidence
├── vault/                       # Human-readable knowledge layer
│   ├── Architecture/            # Architecture decisions and patterns
│   ├── Meta/                    # Project meta-knowledge
│   ├── Operations/              # Operational runbooks
│   ├── Project/                 # Project-level documentation
│   ├── Research/                # Research findings
│   ├── Security/                # Security analysis
│   └── Strategy/                # Strategic direction
└── .github/workflows/
    └── ci.yml                   # CI pipeline
```

---

## The Identity System

PARAM's most distinctive feature is its identity architecture. Two plain Markdown files, loaded at session start, define everything PARAM is:

| File | Role | Content |
|------|------|---------|
| `SOUL.md` | Persona | Voice, tone, six core imperatives, relationship dynamic, situational playbook, learning protocol |
| `AGENTS.md` | Protocol | Session startup, three hard gates (Governance, Research Integrity, Verification), tool awareness, exit protocol |

The dual-file design means personality and mechanics evolve independently. Adding an integration never requires rewriting the persona. The identity is version-controlled, plain-text, and can be tuned without rebuilding anything.

### The Three Hard Gates

AGENTS.md enforces three gates that override all OMO framework instructions:

1. **Governance Gate**: Critical decisions (architecture changes, infra modifications, commits, security changes) must go through the user. PARAM presents analysis and waits for approval.
2. **Research Integrity Gate**: No conclusion is valid until independently verified. Single data points are hints, not facts. Every finding carries a confidence level (CONFIRMED, LIKELY, TENTATIVE).
3. **Verification Gate**: No task is complete until verified by machine. `scripts/verify-roadmap.py` is the source of truth, not manual checkboxes.

These gates exist because PARAM's OMO substrate has a "proactive execution" bias that produced wrong conclusions from insufficient data. The gates are the corrective.

---

## The MCP Bridge

`param_hermes_mcp.py` is a 93-line Python MCP server that connects OMO's agent runtime to Hermes's tool surface. It does three things:

1. **Discovery**: Calls Hermes's tool registry to enumerate all available tools
2. **Wrapping**: Exposes each tool under the `hermes__` prefix (e.g., `messages_read` becomes `hermes__messages_read`)
3. **Dispatch**: Strips the prefix and forwards tool calls to the Hermes registry

The bridge is a pass-through, not an orchestrator. It makes Hermes tools available to OMO agents without adding logic. Composition and routing happen at the PARAM identity layer, not in the bridge.

### Exposed Tool Domains

| Domain | Example Tools |
|--------|--------------|
| Terminal | `hermes__terminal`, `hermes__execute_code` |
| Web | `hermes__web_search`, `hermes__web_extract` |
| Browser | `hermes__browser_navigate`, `hermes__browser_snapshot` |
| Files | `hermes__read_file`, `hermes__write_file`, `hermes__patch` |
| Messaging | Telegram gateway adapter |
| Cron | `hermes__cronjob` |
| Memory | `hermes__memory`, `hermes__session_search` |
| Delegation | `hermes__delegate_task` |
| Skills | `hermes__skills_list`, `hermes__skill_view` |

The `hermes__` prefix prevents namespace collisions with OMO's native tools (`bash`, `read`, `write`, `grep`, `glob`, `lsp_*`, etc.) and makes the provenance of every tool call visible in agent reasoning.

---

## The Intent Router

PARAM includes a rule-based intent classifier at `src/router/`. It categorizes incoming user intent into 10 types (CODE_SEARCH, CODE_WRITE, FILE_OPS, WEB_SEARCH, DEPLOYMENT, SCHEDULING, NOTIFICATION, CONVERSATION, SYSTEM_CHECK, and UNKNOWN) using keyword patterns with confidence scoring. A guard layer validates classified intents against safety and policy rules before routing to the appropriate subsystem.

This is the component the ASSESSMENT.md correctly identified as missing during the MVP phase. It now exists and is tested.

---

## Testing

The test suite covers the MCP bridge, intent router, configuration, and memory provider:

```bash
python -m pytest tests/ -v
```

Coverage targets are enforced via `pyproject.toml`:

| Metric | Target |
|--------|--------|
| Line coverage | 90% |
| Branch coverage | 70% |

Mutation testing is configured via mutmut. The CI pipeline runs tests on every push.

For detail on what tests cover and what gaps remain, see the verification report at `specs/verification-report.json`.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](specs/ARCHITECTURE.md) | System design, data flow, component interactions, security model |
| [ASSESSMENT.md](specs/ASSESSMENT.md) | Honest gap analysis: what works, what doesn't, what's oversold |
| [ROADMAP.md](specs/ROADMAP.md) | 82-task implementation plan across 10 phases |
| [EXTENSIONS.md](specs/EXTENSIONS.md) | MCP integration guide and future extension architecture |
| [TROUBLESHOOTING.md](specs/TROUBLESHOOTING.md) | Operational checks, common issues, and fixes |
| [INTENT_ROUTER_ARCHITECTURE.md](specs/INTENT_ROUTER_ARCHITECTURE.md) | Router design and decision rationale |
| [INTENT_ROUTER_ROADMAP.md](specs/INTENT_ROUTER_ROADMAP.md) | Router-specific implementation plan |
| [REDDIT-ANALYSIS.md](specs/REDDIT-ANALYSIS.md) | Patterns and lessons from production Hermes deployments |
| [NOTIFICATIONS.md](specs/NOTIFICATIONS.md) | Notification system design |
| [COMPLIANCE-AUDIT.md](specs/COMPLIANCE-AUDIT.md) | Security and compliance review |

---

## Contributing

PARAM is a personal infrastructure project. The primary development model is solo with agent assistance. If you want to contribute:

1. Read `SOUL.md` and `AGENTS.md` first. They define what PARAM is. You cannot contribute effectively without understanding the identity system.
2. Read `specs/ARCHITECTURE.md` for the system design.
3. Read `specs/ROADMAP.md` for the current implementation plan.
4. Run the test suite (`python -m pytest tests/ -v`) before and after changes.
5. Run the roadmap verifier (`python3 scripts/verify-roadmap.py`) to ensure no regressions.
6. Follow the AGENTS.md communication style in any discussion.

Pull requests are welcome but should target items from the roadmap. Random features that don't align with the architecture will be declined.

---

## License

MIT. See [LICENSE](LICENSE) for details.

---

*PARAM. Callsign Jarvis. "At your service, sir. I've already started."*
