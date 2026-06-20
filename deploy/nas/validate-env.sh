#!/usr/bin/env bash
# PARAM .env Validator — checks required environment variables before startup
# Run: ./validate-env.sh [path/to/.env]

set -euo pipefail

ENV_FILE="${1:-.env}"
ERRORS=0
WARNINGS=0

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "PARAM Environment Validator"
echo "=========================="

# Source the .env file if it exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗${NC} .env file not found at $ENV_FILE"
    exit 1
fi
set -a; source "$ENV_FILE" 2>/dev/null; set +a
echo "  Source: $ENV_FILE"
echo ""

# --- CRITICAL: Must be present and non-empty ---
critical() {
    local var="$1"
    local desc="$2"
    if [ -z "${!var:-}" ]; then
        echo -e "  ${RED}✗${NC} $var — $desc"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "  ${GREEN}✓${NC} $var"
    fi
}

# --- WARNING: Should be present but non-fatal ---
warn_if_missing() {
    local var="$1"
    local desc="$2"
    if [ -z "${!var:-}" ]; then
        echo -e "  ${YELLOW}⚠${NC} $var — $desc (not set)"
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "  ${GREEN}✓${NC} $var"
    fi
}

echo "Critical:"
critical TELEGRAM_BOT_TOKEN     "Telegram bot token from @BotFather"
critical TELEGRAM_ALLOWED_USERS  "Comma-separated allowed Telegram user IDs"
echo ""

echo "TokenEye:"
warn_if_missing OPENCODE_GO_API_KEY  "Primary LLM API key (managed-by-tokeneye)"
echo ""

echo "Langfuse (optional):"
warn_if_missing HERMES_LANGFUSE_PUBLIC_KEY  "Langfuse public key (pk-lf-...)"
warn_if_missing HERMES_LANGFUSE_SECRET_KEY  "Langfuse secret key (sk-lf-...)"
echo ""

# --- Validate format where possible ---
echo "Format checks:"
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    if [[ "$TELEGRAM_BOT_TOKEN" =~ ^[0-9]+:[a-zA-Z0-9_-]+$ ]]; then
        echo -e "  ${GREEN}✓${NC} TELEGRAM_BOT_TOKEN format valid"
    else
        echo -e "  ${YELLOW}⚠${NC} TELEGRAM_BOT_TOKEN — unexpected format"
    fi
fi
if [ -n "${HERMES_LANGFUSE_PUBLIC_KEY:-}" ]; then
    if [[ "$HERMES_LANGFUSE_PUBLIC_KEY" == pk-lf-* ]]; then
        echo -e "  ${GREEN}✓${NC} HERMES_LANGFUSE_PUBLIC_KEY prefix valid"
    else
        echo -e "  ${YELLOW}⚠${NC} HERMES_LANGFUSE_PUBLIC_KEY — should start with pk-lf-"
    fi
fi
if [ -n "${HERMES_LANGFUSE_SECRET_KEY:-}" ]; then
    if [[ "$HERMES_LANGFUSE_SECRET_KEY" == sk-lf-* ]]; then
        echo -e "  ${GREEN}✓${NC} HERMES_LANGFUSE_SECRET_KEY prefix valid"
    else
        echo -e "  ${YELLOW}⚠${NC} HERMES_LANGFUSE_SECRET_KEY — should start with sk-lf-"
    fi
fi
echo ""

# --- Result ---
echo "=========================="
if [ "$ERRORS" -gt 0 ]; then
    echo -e "${RED}VALIDATION FAILED: $ERRORS error(s), $WARNINGS warning(s)${NC}"
    echo "Fix the errors above before starting PARAM."
    exit 1
elif [ "$WARNINGS" -gt 0 ]; then
    echo -e "${YELLOW}VALIDATION PASSED with warnings: $WARNINGS warning(s)${NC}"
    exit 0
else
    echo -e "${GREEN}VALIDATION PASSED — all checks green${NC}"
    exit 0
fi
