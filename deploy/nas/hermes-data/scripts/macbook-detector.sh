#!/usr/bin/env bash
# macbook-detector.sh — MacBook presence probe for PARAM dispatcher
# no_agent=true, runs every 5 min. Emits ONE LINE only on status change.
# State: /opt/data/state/macbook-state.json

STATE="/opt/data/state/macbook-state.json"
SSH_OPTS="-o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

mkdir -p "$(dirname "$STATE")"

prev_online="false"
if [ -f "$STATE" ]; then
    prev_online=$(python3 -c "
import json,sys
try:
    d=json.load(open('$STATE'))
    print('true' if d.get('online') else 'false')
except Exception:
    print('false')
" 2>/dev/null || echo "false")
fi

now_online="false"
detected_via=""

if ssh $SSH_OPTS gajendra.local 'echo online' 2>/dev/null | grep -q online; then
    now_online="true"
    detected_via="gajendra.local"
fi

if [ "$now_online" = "false" ]; then
    last_ip=$(python3 -c "
import json
try:
    d=json.load(open('$STATE'))
    print(d.get('last_ip',''))
except Exception:
    print('')
" 2>/dev/null || echo "")
    if [ -n "$last_ip" ] && [ "$last_ip" != "gajendra.local" ]; then
        if ssh -o ConnectTimeout=2 -o BatchMode=yes -o StrictHostKeyChecking=no \
               -o UserKnownHostsFile=/dev/null \
               "$last_ip" 'echo online' 2>/dev/null | grep -q online; then
            now_online="true"
            detected_via="$last_ip"
        fi
    fi
fi

if [ "$now_online" = "false" ]; then
    for i in $(seq 1 20); do
        candidate="192.168.1.$i"
        if ssh -o ConnectTimeout=1 -o BatchMode=yes -o StrictHostKeyChecking=no \
               -o UserKnownHostsFile=/dev/null \
               "$candidate" 'echo online' 2>/dev/null | grep -q online; then
            now_online="true"
            detected_via="$candidate"
            break
        fi
    done
fi

ts=$(date -Iseconds 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ")

python3 - <<PYEOF
import json
try:
    d = json.load(open("$STATE"))
except Exception:
    d = {}
d["online"] = ("$now_online" == "true")
d["last_check"] = "$ts"
if "$now_online" == "true":
    d["last_seen"] = "$ts"
    d["last_ip"] = "$detected_via"
elif "last_seen" not in d:
    d["last_seen"] = None
json.dump(d, open("$STATE", "w"))
PYEOF

if [ "$now_online" != "$prev_online" ]; then
    if [ "$now_online" = "true" ]; then
        echo "MacBook ONLINE (${detected_via}) at ${ts} — MACBOOK_REQUIRED tasks can now be dispatched."
    else
        echo "MacBook OFFLINE at ${ts} — queuing MACBOOK_REQUIRED tasks for next availability window."
    fi
fi
