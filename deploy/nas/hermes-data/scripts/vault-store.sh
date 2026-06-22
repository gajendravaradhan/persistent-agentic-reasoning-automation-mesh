#!/usr/bin/env bash
# vault-store.sh — Store .env secrets into Vaultwarden vault
# Usage: vault-store.sh [env-file-path]
set -uo pipefail

VAULT_URL="${VAULTWARDEN_URL:-http://localhost:8311}"
if ! curl -sf -o /dev/null "${VAULT_URL}/" 2>/dev/null; then
    VAULT_URL="http://param-vaultwarden:8311"
fi
BW_CLIENT_ID="${BW_CLIENTID:-}"
BW_CLIENT_SECRET="${BW_CLIENTSECRET:-}"
ENV_FILE="${1:-/opt/data/.env}"

if [ -z "$BW_CLIENT_ID" ] || [ -z "$BW_CLIENT_SECRET" ]; then
    echo "[vault-store] ERROR: BW_CLIENTID/BW_CLIENTSECRET not set"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "[vault-store] ERROR: .env file not found at $ENV_FILE"
    exit 1
fi

TOKEN=$(curl -s \
    -X POST "${VAULT_URL}/identity/connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials&client_id=${BW_CLIENT_ID}&client_secret=${BW_CLIENT_SECRET}&scope=api&deviceIdentifier=param-vault-store&deviceName=param-vault-store&deviceType=0" \
    2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)

if [ -z "$TOKEN" ]; then
    echo "[vault-store] ERROR: authentication failed"
    exit 1
fi

echo "[vault-store] Authenticated successfully to ${VAULT_URL}"

SECRET_KEYS=(
    "OPENCODE_GO_API_KEY"
    "TELEGRAM_BOT_TOKEN"
    "TELEGRAM_ALLOWED_USERS"
    "DISCORD_BOT_TOKEN"
)

STORED=0
SKIPPED=0

for KEY in "${SECRET_KEYS[@]}"; do
    VALUE=$(grep "^${KEY}=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true)
    if [ -z "$VALUE" ]; then
        echo "[vault-store] SKIP: ${KEY} not set in .env"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    EXISTING=$(curl -s \
        -H "Authorization: Bearer ${TOKEN}" \
        "${VAULT_URL}/api/objects/item?search=${KEY}" \
        2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    items = d.get('Data', {}).get('Data', [])
    for i in items:
        if i.get('Name') == '${KEY}' or i.get('name') == '${KEY}':
            print(i.get('id') or i.get('Id') or '')
            break
except Exception:
    pass
" 2>/dev/null || true)

    if [ -n "$EXISTING" ]; then
        echo "[vault-store] SKIP: ${KEY} already in vault (id=${EXISTING})"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    RESP=$(curl -s \
        -X POST "${VAULT_URL}/api/ciphers" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"type\":1,\"name\":\"${KEY}\",\"login\":{\"password\":\"${VALUE}\"},\"notes\":\"Stored by vault-store.sh\"}" \
        2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id') or d.get('Id') or 'FAILED')" 2>/dev/null || echo "FAILED")

    if [ "$RESP" != "FAILED" ] && [ -n "$RESP" ]; then
        echo "[vault-store] STORED: ${KEY} (id=${RESP})"
        STORED=$((STORED + 1))
    else
        echo "[vault-store] ERROR: Failed to store ${KEY}"
    fi
done

echo "[vault-store] Done: ${STORED} stored, ${SKIPPED} skipped"

# Verify by listing all items
echo "[vault-store] Verifying vault contents..."
curl -s \
    -H "Authorization: Bearer ${TOKEN}" \
    "${VAULT_URL}/api/objects/item" \
    2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('Data', {}).get('Data', [])
print(f'Total items in vault: {len(items)}')
for i in items:
    print(f'  - {i.get(\"Name\", \"?\")}')
" 2>/dev/null || echo "[vault-store] Verification failed"
