#!/usr/bin/env bash
# PARAM Auto-Heal — restart unhealthy containers
# Run as cron: */5 * * * * /opt/data/scripts/autoheal.sh
PREFIX="param-"
unhealthy=$(docker ps --filter "name=$PREFIX" --filter "health=unhealthy" --format '{{.Names}}' 2>/dev/null)
if [ -n "$unhealthy" ]; then
    for c in $unhealthy; do
        echo "[$(date -Iseconds)] Restarting unhealthy: $c"
        docker restart "$c"
    done
fi
