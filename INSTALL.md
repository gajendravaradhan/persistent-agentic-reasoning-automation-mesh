# PARAM — Installation Guide

This guide walks you through setting up PARAM from scratch. Read all sections before running any commands — several decisions early on affect how you configure later components.

**Time to basic setup**: 30–60 minutes  
**Time to full NAS deployment**: 2–4 hours

---

## Table of Contents

1. [What PARAM Requires](#1-what-param-requires)
2. [Choose Your Deployment Mode](#2-choose-your-deployment-mode)
3. [Step 1 — Install Dependencies](#step-1--install-dependencies)
4. [Step 2 — Clone and Configure PARAM](#step-2--clone-and-configure-param)
5. [Step 3 — Configure the MCP Bridge](#step-3--configure-the-mcp-bridge)
6. [Step 4 — Set Up Hermes](#step-4--set-up-hermes)
7. [Step 5 — Telegram Bot (Optional but Recommended)](#step-5--telegram-bot-optional-but-recommended)
8. [Step 6 — Test the Setup](#step-6--test-the-setup)
9. [Step 7 — NAS Deployment (Optional, 24/7)](#step-7--nas-deployment-optional-247)
10. [Step 8 — Optional Components](#step-8--optional-components)
11. [Verification](#verification)
12. [Troubleshooting](#troubleshooting)

---

## 1. What PARAM Requires

PARAM is a bridge and configuration layer, not a standalone application. It requires two underlying systems:

| System | Role | Where to Get It |
|--------|------|-----------------|
| **OhMyOpenCode (OMO)** | Agent runtime, tool execution, LLM routing | [oh-my-opencode npm package](https://www.npmjs.com/package/oh-my-opencode) |
| **Hermes Agent** | Persistent automation: messaging, cron, memory, kanban | [hermes-agent releases](https://github.com/heurist-ai/hermes-agent) |

Without both, PARAM does nothing. These are not optional.

### Required Accounts

| Service | Required For | Free Tier Available? |
|---------|-------------|----------------------|
| **LLM provider** | Any AI responses | Yes (opencode-go, Nous free tier) |
| **Telegram Bot** | Messaging interface | Yes (free via @BotFather) |

### Optional Accounts

| Service | Required For | Free Tier Available? |
|---------|-------------|----------------------|
| **Langfuse** | Session observability | Yes (cloud.langfuse.com, 50K units/month) |
| **Cloudflare** | Tunnel for remote access | Yes |
| **Discord** | Second messaging channel | Yes |

---

## 2. Choose Your Deployment Mode

Before proceeding, decide what you're building:

### Mode A: Local Only (MacBook/Desktop)
**Best for:** Trying PARAM out, development, MacBook-first workflow  
**What you get:** Full OMO agent pool, Hermes tools, Telegram messaging during active sessions  
**What you don't get:** 24/7 availability, autonomous cron jobs, persistent background operation  
**Time:** 30–60 minutes

### Mode B: Full NAS Deployment (24/7)
**Best for:** Actual daily use, autonomous operation, always-on Telegram  
**What you need:** A Docker host (NAS, VPS, Raspberry Pi, cloud VM — anything running Docker 24/7)  
**What you get:** Everything in Mode A plus: background cron jobs, always-on Telegram, persistent memory across sessions, multi-channel (Telegram + Discord + webhook)  
**Time:** 2–4 hours

> **Recommendation:** Start with Mode A to verify everything works, then add the NAS deployment.

---

## Step 1 — Install Dependencies

### 1.1 Python 3.11+

```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt-get install python3.11 python3.11-venv

# Verify
python3 --version
```

### 1.2 Node.js / Bun (for OMO)

```bash
# Install Bun (recommended — faster than Node for OMO)
curl -fsSL https://bun.sh/install | bash

# Or Node.js via nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
nvm install 20
```

### 1.3 OpenCode CLI (required for OMO)

```bash
# Install OpenCode
curl -fsSL https://opencode.ai/install | bash
# or
npm install -g @opencode-ai/cli
```

### 1.4 OhMyOpenCode Plugin

```bash
# Install globally
npm install -g oh-my-opencode

# Verify OMO is installed
omo --version
```

### 1.5 Hermes Agent

Download the latest release from [hermes-agent releases](https://github.com/heurist-ai/hermes-agent/releases) and install:

```bash
# macOS (example — check current release URL)
curl -L https://github.com/heurist-ai/hermes-agent/releases/latest/download/hermes-macos -o /usr/local/bin/hermes
chmod +x /usr/local/bin/hermes

# Verify
hermes --version
```

---

## Step 2 — Clone and Configure PARAM

```bash
git clone https://github.com/gajendravaradhan/persistent-agentic-reasoning-automation-mesh.git
cd persistent-agentic-reasoning-automation-mesh

# Create virtual environment for MCP bridge
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install mcp pyyaml pytest pytest-cov
```

### 2.1 Choose Your Identity Files

PARAM ships with pre-written `SOUL.md` and `AGENTS.md`. You have two options:

**Option A: Use as-is** — The persona is written for Gajendra's workflow (Tony Stark / Jarvis dynamic). You can use it verbatim. It's generic enough.

**Option B: Customize** — Edit `SOUL.md` to change:
- Name/callsign (find/replace "Jarvis" with your preferred name)
- The Tony Stark / user relationship framing (Section 4)
- The situational playbook examples (Section 9)

Do **not** change:
- The six core imperatives (Section 3)
- The hard gates in `AGENTS.md`
- The prohibited behaviors list

### 2.2 Copy Identity Files to Config

```bash
# OMO reads AGENTS.md from ~/.config/opencode/
cp AGENTS.md ~/.config/opencode/AGENTS.md

# Hermes reads SOUL.md from its config directory
cp SOUL.md ~/.hermes/SOUL.md
```

---

## Step 3 — Configure the MCP Bridge

The MCP bridge (`param_hermes_mcp.py`) connects OMO to Hermes. It needs to be registered in OMO's MCP config.

### 3.1 Get the Absolute Path

```bash
echo "$(pwd)/.venv/bin/python"
echo "$(pwd)/param_hermes_mcp.py"
```

### 3.2 Register the Bridge

Add to `~/.mcp.json` (create if it doesn't exist):

```json
{
  "mcpServers": {
    "hermes": {
      "type": "stdio",
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/param_hermes_mcp.py"],
      "env": {}
    }
  }
}
```

Replace the paths with the absolute paths from Step 3.1. Relative paths and `~` do not work here.

### 3.3 Verify the Bridge Starts

```bash
# Test the bridge directly
.venv/bin/python param_hermes_mcp.py
# Should start without errors (Ctrl+C to stop)
```

---

## Step 4 — Set Up Hermes

### 4.1 Initialize Hermes Config

```bash
hermes init
# Creates ~/.hermes/config.yaml
```

### 4.2 Configure an LLM Provider

Edit `~/.hermes/config.yaml`. Choose one:

**Option A: opencode-go (recommended — includes free tier with OMO subscription)**
```yaml
model:
  provider: openai
  name: kimi-k2.5  # or any model from opencode-go
  base_url: http://127.0.0.1:8787/zen/go/v1  # if using TokenEye locally
  # OR directly:
  base_url: https://opencode.ai/zen/go/v1
  api_key: YOUR_OPENCODE_GO_API_KEY
```

**Option B: Anthropic Claude**
```yaml
model:
  provider: anthropic
  name: claude-sonnet-4-5
  api_key: YOUR_ANTHROPIC_API_KEY
```

**Option C: OpenAI**
```yaml
model:
  provider: openai
  name: gpt-4o
  api_key: YOUR_OPENAI_API_KEY
```

### 4.3 Set Required Environment Variables

Create `~/.hermes/.env`:

```bash
# Required
TELEGRAM_BOT_TOKEN=          # See Step 5
TELEGRAM_ALLOWED_USERS=      # Your Telegram user ID (get from @userinfobot)

# LLM provider (if using API key)
OPENCODE_API_KEY=             # opencode-go key
# OR
ANTHROPIC_API_KEY=
# OR
OPENAI_API_KEY=
```

```bash
chmod 600 ~/.hermes/.env
```

---

## Step 5 — Telegram Bot (Optional but Recommended)

Without Telegram, PARAM only works in interactive OpenCode sessions. Telegram gives you persistent messaging, mobile access, and the ability to talk to PARAM when you're away from your computer.

### 5.1 Create a Bot

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Follow prompts — choose a name and username
4. Copy the token (format: `123456789:AAH...`)

### 5.2 Get Your User ID

1. Search for `@userinfobot` in Telegram
2. Send it any message
3. Copy your numeric user ID

### 5.3 Configure

Add to `~/.hermes/.env`:
```bash
TELEGRAM_BOT_TOKEN=123456789:AAH...
TELEGRAM_ALLOWED_USERS=YOUR_NUMERIC_ID
```

Add to `~/.hermes/config.yaml`:
```yaml
gateway:
  platforms:
    telegram:
      enabled: true
      bot_token: ${TELEGRAM_BOT_TOKEN}
      allowed_users: [${TELEGRAM_ALLOWED_USERS}]
```

---

## Step 6 — Test the Setup

### 6.1 Run the Test Suite

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

All tests should pass. If any fail, see [Troubleshooting](#troubleshooting).

### 6.2 Start Hermes

```bash
hermes start
```

### 6.3 Test Telegram (if configured)

Send a message to your bot. It should respond within a few seconds.

### 6.4 Start an OMO Session

```bash
opencode
```

In the session, verify PARAM identity is loaded:
- The session startup should reference `~/.config/opencode/AGENTS.md`
- PARAM should greet with "Jarvis online." (or your customized callsign)
- `hermes__*` tools should be available

---

## Step 7 — NAS Deployment (Optional, 24/7)

Skip this section if you're using Mode A (local only).

### 7.1 Prerequisites

- Docker host with 2GB+ RAM, 20GB+ storage
- SSH access to the host
- A Cloudflare account with a domain (for remote tunnel)

### 7.2 Prepare the NAS Data Directory

```bash
cd deploy/nas

# Stage configuration files to NAS data directory
./deploy.sh prepare

# Review what was staged
ls -la hermes-data/
```

### 7.3 Configure NAS Environment

```bash
cp hermes-data/.env.example hermes-data/.env
# Edit hermes-data/.env with your keys (same as local .env, but for NAS)
chmod 600 hermes-data/.env

# Validate
./validate-env.sh
```

### 7.4 Configure NAS Hermes Config

Copy `configs/hermes-config.yaml.tmpl` to `hermes-data/config.yaml` and fill in:

```yaml
model:
  base_url: http://tokeneye:8787/zen/go/v1  # TokenEye is a sidecar on NAS
  # other provider config...

gateway:
  platforms:
    telegram:
      enabled: true
      # ...

memory:
  provider: honcho
  honcho:
    base_url: http://honcho-api:8000  # Honcho sidecar
    workspace_name: param
```

### 7.5 Transfer to NAS

```bash
# Copy the deploy directory to your NAS
scp -r deploy/nas/ user@your-nas:/path/to/param/

# SSH into NAS
ssh user@your-nas

# Start the stack
cd /path/to/param/nas
HERMES_UID=$(id -u) HERMES_GID=$(id -g) ./deploy.sh start
```

### 7.6 Set Up Cloudflare Tunnel

```bash
# On your NAS
./cloudflared-setup.sh
```

Follow prompts. This creates a permanent tunnel at `param.your-domain.com` pointing to the Hermes dashboard.

### 7.7 Verify NAS Deployment

```bash
# Check containers
docker ps --format 'table {{.Names}}\t{{.Status}}'

# Should show: param-hermes, param-tokeneye, param-honcho (and sidecars)
```

Send a Telegram message to your bot — it should respond from the NAS.

---

## Step 8 — Optional Components

### 8.1 TokenEye Proxy (LLM Load Balancing)

**What it does**: Balances requests across multiple API keys, tracks cost per call, provides failover  
**When to add**: If you have 2+ API keys, or want cost tracking  
**How**: See [TokenEye README](https://github.com/gajendravaradhan/TokenEye)

### 8.2 Honcho Memory (Dialectic Reasoning)

**What it does**: Cross-session context persistence with multi-pass reasoning  
**When to add**: When you notice PARAM forgetting things between sessions  
**Default**: `MEMORY.md` flat file (simpler, sufficient for low session volume)

> **Decision**: Honcho requires a running Docker container and adds ~200MB RAM. For most users, the MEMORY.md flat file is sufficient to start. Add Honcho after 2–4 weeks when you've validated the workflow.

To enable Honcho:
```yaml
# In config.yaml
memory:
  provider: honcho
  honcho:
    base_url: http://localhost:8000
    workspace_name: param
```

### 8.3 Langfuse Observability

**What it does**: Logs every LLM call with tokens, cost, latency, and prompt/response  
**When to add**: When debugging model behavior or tracking costs  
**Free tier**: cloud.langfuse.com, 50K events/month

```yaml
# In config.yaml
plugins:
  enabled:
    - observability/langfuse

langfuse:
  public_key: pk-lf-...
  secret_key: sk-lf-...
  host: https://cloud.langfuse.com
```

### 8.4 Discord Gateway

**What it does**: Second messaging channel alongside Telegram  
**When to add**: If you want PARAM reachable from Discord  

```yaml
# In config.yaml
gateway:
  platforms:
    discord:
      enabled: true
      bot_token: ${DISCORD_BOT_TOKEN}
```

### 8.5 Skill Whitelist

PARAM ships with 71 Hermes skills. By default all are loaded. The skill whitelist reduces that per-agent. This saves tokens but requires manual configuration.

See `configs/skill-whitelist.yaml` for the pre-configured agent skill sets.

> **Note**: Skip this initially. Add it after you've run a few sessions and notice which skills you actually use.

---

## Verification

Run the full verification suite to confirm your setup:

```bash
# Test suite
python -m pytest tests/ -v --tb=short

# Roadmap verification (requires NAS for full check; runs locally for code checks)
python3 scripts/verify-roadmap.py

# Basic health check
./scripts/param-status.sh
```

---

## Troubleshooting

### MCP bridge not loading in OMO

1. Check absolute paths in `~/.mcp.json` — no relative paths, no `~`
2. Verify the venv has `mcp` installed: `.venv/bin/pip show mcp`
3. Test the bridge directly: `.venv/bin/python param_hermes_mcp.py` (should start without error)
4. Check OMO logs for bridge startup errors

### Hermes not starting

1. Check Python path in mcp.json points to the venv, not system python
2. Run `hermes --debug` for verbose output
3. Verify `~/.hermes/.env` has `chmod 600`
4. Check `~/.hermes/config.yaml` is valid YAML: `python3 -c "import yaml; yaml.safe_load(open('~/.hermes/config.yaml'))"`

### Telegram not responding

1. Verify bot token is correct (no spaces, no extra characters)
2. Verify your user ID is in `TELEGRAM_ALLOWED_USERS`
3. Check Hermes gateway logs: `hermes logs`
4. Send `/start` to your bot first (Telegram bots require users to initiate)

### NAS containers not starting

1. Run `docker compose logs` to see specific errors
2. Check `.env` file has all required variables: run `./validate-env.sh`
3. Verify port conflicts: `docker ps` to see what's using ports 9119, 8787, 8000
4. Check `HERMES_UID` and `HERMES_GID` are set for file permission correctness

### Tests failing

```bash
# Run with verbose output to see exactly what's failing
python -m pytest tests/ -v --tb=long

# Run specific test file
python -m pytest tests/test_mcp_bridge.py -v
```

Most test failures in a fresh setup are path issues (tests expect the venv to be active).

---

## Common Customizations

### Change the persona name

In `SOUL.md`, find and replace "Jarvis" with your preferred callsign. In `AGENTS.md`, update the callsign references in the Session Startup Protocol section.

### Add a new LLM provider

Edit `~/.hermes/config.yaml` under the `model:` section. Hermes supports any OpenAI-compatible API endpoint.

### Add a new MCP server

See `specs/EXTENSIONS.md` for the full guide. The short version: create a Python MCP server script, register it in `~/.mcp.json`, restart your OMO session.

### Set up a cron job

```bash
hermes cron create --schedule "0 9 * * *" --name "morning-check" \
  --prompt "Check Telegram, review kanban, send status to Telegram"
```

### Configure memory consolidation

```yaml
# In config.yaml
memory:
  consolidation:
    enabled: true
    schedule: "0 2 * * 0"  # Weekly at 2am Sunday
```

---

## What PARAM Is and Isn't (For New Users)

PARAM is an **identity layer and integration bridge** — it makes OMO and Hermes work as a single coherent entity. It is not:

- A replacement for Hermes (you still need Hermes)
- A replacement for OMO (you still need OpenCode + OMO)
- A standalone AI (it has no inference capability of its own)

Think of PARAM as the personality and the wiring. Hermes is the hands. OMO is the brain. Your LLM provider is the knowledge. PARAM is what makes "I" mean something consistent across all three.

---

## Getting Help

- [ARCHITECTURE.md](specs/ARCHITECTURE.md) — system design and data flow
- [TROUBLESHOOTING.md](specs/TROUBLESHOOTING.md) — operational issues and fixes
- [EXTENSIONS.md](specs/EXTENSIONS.md) — adding new integrations
- [GitHub Issues](https://github.com/gajendravaradhan/persistent-agentic-reasoning-automation-mesh/issues)

---

*PARAM. Callsign Jarvis. "At your service, sir. I've already started."*
