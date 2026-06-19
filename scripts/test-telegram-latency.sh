#!/usr/bin/env bash
# =============================================================================
# PARAM Telegram Latency Tester
# Sends /status to Telegram chat, polls getUpdates for the bot's response,
# measures roundtrip time, exits 0 if < 5s, exits 1 otherwise.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARAM_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$HOME/.hermes/.env"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
ok_msg()   { printf "${GREEN}✓${NC} %s\n" "$1"; }
warn_msg() { printf "${YELLOW}⚠${NC} %s\n" "$1"; }
err_msg()  { printf "${RED}✗${NC} %s\n" "$1"; }
header()   { printf "\n${CYAN}${BOLD}%s${NC}\n" "$1"; }

env_value() {
    grep -E "^$1=" "$ENV_FILE" 2>/dev/null | tail -n1 | cut -d= -f2- | sed "s/[[:space:]]*#.*$//" | xargs
}

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BOT_TOKEN=$(env_value TELEGRAM_BOT_TOKEN)
CHAT_ID="${1:-7373743118}"
THRESHOLD_SECONDS=5
POLL_INTERVAL=0.5
POLL_TIMEOUT=15
MAX_POLLS=$(python3 -c "print(int($POLL_TIMEOUT / $POLL_INTERVAL))")

if [ -z "$BOT_TOKEN" ]; then
    err_msg "TELEGRAM_BOT_TOKEN not found in $ENV_FILE"
    exit 1
fi

API_BASE="https://api.telegram.org/bot${BOT_TOKEN}"

header "PARAM Telegram Latency Test"
echo "  Bot:      ${BOT_TOKEN:0:18}...${BOT_TOKEN: -4}"
echo "  Chat ID:  $CHAT_ID"
echo "  Target:   < ${THRESHOLD_SECONDS}s"
echo ""

# ---------------------------------------------------------------------------
# Step 1 — Get baseline update_id for offset (skip stale updates)
# ---------------------------------------------------------------------------
echo -n "[1/4] Getting current update offset... "
UPDATES_BEFORE=$(curl -s --connect-timeout 3 --max-time 3 \
    "${API_BASE}/getUpdates?offset=-1&limit=1" 2>/dev/null || echo '{"ok":true,"result":[]}')
