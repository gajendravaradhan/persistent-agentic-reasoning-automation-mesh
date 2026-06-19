#!/usr/bin/env bash
# PARAM Telegram latency test — verifies roundtrip < 5 seconds
set -euo pipefail

TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.hermes/.env 2>/dev/null | head -1 | cut -d= -f2- | tr -d ' ')
CHAT_ID="${TELEGRAM_TEST_CHAT:-7373743118}"
MAX_WAIT=30
TIMEOUT=5

if [ -z "$TOKEN" ]; then
    echo "FAIL: TELEGRAM_BOT_TOKEN not found in ~/.hermes/.env"
    exit 1
fi

# Record pre-send timestamp (nanoseconds)
START_NS=$(date +%s%N 2>/dev/null || perl -MTime::HiRes -e 'print int(Time::HiRes::time()*1e9)' 2>/dev/null || echo 0)
START_S=$(date +%s)

# Send /status command
SEND_RESULT=$(curl -s --connect-timeout 10 -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\": \"$CHAT_ID\", \"text\": \"/status\"}" 2>&1)

SEND_OK=$(echo "$SEND_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok',False))" 2>/dev/null || echo "False")

if [ "$SEND_OK" != "True" ]; then
    echo "FAIL: Could not send /status — $SEND_RESULT"
    exit 1
fi

SEND_MSG_ID=$(echo "$SEND_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['message_id'])" 2>/dev/null)
echo "Sent /status (msg_id=$SEND_MSG_ID)"

# Poll for bot response (Hermes should reply with status)
OFFSET=0
FOUND=0
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    UPDATES=$(curl -s --connect-timeout 10 "https://api.telegram.org/bot${TOKEN}/getUpdates?offset=${OFFSET}&timeout=5" 2>&1)
    
    # Check if our sent message has been processed and a reply exists
    REPLY=$(echo "$UPDATES" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for u in data.get('result', []):
    msg = u.get('message', {})
    if msg.get('text','').startswith('PARAM Status') or msg.get('text','').startswith('Gateway'):
        print(msg.get('text','')[:100])
        sys.exit(0)
print('')
" 2>/dev/null)
    
    if [ -n "$REPLY" ]; then
        FOUND=1
        break
    fi
    
    # Update offset to avoid re-processing
    MAX_ID=$(echo "$UPDATES" | python3 -c "import sys,json; ids=[u['update_id'] for u in json.load(sys.stdin).get('result',[])]; print(max(ids) if ids else 0)" 2>/dev/null)
    if [ "$MAX_ID" -gt 0 ] 2>/dev/null; then
        OFFSET=$((MAX_ID + 1))
    fi
    
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

if [ $FOUND -eq 0 ]; then
    echo "FAIL: No response received within ${MAX_WAIT}s"
    exit 1
fi

# Calculate elapsed time
END_S=$(date +%s)
ROUNDTRIP=$((END_S - START_S))

echo "Roundtrip: ${ROUNDTRIP}s"
echo "Response: $REPLY"

if [ $ROUNDTRIP -le $TIMEOUT ]; then
    echo "PASS: Latency ${ROUNDTRIP}s <= ${TIMEOUT}s"
    exit 0
else
    echo "FAIL: Latency ${ROUNDTRIP}s > ${TIMEOUT}s"
    exit 1
fi
