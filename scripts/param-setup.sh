#!/usr/bin/env bash
# =============================================================================
# PARAM Setup Wizard
# Guides user through remaining PARAM configuration steps.
# =============================================================================

set -euo pipefail

PARAM_DIR="$HOME/projects/persistent-agentic-reasoning-automation-mesh"
HERMES_DIR="$HOME/.hermes"
HERMES_AGENT="$HERMES_DIR/hermes-agent"
ENV_FILE="$HERMES_DIR/.env"
CONFIG_FILE="$HERMES_DIR/config.yaml"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok_msg()   { printf "${GREEN}✓${NC} %s\n" "$1"; }
todo_msg() { printf "${YELLOW}⚠${NC} %s\n" "$1"; }
err_msg()  { printf "${RED}✗${NC} %s\n" "$1"; }
header()   { printf "\n${CYAN}${BOLD}%s${NC}\n" "$1"; }

RESULTS=()

record_ok()   { RESULTS+=("${GREEN}✓${NC} $1"); }
record_todo() { RESULTS+=("${YELLOW}⚠${NC} $1"); }
record_err()  { RESULTS+=("${RED}✗${NC} $1"); }
env_value() {
    grep -E "^$1=" "$ENV_FILE" 2>/dev/null | tail -n1 | cut -d= -f2- | sed "s/[[:space:]]*#.*$//" | xargs
}

clear
printf "${CYAN}${BOLD}"
printf "╔══════════════════════════════════════════════╗\n"
printf "║        PARAM Setup Wizard                    ║\n"
printf "║  Persistent Agentic Reasoning Automation Mesh║\n"
printf "╚══════════════════════════════════════════════╝\n"
printf "${NC}\n"

# =============================================================================
# Step 1 — Hermes Installation
# =============================================================================
header "[1/8] Hermes Installation"

if [ -f "$HERMES_AGENT/hermes_constants.py" ] || [ -d "$HERMES_AGENT/hermes" ]; then
    ok_msg "Hermes agent found at $HERMES_AGENT"
    record_ok "Hermes installed"
else
    err_msg "Hermes agent not found at $HERMES_AGENT"
    echo "  Install: cd $HERMES_DIR && git clone https://github.com/your-org/hermes-agent.git"
    record_err "Hermes missing — install required"
fi

if [ -f "$ENV_FILE" ]; then
    ok_msg "Environment file exists at $ENV_FILE"
else
    todo_msg "No .env file found. Copy template:"
    echo "  cp $PARAM_DIR/configs/hermes-env.tmpl $ENV_FILE"
    echo "  chmod 600 $ENV_FILE"
    record_todo "Create ~/.hermes/.env"
fi

# =============================================================================
# Step 2 — MCP Server Verification
# =============================================================================
header "[2/8] MCP Server"

MCP="$PARAM_DIR/param_hermes_mcp.py"
if [ -f "$MCP" ]; then
    if python3 -m py_compile "$MCP" 2>/dev/null; then
        ok_msg "MCP server syntax OK — $MCP"
        record_ok "MCP server valid"
    else
        err_msg "MCP server has syntax errors!"
        python3 -m py_compile "$MCP" 2>&1 | sed 's/^/  /'
        record_err "MCP server has syntax errors"
    fi
else
    err_msg "MCP server not found at $MCP"
    record_err "MCP server file missing"
fi

# Check if MCP is registered in AGENTS.md
if grep -q 'param_hermes_mcp' "$PARAM_DIR/AGENTS.md" 2>/dev/null; then
    ok_msg "MCP server referenced in AGENTS.md"
else
    todo_msg "MCP server NOT referenced in AGENTS.md — add it to the MCP integrations section"
    record_todo "Register MCP server in AGENTS.md"
fi

# =============================================================================
# Step 3 — Telegram Status
# =============================================================================
header "[3/8] Telegram Integration"

TELEGRAM_TOKEN=$(env_value TELEGRAM_BOT_TOKEN)
TELEGRAM_USERS=$(env_value TELEGRAM_ALLOWED_USERS)

if [ -n "$TELEGRAM_TOKEN" ]; then
    ok_msg "Telegram bot token is configured"
    if [ -n "$TELEGRAM_USERS" ]; then
        ok_msg "Telegram allowed users configured"
        record_ok "Telegram configured"
    else
        todo_msg "Set TELEGRAM_ALLOWED_USERS to your Telegram numeric user ID"
        echo "  Message @userinfobot on Telegram to find your ID."
        record_todo "Configure Telegram allowed users"
    fi
else
    todo_msg "Telegram bot token missing. Create a bot with @BotFather."
    echo "  Set TELEGRAM_BOT_TOKEN in $ENV_FILE"
    echo "  Set TELEGRAM_ALLOWED_USERS to your Telegram numeric user ID"
    record_todo "Configure Telegram bot"
fi

# =============================================================================
# Step 4 — Memory Providers
# =============================================================================
header "[4/8] Memory Providers"

HONCHO_KEY=$(env_value HONCHO_API_KEY)
MEM0_KEY=$(env_value MEM0_API_KEY)

if [ -n "$HONCHO_KEY" ]; then
    ok_msg "Honcho configured (API key present)"
    record_ok "Honcho memory configured"
else
    todo_msg "Honcho not configured. Get API key from https://app.honcho.dev"
    echo "  Set HONCHO_API_KEY in $ENV_FILE"
    record_todo "Configure Honcho API key"