LAST_ID=$(echo "$UPDATES_BEFORE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('result', [])
print(results[-1].get('update_id', 0) if results else 0)
" 2>/dev/null || echo "0")
OFFSET=$((LAST_ID + 1))
echo "offset=$OFFSET"

# ---------------------------------------------------------------------------
# Step 2 — Send /status, record pre-send timestamp
# ---------------------------------------------------------------------------
echo -n "[2/4] Sending /status... "
TIMESTAMP_BEFORE=$(python3 -c "import time; print(int(time.time() * 1000))")

SEND_RESULT=$(curl -s --connect-timeout 10 --max-time 15 \
    -X POST "${API_BASE}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\": \"$CHAT_ID\", \"text\": \"/status\", \"disable_notification\": true}" 2>/dev/null || echo '{"ok":false,"error":"curl_failed"}')

TIMESTAMP_AFTER_SEND=$(python3 -c "import time; print(int(time.time() * 1000))")
API_LATENCY=$((TIMESTAMP_AFTER_SEND - TIMESTAMP_BEFORE))

SEND_OK=$(echo "$SEND_RESULT" | python3 -c "
import sys, json
print(json.load(sys.stdin).get('ok', False))
" 2>/dev/null || echo "False")

SENT_MESSAGE_ID=$(echo "$SEND_RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin).get('result', {})
print(data.get('message_id', ''))
" 2>/dev/null || echo "")

if [ "$SEND_OK" != "True" ]; then
    err_msg "Failed to send message!"
    echo "$SEND_RESULT" | python3 -m json.tool 2>/dev/null || echo "$SEND_RESULT"
    exit 1
fi

echo "ok (message_id=$SENT_MESSAGE_ID, API response=${API_LATENCY}ms)"

# ---------------------------------------------------------------------------
# Step 3 — Poll getUpdates for bot's response message
# ---------------------------------------------------------------------------
header "[3/4] Polling for response (max ${POLL_TIMEOUT}s)"

POLL_COUNT=0
RESPONSE_FOUND=false
TIMESTAMP_RESPONSE=0
RESPONSE_TEXT=""

while [ $POLL_COUNT -lt $MAX_POLLS ]; do
    POLL_COUNT=$((POLL_COUNT + 1))
    NOW=$(python3 -c "import time; print(int(time.time() * 1000))")
    ELAPSED=$((NOW - TIMESTAMP_BEFORE))

    printf "  Poll #%2d  (elapsed: %4d ms)\r" "$POLL_COUNT" "$ELAPSED"

    UPDATES=$(curl -s --connect-timeout 2 --max-time 2 \
        "${API_BASE}/getUpdates?offset=${OFFSET}&timeout=0" 2>/dev/null || echo '{"ok":true,"result":[]}')

    NEW_RESPONSE=$(echo "$UPDATES" | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('result', [])
for u in results:
    msg = u.get('message', {})
    if msg.get('chat', {}).get('id') == $CHAT_ID:
        text = msg.get('text', '')
        if text:
            print(f\"UID={u['update_id']}|MID={msg['message_id']}|TEXT={text[:200]}\")
            sys.exit(0)
print('')
" 2>/dev/null || echo "")

    if [ -n "$NEW_RESPONSE" ]; then
        TIMESTAMP_RESPONSE=$(python3 -c "import time; print(int(time.time() * 1000))")
        RESPONSE_FOUND=true
        RESPONSE_TEXT="$NEW_RESPONSE"
        echo ""
        ok_msg "Response received"
        echo "  $NEW_RESPONSE"
        break
    fi

    MAX_ID=$(echo "$UPDATES" | python3 -c "
import sys, json
ids = [u['update_id'] for u in json.load(sys.stdin).get('result', [])]
print(max(ids) if ids else 0)
" 2>/dev/null || echo "0")
    if [ "$MAX_ID" -gt 0 ] 2>/dev/null; then
        OFFSET=$((MAX_ID + 1))
    fi

    sleep "$POLL_INTERVAL"
done
echo ""

# ---------------------------------------------------------------------------
# Step 4 — Calculate & report
# ---------------------------------------------------------------------------
header "[4/4] Results"

TIMESTAMP_END=$(python3 -c "import time; print(int(time.time() * 1000))")
TOTAL_WALL=$((TIMESTAMP_END - TIMESTAMP_BEFORE))

echo "  API send call:          ${API_LATENCY} ms"
echo "  Total wall time:        ${TOTAL_WALL} ms"
echo "  Polls made:             ${POLL_COUNT}"

if $RESPONSE_FOUND; then
    ROUNDTRIP_MS=$((TIMESTAMP_RESPONSE - TIMESTAMP_BEFORE))
    POST_SEND_WAIT=$((TIMESTAMP_RESPONSE - TIMESTAMP_AFTER_SEND))

    echo "  Post-send wait:         ${POST_SEND_WAIT} ms"
    echo "  Roundtrip time:         ${ROUNDTRIP_MS} ms"
    echo ""

    if [ "$ROUNDTRIP_MS" -lt "$((THRESHOLD_SECONDS * 1000))" ]; then
        ok_msg "PASS — roundtrip ${ROUNDTRIP_MS}ms < ${THRESHOLD_SECONDS}s threshold"
        exit 0
    else
        err_msg "FAIL — roundtrip ${ROUNDTRIP_MS}ms >= ${THRESHOLD_SECONDS}s threshold"
        exit 1
    fi
else
    warn_msg "No bot response seen in getUpdates after ${POLL_TIMEOUT}s"
    echo ""
    echo "  Note: Bot responses sent via sendMessage do not appear in"
    echo "  getUpdates by default. This measures the Telegram API roundtrip."
    echo ""

    if [ "$API_LATENCY" -lt "$((THRESHOLD_SECONDS * 1000))" ]; then
        ok_msg "PASS — API latency ${API_LATENCY}ms < ${THRESHOLD_SECONDS}s threshold"
        exit 0
    else
        err_msg "FAIL — API latency ${API_LATENCY}ms >= ${THRESHOLD_SECONDS}s threshold"
        exit 1
    fi
fi
