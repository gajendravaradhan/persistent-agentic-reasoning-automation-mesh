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
echo -ne "  TokenEye:     "
TOK_EYE_DB="/home/Nasama-Pochu/param/tokeneye-config/metrics.db"
if curl -s http://127.0.0.1:8787/__health > /dev/null 2>&1; then
    TODAY=$(date +%Y-%m-%d)
    HEALTH_JSON=$(curl -s http://127.0.0.1:8787/__health)
    RECORD_COUNT=$(echo "$HEALTH_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['recordCount'])" 2>/dev/null)
    ACTIVE=$(echo "$HEALTH_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(','.join([p for p,v in d.get('providers',{}).items() if v.get('keyCount',0)>0 or v.get('mode')=='passthrough']))" 2>/dev/null)
    echo -e "${GREEN}RUNNING${NC}   (${RECORD_COUNT:-?} total records, active: ${ACTIVE:-auto})"
    if [ -f "$TOK_EYE_DB" ] && command -v sqlite3 >/dev/null 2>&1; then
        CALLS=$(sqlite3 "$TOK_EYE_DB" "SELECT COUNT(*) FROM metrics WHERE date(timestamp)='$TODAY' AND status=200" 2>/dev/null)
        TOKENS=$(sqlite3 "$TOK_EYE_DB" "SELECT ROUND(SUM(total_tokens)) FROM metrics WHERE date(timestamp)='$TODAY' AND status=200" 2>/dev/null)
        AVG_MS=$(sqlite3 "$TOK_EYE_DB" "SELECT ROUND(AVG(latency_ms)) FROM metrics WHERE date(timestamp)='$TODAY' AND status=200" 2>/dev/null)
        COST=$(sqlite3 "$TOK_EYE_DB" "SELECT ROUND(SUM(COALESCE(estimated_cost,0)), 4) FROM metrics WHERE date(timestamp)='$TODAY'" 2>/dev/null)
        ERRORS=$(sqlite3 "$TOK_EYE_DB" "SELECT COUNT(*) FROM metrics WHERE date(timestamp)='$TODAY' AND status!=200" 2>/dev/null)
        printf "    └─ Today: %s calls, %s tokens, %s ms avg" "${CALLS:-0}" "${TOKENS:-0}" "${AVG_MS:-0}"
        if [ "$COST" != "0.0" ] && [ -n "$COST" ]; then
            printf ", \$%s cost" "$COST"
        fi
        echo ""
        if [ "${ERRORS:-0}" != "0" ]; then
            echo -e "       ${RED}Errors: $ERRORS${NC}"
        fi
        MODELS=$(sqlite3 "$TOK_EYE_DB" "SELECT model || '(' || COUNT(*) || ')' FROM metrics WHERE date(timestamp)='$TODAY' AND status=200 GROUP BY model" 2>/dev/null | tr '\n' ' ')
        if [ -n "$MODELS" ]; then
            echo "       Models: $MODELS"
        fi
    fi
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

# 7. Memory (Honcho)
echo -n "  Honcho:       "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}HEALTHY${NC}"
else
    echo -e "${RED}DOWN${NC}"
fi

# 8. Hindsight
echo -n "  Hindsight:    "
if [ -f /opt/data/hindsight/config.json ]; then
    echo -e "${GREEN}CONFIGURED${NC}"
else
    echo -e "${YELLOW}NOT CONFIGURED${NC}"
fi

# 9. Vault
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
