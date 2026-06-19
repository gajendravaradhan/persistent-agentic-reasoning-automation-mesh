#!/usr/bin/env bash
# Cloudflare Tunnel setup for PARAM dashboard remote access.
# The tunnel creates a secure outbound connection from NAS to Cloudflare,
# so no inbound ports or router config needed.
#
# Prerequisites:
#   - Cloudflare account (free tier works)
#   - A domain managed by Cloudflare (or use trycloudflare.com for testing)
#   - cloudflared installed on NAS
#
# Install cloudflared on NAS (Linux):
#   curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
#   chmod +x /usr/local/bin/cloudflared

set -euo pipefail

GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

header() { printf "\n${BOLD}%s${NC}\n" "$1"; }
ok()    { printf "  ${GREEN}✓${NC} %s\n" "$1"; }

header "Cloudflare Tunnel Setup for PARAM Dashboard"

if ! command -v cloudflared &>/dev/null; then
    echo "cloudflared not found. Install it first:"
    echo "  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared"
    echo "  chmod +x /usr/local/bin/cloudflared"
    exit 1
fi

ok "cloudflared found: $(cloudflared --version 2>&1 | head -1)"

echo ""
echo "Choose setup mode:"
echo "  1) Quick test — temporary tunnel (trycloudflare.com, lasts until process dies)"
echo "  2) Permanent — named tunnel with your Cloudflare domain"
echo ""
read -rp "Choice [1/2]: " MODE

if [ "$MODE" = "1" ]; then
    header "Starting temporary tunnel"
    echo "Dashboard will be available at a random trycloudflare.com URL."
    echo "Press Ctrl+C to stop."
    echo ""
    cloudflared tunnel --url http://localhost:9119
elif [ "$MODE" = "2" ]; then
    header "Setting up permanent tunnel"

    read -rp "Tunnel name [param-dashboard]: " TUNNEL_NAME
    TUNNEL_NAME="${TUNNEL_NAME:-param-dashboard}"

    read -rp "Domain/subdomain for dashboard [param.yourdomain.com]: " DASHBOARD_DOMAIN
    DASHBOARD_DOMAIN="${DASHBOARD_DOMAIN:-param.yourdomain.com}"

    cloudflared tunnel create "$TUNNEL_NAME"
    ok "Tunnel created: $TUNNEL_NAME"

    CONFIG_DIR="$HOME/.cloudflared"
    mkdir -p "$CONFIG_DIR"

    cat > "$CONFIG_DIR/config.yml" <<YAML
tunnel: ${TUNNEL_NAME}
credentials-file: ${CONFIG_DIR}/${TUNNEL_NAME}.json

ingress:
  - hostname: ${DASHBOARD_DOMAIN}
    service: http://localhost:9119
  - service: http_status:404
YAML

    ok "Config written to $CONFIG_DIR/config.yml"

    cloudflared tunnel route dns "$TUNNEL_NAME" "$DASHBOARD_DOMAIN"
    ok "DNS route created: $DASHBOARD_DOMAIN → tunnel"

    echo ""
    echo "To install as a systemd service (auto-start on boot):"
    echo "  sudo cloudflared service install"
    echo ""
    echo "To run manually now:"
    echo "  cloudflared tunnel run $TUNNEL_NAME"

    read -rp "Install as systemd service now? [y/N]: " INSTALL_SVC
    if [ "${INSTALL_SVC,,}" = "y" ]; then
        sudo cloudflared service install
        ok "cloudflared service installed"
    fi
fi
