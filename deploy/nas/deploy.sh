#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_SRC="$HOME/.hermes"
DATA_DIR="$SCRIPT_DIR/hermes-data"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

header()  { printf "\n${BOLD}%s${NC}\n" "$1"; }
ok()     { printf "  ${GREEN}✓${NC} %s\n" "$1"; }
warn()   { printf "  ${YELLOW}⚠${NC} %s\n" "$1"; }
err()    { printf "  ${RED}✗${NC} %s\n" "$1"; }

usage() {
    cat <<'EOF'
Usage: ./deploy.sh <command>

Commands:
  prepare    Copy Hermes config/state from ~/.hermes to ./hermes-data/
  start      Pull image and start containers
  stop       Stop containers
  logs       Tail gateway logs
  status     Show container status
  shell      Open shell in gateway container
  restart    Restart containers

Environment:
  HERMES_UID  Host user UID for file ownership (default: 1000)
  HERMES_GID  Host group GID for file ownership (default: 1000)

First run:
  1. ./deploy.sh prepare
  2. Edit ./hermes-data/.env with your API keys
  3. ./deploy.sh start
EOF
}

cmd_prepare() {
    header "Preparing Hermes data directory"

    if [ ! -d "$HERMES_SRC" ]; then
        err "Hermes not found at $HERMES_SRC"
        err "Install Hermes first: https://github.com/NousResearch/hermes-agent"
        exit 1
    fi

    mkdir -p "$DATA_DIR"/{logs,sessions,cron,memories,skills,plugins,output}

    local files=(
        "config.yaml"
        ".env"
    )

    local copied=0 skipped=0
    for f in "${files[@]}"; do
        if [ -f "$HERMES_SRC/$f" ]; then
            cp "$HERMES_SRC/$f" "$DATA_DIR/$f"
            ok "Copied $f"
            ((copied++))
        else
            warn "Skipped $f (not found)"
            ((skipped++))
        fi
    done

    local dirs=("memories" "sessions" "cron" "skills" "plugins")
    for d in "${dirs[@]}"; do
        if [ -d "$HERMES_SRC/$d" ] && [ "$(ls -A "$HERMES_SRC/$d" 2>/dev/null)" ]; then
            cp -r "$HERMES_SRC/$d/"* "$DATA_DIR/$d/" 2>/dev/null || true
            ok "Copied $d/"
            ((copied++))
        else
            warn "Skipped $d/ (empty or not found)"
            ((skipped++))
        fi
    done

    chmod 600 "$DATA_DIR/.env" 2>/dev/null || true

    header "Prepare complete"
    printf "  Copied: %d  Skipped: %d\n" "$copied" "$skipped"
    echo ""
    echo "  Next: Edit $DATA_DIR/.env with your API keys"
    echo "        Then: ./deploy.sh start"
}

cmd_start() {
    header "Starting PARAM on NAS"

    if [ ! -f "$DATA_DIR/.env" ]; then
        err ".env not found in $DATA_DIR"
        err "Run './deploy.sh prepare' first, then edit .env"
        exit 1
    fi

    if ! grep -q "TELEGRAM_BOT_TOKEN=" "$DATA_DIR/.env" 2>/dev/null || \
       grep -q "TELEGRAM_BOT_TOKEN=$" "$DATA_DIR/.env" 2>/dev/null; then
        err "TELEGRAM_BOT_TOKEN not set in $DATA_DIR/.env"
        exit 1
    fi

    cd "$SCRIPT_DIR"
    export HERMES_UID="${HERMES_UID:-$(id -u)}"
    export HERMES_GID="${HERMES_GID:-$(id -g)}"

    docker compose pull
    docker compose up -d

    sleep 3
    cmd_status
}

cmd_stop() {
    header "Stopping PARAM"
    cd "$SCRIPT_DIR"
    docker compose down
    ok "Containers stopped"
}

cmd_logs() {
    cd "$SCRIPT_DIR"
    docker compose logs -f --tail=50 gateway
}

cmd_status() {
    header "PARAM Container Status"
    cd "$SCRIPT_DIR"
    docker compose ps

    echo ""
    if docker compose exec -T gateway hermes cron status 2>/dev/null; then
        ok "Gateway responding"
    else
        warn "Gateway may still be starting — check logs: ./deploy.sh logs"
    fi
}

cmd_shell() {
    cd "$SCRIPT_DIR"
    docker compose exec gateway bash
}

cmd_restart() {
    cmd_stop
    sleep 2
    cmd_start
}

case "${1:-}" in
    prepare) cmd_prepare ;;
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    logs)    cmd_logs ;;
    status)  cmd_status ;;
    shell)   cmd_shell ;;
    restart) cmd_restart ;;
    *)       usage; exit 1 ;;
esac
