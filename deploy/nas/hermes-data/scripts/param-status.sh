#!/usr/bin/env bash
# PARAM Status Checker — container-aware version (Docker on NAS)
# Uses /opt/data/ instead of ~/.hermes/ for container compatibility

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BOLD}PARAM Status Dashboard${NC}"
echo "======================"

# 1. Hermes Gateway
echo -n "  Gateway:      "
if ps aux 2>/dev/null | grep -q "[h]ermes gateway run"; then
    echo -e "${GREEN}RUNNING${NC}"
else
    echo -e "${RED}DOWN${NC}"
fi

# 2. Dashboard
echo -n "  Dashboard:    "
if curl -s http://localhost:9119/ > /dev/null 2>&1; then
    echo -e "${GREEN}RUNNING${NC}"
else
    echo -e "${RED}DOWN${NC}"
fi

# 3. TokenEye
echo -n "  TokenEye:     "
if curl -s http://127.0.0.1:8787/__health > /dev/null 2>&1; then
    RECORDS=$(curl -s http://127.0.0.1:8787/__health | python3 -c "import sys,json; print(json.load(sys.stdin)['recordCount'])" 2>/dev/null)
    echo -e "${GREEN}RUNNING ($RECORDS records)${NC}"
else
    echo -e "${RED}DOWN${NC}"
fi

# 4. Telegram
echo -n "  Telegram:     "
if grep -q "telegram connected" /opt/data/logs/agent.log 2>/dev/null; then
    echo -e "${GREEN}CONNECTED${NC}"
else
    echo -e "${YELLOW}DISCONNECTED${NC}"
fi

# 5. Cron
echo -n "  Cron:         "
if grep -q "Cron ticker started" /opt/data/logs/agent.log 2>/dev/null; then
    echo -e "${GREEN}ACTIVE${NC}"
else
    echo -e "${YELLOW}NOT RUNNING${NC}"
fi

# 6. Kanban
echo -n "  Kanban:       "
if grep -q "kanban dispatcher" /opt/data/logs/agent.log 2>/dev/null; then
    echo -e "${GREEN}ACTIVE${NC}"
else
    echo -e "${YELLOW}NOT RUNNING${NC}"
fi

# 7. Vault
echo -n "  Vault:        "
if [ -d /workspace/vault ]; then
    DIRS=$(ls -d /workspace/vault/*/ 2>/dev/null | wc -l)
    echo -e "${GREEN}MOUNTED ($DIRS dirs)${NC}"
else
    echo -e "${RED}NOT MOUNTED${NC}"
fi

# 8. Cloudflare tunnel
echo -n "  Tunnel:       "
if ps aux 2>/dev/null | grep -q "[c]loudflared tunnel run param"; then
    echo -e "${GREEN}RUNNING${NC}"
else
    echo -e "${YELLOW}DOWN${NC}"
fi

echo ""
echo -e "${BOLD}GitHub:${NC} https://github.com/gajendravaradhan/persistent-agentic-reasoning-automation-mesh"
