#!/usr/bin/env bash
# cloudflared-watchdog.sh — verifies the PARAM tunnel is reachable
# Called by Hermes cron every 5 minutes (no_agent mode).
#
# Architecture: cloudflared runs in param-cloudflared container (separate from this param container).
# pgrep/pkill cannot see it. The only correct health check is an external reachability probe.
# Docker restart policy (unless-stopped) handles container recovery automatically.
# This script's job: detect tunnel degradation and emit a non-zero exit so Hermes cron surfaces it.

TUNNEL_URL="https://param.aiforges.app/"
LOG="/tmp/cloudflared-watchdog.log"

HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "$TUNNEL_URL" --max-time 10 2>/dev/null)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
    exit 0
fi

echo "$(date): Tunnel unreachable — param.aiforges.app returned ${HTTP_CODE:-timeout}" >> "$LOG"
echo "TUNNEL_DOWN: param.aiforges.app returned ${HTTP_CODE:-timeout} at $(date)"
exit 1
