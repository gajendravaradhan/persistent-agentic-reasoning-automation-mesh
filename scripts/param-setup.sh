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
# Step 3 — WhatsApp Status
# =============================================================================
header "[3/8] WhatsApp Integration"

WHATSAPP_ENABLED=$(grep -E '^WHATSAPP_ENABLED=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "false")

if [ "$WHATSAPP_ENABLED" = "true" ]; then
    ok_msg "WhatsApp is enabled in .env"
    
    # Check if paired (look for pairing state files)
    if [ -d "$HERMES_DIR/pairing" ] && [ "$(ls -A "$HERMES_DIR/pairing" 2>/dev/null)" ]; then
        ok_msg "WhatsApp pairing data found"
        record_ok "WhatsApp paired"
    else
        todo_msg "WhatsApp enabled but not paired. Run pairing command:"
        echo "  python $HERMES_AGENT/hermes_cli/main.py whatsapp"
        record_todo "Pair WhatsApp"
    fi
else
    todo_msg "WhatsApp not enabled. Set WHATSAPP_ENABLED=true in .env"
    echo "  Or skip if you don't need WhatsApp."
    echo "  To enable, see: $PARAM_DIR/configs/whatsapp-config.md"
    record_todo "Enable WhatsApp (optional)"
fi

# =============================================================================
# Step 4 — Memory Providers
# =============================================================================
header "[4/8] Memory Providers"

HONCHO_ID=$(grep -E '^HONCHO_APP_ID=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "")
MEM0_KEY=$(grep -E '^MEM0_API_KEY=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "")

if [ -n "$HONCHO_ID" ] && [ "$HONCHO_ID" != "your-honcho-app-id" ]; then
    ok_msg "Honcho configured (APP_ID: $HONCHO_ID)"
    record_ok "Honcho memory configured"
else
    todo_msg "Honcho not configured. Get APP_ID from https://honcho.dev/dashboard"
    echo "  Set HONCHO_APP_ID in $ENV_FILE"
    record_todo "Configure Honcho APP_ID"
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

CRON_ENABLED=$(grep -E '^CRON_ENABLED=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "false")

if [ "$CRON_ENABLED" = "true" ]; then
    ok_msg "Cron is enabled"
    if [ -f "$HERMES_DIR/cron-jobs.yaml" ]; then
        ok_msg "Cron job definitions found"
    fi
    record_ok "Cron enabled"
else
    todo_msg "Cron not enabled. To activate:"
    echo "  1. Set CRON_ENABLED=true in $ENV_FILE"
    echo "  2. Copy cron definitions:"
    echo "     cp $PARAM_DIR/configs/cron-jobs.yaml $HERMES_DIR/cron-jobs.yaml"
    echo "  3. Set cron.enabled: true in $CONFIG_FILE (under the cron: section)"
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
