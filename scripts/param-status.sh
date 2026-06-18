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

# 3. TokenEye
echo -n "  TokenEye:     "
if curl -s http://127.0.0.1:8787/__health > /dev/null 2>&1; then
    RECORDS=$(curl -s http://127.0.0.1:8787/__health | python3 -c "import sys,json; print(json.load(sys.stdin)['recordCount'])" 2>/dev/null)
    echo -e "${GREEN}RUNNING ($RECORDS records)${NC}"
else
    echo -e "${RED}DOWN${NC}"
fi

# 4. WhatsApp
echo -n "  WhatsApp:     "
if [ -f "$HOME/.hermes/platforms/whatsapp/session/creds.json" ]; then
    echo -e "${GREEN}PAIRED${NC}"
else
    echo -e "${YELLOW}NOT PAIRED — run: python ~/.hermes/hermes-agent/hermes_cli/main.py whatsapp${NC}"
fi

# 5. Memory
echo -n "  Memory seeds: "
if [ -f "$HOME/.hermes/memories/MEMORY.md" ] && [ -f "$HOME/.hermes/memories/USER.md" ]; then
    echo -e "${GREEN}SEEDED${NC}"
else
    echo -e "${RED}MISSING${NC}"
fi

echo -n "  Honcho:       "
if grep -q "HONCHO_API_KEY=" "$HOME/.hermes/.env" 2>/dev/null && ! grep -q "^#.*HONCHO_API_KEY" "$HOME/.hermes/.env" 2>/dev/null; then
    echo -e "${GREEN}CONFIGURED${NC}"
else
    echo -e "${YELLOW}NO API KEY${NC}"
fi

echo -n "  Mem0:         "
if grep -q "MEM0_API_KEY=" "$HOME/.hermes/.env" 2>/dev/null && ! grep -q "^#.*MEM0_API_KEY" "$HOME/.hermes/.env" 2>/dev/null; then
    echo -e "${GREEN}CONFIGURED${NC}"
else
    echo -e "${YELLOW}NO API KEY${NC}"
fi

# 6. Identity
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

# 7. Cron
echo -n "  Cron:         "
if grep -q "enabled: true" "$HOME/.hermes/config.yaml" 2>/dev/null; then
    echo -e "${YELLOW}CONFIGURED (no jobs enabled yet)${NC}"
else
    echo -e "${YELLOW}NOT CONFIGURED${NC}"
fi

echo ""
echo -e "${BOLD}GitHub:${NC} https://github.com/gajendravaradhan/persistent-agentic-reasoning-automation-mesh"