fi

if [ -n "$MEM0_KEY" ] && [ "$MEM0_KEY" != "m0-your-mem0-api-key" ]; then
    ok_msg "Mem0 configured (key present)"
    record_ok "Mem0 memory configured"
else
    todo_msg "Mem0 not configured. Get API key from https://app.mem0.ai/settings/api-keys"
    echo "  Set MEM0_API_KEY in $ENV_FILE"
    record_todo "Configure Mem0 API key"
fi

# =============================================================================
# Step 5 — Cron Jobs
# =============================================================================
header "[5/8] Cron Scheduler"

CRON_ENABLED=$(grep -A10 '^cron:' "$CONFIG_FILE" 2>/dev/null | grep -E '^[[:space:]]+enabled:[[:space:]]+true' || true)
CRON_LIST=$($HERMES_AGENT/venv/bin/python $HERMES_AGENT/hermes_cli/main.py cron list 2>/dev/null || true)

if [ -n "$CRON_ENABLED" ]; then
    ok_msg "Cron scheduler is enabled in config.yaml"
    if echo "$CRON_LIST" | grep -q "No scheduled jobs"; then
        todo_msg "Cron is enabled but no jobs are created yet"
        record_todo "Create PARAM cron jobs with hermes cron create"
    else
        ok_msg "Cron jobs found"
        record_ok "Cron enabled"
    fi
else
    todo_msg "Cron not enabled. To activate:"
    echo "  1. Set cron.enabled: true in $CONFIG_FILE"
    echo "  2. Create jobs with hermes cron create"
    record_todo "Enable cron scheduler"
fi

# =============================================================================
# Step 6 — TokenEye Proxy Check
# =============================================================================
header "[6/8] TokenEye Proxy"

if command -v nc &>/dev/null; then
    if nc -z -w 2 127.0.0.1 8787 2>/dev/null; then
        ok_msg "Proxy responding on localhost:8787"
        record_ok "TokenEye proxy running"
    else
        todo_msg "Nothing listening on 127.0.0.1:8787"
        echo "  Start TokenEye proxy or update API endpoints in $ENV_FILE"
        echo "  See: https://tokeneye.io/docs"
        record_todo "Configure TokenEye proxy (optional)"
    fi
else
    todo_msg "Cannot check proxy (nc not available)"
    echo "  Install netcat or manually verify: curl http://127.0.0.1:8787/health"
    record_todo "Verify TokenEye proxy manually"
fi

# Check if API keys use TokenEye URLs
if grep -qE 'ANTHROPIC_BASE_URL=.*tokeneye' "$ENV_FILE" 2>/dev/null; then
    ok_msg "LLM endpoints pointed at TokenEye"
else
    todo_msg "LLM endpoints not using TokenEye (using direct API keys)"
    echo "  Recommended: route through TokenEye for unified billing."
    echo "  Set ANTHROPIC_BASE_URL=https://api.tokeneye.io/v1/anthropic"
    record_todo "Route LLM through TokenEye (recommended)"
fi

# =============================================================================
# Step 7 — AGENTS.md Deployed
# =============================================================================
header "[7/8] AGENTS.md Deployment"

if [ -f "$PARAM_DIR/AGENTS.md" ]; then
    ok_msg "AGENTS.md exists in repo"
    record_ok "AGENTS.md deployed"
    
    # Check if SOUL.md is referenced
    if grep -q 'SOUL.md' "$PARAM_DIR/AGENTS.md" 2>/dev/null; then
        ok_msg "SOUL.md referenced in AGENTS.md"
    else
        todo_msg "SOUL.md not referenced in AGENTS.md — add load step"
        record_todo "Link SOUL.md in AGENTS.md"
    fi
else
    err_msg "AGENTS.md missing from $PARAM_DIR"
    record_err "AGENTS.md missing"
fi

# =============================================================================
# Step 8 — Summary
# =============================================================================
header "[8/8] Setup Summary"

echo ""
NEEDS_ACTION=0
for result in "${RESULTS[@]}"; do
    echo "  $result"
    if [[ $result == *"⚠"* ]] || [[ $result == *"✗"* ]]; then
        NEEDS_ACTION=$((NEEDS_ACTION + 1))
    fi
done

echo ""
if [ $NEEDS_ACTION -eq 0 ]; then
    printf "${GREEN}${BOLD}✓ All systems ready. PARAM is fully configured.${NC}\n"
else
    printf "${YELLOW}${BOLD}⚠ $NEEDS_ACTION item(s) need attention.${NC}\n"
    echo ""
    echo "Next steps:"
    echo "  1. Fix items marked with ⚠ (TODO) above"
    echo "  2. Restart Hermes after changes:"
    echo "     kill \$(cat $HERMES_DIR/gateway.lock 2>/dev/null) 2>/dev/null || true"
    echo "     cd $HERMES_DIR && python hermes-agent/run_agent.py --gateway &"
    echo "  3. Re-run this wizard to verify:"
    echo "     bash $PARAM_DIR/scripts/param-setup.sh"
fi

echo ""
printf "${CYAN}For full setup docs:${NC}\n"
printf "  cat $PARAM_DIR/README.md\n"
printf "${CYAN}For architecture reference:${NC}\n"
printf "  cat $PARAM_DIR/specs/ARCHITECTURE.md\n"
echo ""
