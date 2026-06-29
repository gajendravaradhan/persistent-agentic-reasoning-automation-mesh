#!/usr/bin/env bash
# Non-interactive Cloudflare Tunnel setup for PARAM on NAS.
# Assumes: cloudflared installed, Cloudflare domain *.aiforges.app managed.
# Usage:   bash cloudflared-setup-noninteractive.sh
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TUNNEL_NAME="param"
DOMAIN="aiforges.app"
CONFIG_DIR="$HOME/.cloudflared"

ok()  { printf "  ${GREEN}✓${NC} %s\n" "$1"; }
err() { printf "  ${RED}✗${NC} %s\n" "$1"; exit 1; }

echo ""
echo -e "${BOLD}PARAM Cloudflare Tunnel Setup${NC}"
echo "Domain: *.${DOMAIN}"
echo "Tunnel: ${TUNNEL_NAME}"
echo ""

if ! command -v cloudflared &>/dev/null; then
    echo "Installing cloudflared..."
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
    chmod +x /tmp/cloudflared
    sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
    ok "cloudflared installed"
fi

ok "cloudflared: $(cloudflared --version 2>&1 | head -1)"

mkdir -p "$CONFIG_DIR"

if ! cloudflared tunnel list 2>/dev/null | grep -q "$TUNNEL_NAME"; then
    cloudflared tunnel create "$TUNNEL_NAME"
    ok "Tunnel created: $TUNNEL_NAME"
else
    ok "Tunnel already exists: $TUNNEL_NAME"
fi

CRED_FILE="$CONFIG_DIR/${TUNNEL_NAME}.json"
if [ ! -f "$CRED_FILE" ]; then
    cloudflared tunnel token "$TUNNEL_NAME" > /dev/null 2>&1 || true
fi

cp "$SCRIPT_DIR/configs/cloudflared-config.yml" "$CONFIG_DIR/config.yml"
ok "Config deployed to $CONFIG_DIR/config.yml"

echo ""
echo "Setting up DNS routes..."
for HOSTNAME in "param" "vault" "tokeneye"; do
    FQDN="${HOSTNAME}.${DOMAIN}"
    cloudflared tunnel route dns "$TUNNEL_NAME" "$FQDN" 2>/dev/null && \
        ok "DNS route: $FQDN" || \
        ok "DNS route exists: $FQDN (or needs manual Cloudflare setup)"
done

if command -v systemctl &>/dev/null; then
    sudo cloudflared service install 2>/dev/null && \
        ok "systemd service installed (auto-start on boot)" || \
        ok "Service may already be installed"
else
    echo ""
    echo "No systemd detected. Add to crontab or init script:"
    echo "  @reboot cloudflared tunnel run $TUNNEL_NAME"
fi

echo ""
echo -e "${BOLD}Done.${NC} Tunnel will start on next boot or run manually:"
echo "  cloudflared tunnel run $TUNNEL_NAME"
echo ""
echo "Access points:"
echo "  Dashboard:  https://param.${DOMAIN}"
echo "  Vault:      https://vault.${DOMAIN}"
echo "  TokenEye:   https://tokeneye.${DOMAIN}"
