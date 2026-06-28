#!/usr/bin/env bash
# PARAM Status Checker — quick health dashboard

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BOLD}PARAM Status Dashboard${NC}"
echo "======================"
echo ""

env_value() {
    grep -E "^$1=" "$HOME/.hermes/.env" 2>/dev/null | tail -n1 | cut -d= -f2- | sed "s/[[:space:]]*#.*$//" | xargs
}

# 1. Hermes Agent
echo -n "  Hermes Agent: "
if [ -d "$HOME/.hermes/hermes-agent" ]; then
    echo -e "${GREEN}INSTALLED${NC}"
else
    echo -e "${RED}MISSING${NC}"
fi

# 2. MCP Server
echo -n "  MCP Server:   "
if python3 -c "import py_compile; py_compile.compile('$HOME/projects/persistent-agentic-reasoning-automation-mesh/param_hermes_mcp.py', doraise=True)" 2>/dev/null; then
    TOOLS=$(/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/python -c "
import os,sys; os.environ['HERMES_HOME']='$HOME/.hermes'; sys.path.insert(0,'$HOME/.hermes/hermes-agent')
from tools.registry import registry, discover_builtin_tools; discover_builtin_tools()
print(len(registry._snapshot_entries()))" 2>/dev/null)
    echo -e "${GREEN}$TOOLS tools${NC}"
else
    echo -e "${RED}SYNTAX ERROR${NC}"
fi

# 3. TokenEye (runs on NAS in param-tokeneye container, not on this Mac)
echo -n "  TokenEye:     "
if curl -s https://tokeneye.aiforges.app/__health > /dev/null 2>&1; then
    echo -e "${GREEN}UP (NAS-hosted, dashboard reachable)${NC}"
else
    echo -e "${RED}DOWN${NC}"
fi

# 4. Model provider
echo -n "  Model route:  "
MODEL_INFO=$($HOME/.hermes/hermes-agent/venv/bin/python - <<'PY' 2>/dev/null
from pathlib import Path
import yaml
cfg = yaml.safe_load(Path.home().joinpath('.hermes/config.yaml').read_text())
model = cfg.get('model', {})
provider = model.get('provider') or 'auto'
default = model.get('default') or model.get('model') or 'unset'
base = model.get('base_url') or ''
print(f"{provider}:{default}" + (" via " + base if base else ""))
PY
)
if [ -n "$MODEL_INFO" ]; then
    echo -e "${GREEN}$MODEL_INFO${NC}"
else
    echo -e "${YELLOW}UNKNOWN${NC}"
fi

# 5. Telegram
echo -n "  Telegram:    "
if [ -n "$(env_value TELEGRAM_BOT_TOKEN)" ]; then
    if [ -n "$(env_value TELEGRAM_ALLOWED_USERS)" ]; then
        echo -e "${GREEN}CONFIGURED${NC}"
    else
        echo -e "${YELLOW}TOKEN SET — add TELEGRAM_ALLOWED_USERS${NC}"
    fi
else
    echo -e "${YELLOW}NO BOT TOKEN — create bot with @BotFather${NC}"
fi

# 6. Memory
echo -n "  Memory seeds: "
if [ -f "$HOME/.hermes/memories/MEMORY.md" ] && [ -f "$HOME/.hermes/memories/USER.md" ]; then
    echo -e "${GREEN}SEEDED${NC}"
else
    echo -e "${RED}MISSING${NC}"
fi

echo -n "  Honcho:       "
if [ -n "$(env_value HONCHO_API_KEY)" ]; then
    echo -e "${GREEN}CONFIGURED${NC}"
else
    echo -e "${YELLOW}NO API KEY${NC}"
fi

echo -n "  Mem0:         "
if [ -n "$(env_value MEM0_API_KEY)" ]; then
    echo -e "${GREEN}CONFIGURED${NC}"
else
    echo -e "${YELLOW}NO API KEY${NC}"
fi

# 7. Identity
echo -n "  AGENTS.md:    "
if [ -f "$HOME/.config/opencode/AGENTS.md" ]; then
    echo -e "${GREEN}DEPLOYED ($(wc -l < $HOME/.config/opencode/AGENTS.md | tr -d ' ') lines)${NC}"
else
    echo -e "${RED}MISSING${NC}"
fi

echo -n "  SOUL.md:      "
if [ -f "$HOME/.hermes/SOUL.md" ]; then
    echo -e "${GREEN}DEPLOYED ($(wc -l < $HOME/.hermes/SOUL.md | tr -d ' ') lines)${NC}"
else
    echo -e "${RED}MISSING${NC}"
fi

# 8. Cron
echo -n "  Cron:         "
CRON_COUNT=$($HOME/.hermes/hermes-agent/venv/bin/hermes cron list 2>/dev/null | grep -c '\[active\]' || true)
if [ "$CRON_COUNT" -gt 0 ]; then
    echo -e "${GREEN}CONFIGURED ($CRON_COUNT job(s))${NC}"
elif grep -q "^[[:space:]]*enabled: true" "$HOME/.hermes/config.yaml" 2>/dev/null; then
    echo -e "${YELLOW}ENABLED (no jobs created yet)${NC}"
else
    echo -e "${YELLOW}NOT CONFIGURED${NC}"
fi

echo ""
echo -e "${BOLD}GitHub:${NC} https://github.com/gajendravaradhan/persistent-agentic-reasoning-automation-mesh"
