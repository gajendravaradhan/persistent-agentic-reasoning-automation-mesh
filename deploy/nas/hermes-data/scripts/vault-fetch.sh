#!/usr/bin/env bash
# vault-fetch.sh — PARAM runtime secret retrieval from Vaultwarden
# Usage: vault-fetch.sh <secret-name>
# Returns the secret value on stdout, empty string on failure.
#
# Architecture: Vaultwarden is the encrypted store. This script
# authenticates via the API using BW_CLIENTID/BW_CLIENTSECRET (from .env),
# retrieves the named item, and prints its password field.
# Hermes cron agents call this to fetch API keys without reading .env directly.

set -euo pipefail

SECRET_NAME="${1:-}"
VAULT_URL="${VAULTWARDEN_URL:-http://param-vaultwarden:8311}"
BW_CLIENT_ID="${BW_CLIENTID:-}"
BW_CLIENT_SECRET="${BW_CLIENTSECRET:-}"

if [ -z "$SECRET_NAME" ]; then
    echo "[vault-fetch] ERROR: secret name required" >&2
    exit 1
fi

if [ -z "$BW_CLIENT_ID" ] || [ -z "$BW_CLIENT_SECRET" ]; then
    echo "[vault-fetch] WARNING: BW_CLIENTID/BW_CLIENTSECRET not set — falling back to .env" >&2
    exit 1
fi

TOKEN=$(curl -sf \
    -X POST "${VAULT_URL}/identity/connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials&client_id=${BW_CLIENT_ID}&client_secret=${BW_CLIENT_SECRET}&scope=api" \
    2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "[vault-fetch] ERROR: authentication failed" >&2
    exit 1
fi

VALUE=$(curl -sf \
    -H "Authorization: Bearer ${TOKEN}" \
    "${VAULT_URL}/api/objects/item?search=${SECRET_NAME}" \
    2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    items = d.get('Data', {}).get('Data', [])
    if items:
        print(items[0].get('Login', {}).get('Password', ''))
except Exception:
    pass
" 2>/dev/null)

if [ -z "$VALUE" ]; then
    echo "[vault-fetch] WARNING: secret '${SECRET_NAME}' not found in vault" >&2
    exit 1
fi

printf '%s' "$VALUE"
