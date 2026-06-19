#!/usr/bin/env bash
# cloudflared-watchdog.sh — keeps the PARAM tunnel alive
# Called by Hermes cron every 5 minutes (no_agent mode).

LOG="/tmp/cloudflared-watchdog.log"
TUNNEL_LOG="/tmp/cloudflared-param.log"
CLOUDFLARED="$HOME/.local/bin/cloudflared"

if pgrep -f "cloudflared tunnel run param" > /dev/null 2>&1; then
    # Tunnel is running — check if it's healthy (has active connections)
    if grep -q "Registered tunnel connection" "$TUNNEL_LOG" 2>/dev/null; then
        exit 0  # Healthy, nothing to do
    fi
fi

# Tunnel not running or unhealthy — restart
echo "$(date): Tunnel down or unhealthy. Restarting..." >> "$LOG"
pkill -f "cloudflared tunnel run param" 2>/dev/null
sleep 2
nohup "$CLOUDFLARED" tunnel run param > "$TUNNEL_LOG" 2>&1 &
echo "$(date): Restarted with PID $!" >> "$LOG"
