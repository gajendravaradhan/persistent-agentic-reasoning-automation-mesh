#!/usr/bin/env bash
# PARAM WhatsApp Pairing — one-command setup
# Usage: ./param-whatsapp-pair.sh <your-phone-number>
# Example: ./param-whatsapp-pair.sh 15551234567

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PHONE="${1:-}"

if [ -z "$PHONE" ]; then
    echo -e "${YELLOW}Usage: $0 <your-phone-number>${NC}"
    echo "Example: $0 15551234567"
    echo ""
    echo "Enter your WhatsApp phone number (country code + number, no spaces or +):"
    read -r PHONE
    if [ -z "$PHONE" ]; then
        echo -e "${RED}No phone number provided. Exiting.${NC}"
        exit 1
    fi
fi

HERMES_VENV="$HOME/.hermes/hermes-agent/venv/bin/python"
HERMES_CLI="$HOME/.hermes/hermes-agent/hermes_cli/main.py"

if [ ! -f "$HERMES_VENV" ]; then
    echo -e "${RED}Hermes not found. Install first.${NC}"
    exit 1
fi

echo -e "${GREEN}Starting WhatsApp pairing for: $PHONE${NC}"
echo ""

expect -c "
set timeout 60
spawn $HERMES_VENV $HERMES_CLI whatsapp
expect {
    \"Choose *1/2*:\" {
        send \"2\r\"
        exp_continue
    }
    \"Your phone number\" {
        send \"$PHONE\r\"
        exp_continue
    }
    \"QR\" {
        # Let QR display for user to scan
        set timeout 120
        expect {
            \"paired\" { puts \"\nPAIRED_SUCCESSFULLY\" }
            timeout { puts \"\nTIMEOUT — did you scan the QR code?\" }
        }
    }
    timeout {
        puts \"\nTIMEOUT\"
    }
    eof {
        puts \"\nCOMPLETE\"
    }
}
"

echo ""
echo -e "${GREEN}If QR appeared, scan it with WhatsApp:${NC}"
echo "  Settings → Linked Devices → Link a Device → Scan QR"
echo ""
echo -e "${YELLOW}Pairing complete. WhatsApp now active for PARAM.${NC}"