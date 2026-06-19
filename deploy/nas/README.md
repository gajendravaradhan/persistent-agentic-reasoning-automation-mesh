# PARAM NAS Docker Deployment

Deploy PARAM/Hermes on Ugreen NAS with Docker Compose for 24/7 unattended operation.

## What You Get

| Feature | Status |
|---------|--------|
| 24/7 agent runtime | `restart: unless-stopped`, s6-overlay PID 1 |
| Telegram bot | Long-polling, zero inbound ports |
| Cron automation | 3 jobs: 30m heartbeat, 6h status, 9am daily check-in |
| Self-learning memory | 8 providers (Honcho, Mem0, Supermemory, etc.) |
| Dashboard | Web UI at `localhost:9119` |
| Auto-healing | Container auto-restarts on crash |

## Prerequisites

- Ugreen NAS with Docker + Docker Compose
- Hermes installed on your Mac (`~/.hermes/` exists)
- Telegram bot token from @BotFather
- For Cloudflare Tunnel: cloudflared + Cloudflare-managed domain

## Quick Start

**Option 1: Use pre-prepared config (recommended — already done in repo)**

```bash
cd persistent-agentic-reasoning-automation-mesh/deploy/nas

# hermes-data/ is already populated from Mac. Edit .env if needed.
nano hermes-data/.env
# Verify: TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS

# Start
HERMES_UID=$(id -u) HERMES_GID=$(id -g) ./deploy.sh start
```

**Option 2: Prepare fresh from local Hermes**

```bash
cd persistent-agentic-reasoning-automation-mesh/deploy/nas

# 1. Copy config from Mac to deploy directory
./deploy.sh prepare

# 2. Edit API keys
nano hermes-data/.env

# 3. Start
HERMES_UID=$(id -u) HERMES_GID=$(id -g) ./deploy.sh start
```

## Model Provider Routing

Your Mac runs TokenEye at `localhost:8787`. The NAS can't reach that. Choose one:

### Option A: OpenRouter (recommended, simplest)

Get a key at [openrouter.ai](https://openrouter.ai) and edit `hermes-data/.env`:
```
OPENROUTER_API_KEY=sk-or-v1-...
```
Then edit `hermes-data/config.yaml`:
```yaml
model:
  provider: openrouter
  default: anthropic/claude-sonnet-4-20250514
  base_url: https://openrouter.ai/api/v1
```

### Option B: Run TokenEye on NAS

Clone TokenEye and run as a Docker sidecar:
```bash
git clone https://github.com/gajendravaradhan/TokenEye.git tokeneye
mkdir -p tokeneye-config
cp ~/.config/tokeneye/config.json tokeneye-config/
```
Uncomment the `tokeneye` service in `docker-compose.yml`, then:
```bash
# Start TokenEye separately first to verify
docker compose up -d tokeneye
# Then start Hermes (already configured for localhost:8787)
docker compose up -d gateway dashboard
```

### Option C: Direct Anthropic/OpenAI

Set the provider directly (needs own API key):
```yaml
model:
  provider: anthropic
  default: claude-sonnet-4-20250514
```
```env
ANTHROPIC_API_KEY=sk-ant-...
```

## Memory: Self-Learning

Hermes has 8 built-in memory providers. Enable one:

```yaml
# hermes-data/config.yaml
memory:
  provider: mem0          # or: honcho, supermemory, etc.
  memory_enabled: true
  user_profile_enabled: true
```

```env
# hermes-data/.env
MEM0_API_KEY=m0-...
# or: HONCHO_API_KEY=...
```

Get keys:
- Mem0: [mem0.ai](https://mem0.ai)
- Honcho: [app.honcho.dev](https://app.honcho.dev)
- Supermemory: [supermemory.ai](https://supermemory.ai)

## Cloudflare Tunnel (Dashboard Remote Access)

```bash
# Non-interactive setup (uses pre-configured *.aiforges.app domain)
./cloudflared-setup-noninteractive.sh

# Or interactive setup (any domain)
./cloudflared-setup.sh
```

Creates a secure tunnel from NAS to Cloudflare. Dashboard available at `https://param.aiforges.app` without opening router ports.

**Tunnel routes:**
| Hostname | Service | Port |
|----------|---------|------|
| `param.aiforges.app` | Hermes Dashboard | 9119 |
| `api.param.aiforges.app` | API / Health | 9119 |
| `tokeneye.aiforges.app` | TokenEye Dashboard | 8788 |

## Commands

```bash
./deploy.sh prepare    # Copy config from ~/.hermes
./deploy.sh start      # Start containers
./deploy.sh stop       # Stop containers
./deploy.sh logs       # Tail gateway logs
./deploy.sh status     # Container + cron status
./deploy.sh shell      # Open shell in gateway
./deploy.sh restart    # Restart containers
```

## Verifying

After start:
```bash
# Check gateway
docker compose exec gateway hermes gateway status
docker compose exec gateway hermes cron list

# Check Telegram: send /status to your bot
# Dashboard: open http://nas-ip:9119 (or via Cloudflare Tunnel URL)
```

## File Layout

```
deploy/nas/
├── docker-compose.yml      # Gateway + Dashboard + optional TokenEye
├── deploy.sh               # Management script
├── cloudflared-setup.sh    # Cloudflare Tunnel setup
├── README.md               # This file
└── hermes-data/            # Created by deploy.sh prepare
    ├── .env                # API keys (TELEGRAM_BOT_TOKEN, provider keys)
    ├── config.yaml         # Hermes config (model, memory, cron, gateway)
    ├── memories/           # Seeded MEMORY.md + USER.md
    ├── cron/               # Cron job definitions + state
    ├── sessions/           # Conversation state
    ├── skills/             # Installed skills
    └── plugins/            # Installed plugins
```

## Troubleshooting

**Gateway won't start**: Check `docker compose logs gateway`
**Telegram not responding**: Verify TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USERS in `.env`
**Model errors**: Verify provider config and API key in `.env` + `config.yaml`
**Permission errors**: Ensure HERMES_UID/GID match NAS user: `id -u && id -g`
