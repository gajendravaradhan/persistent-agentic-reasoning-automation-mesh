#!/usr/bin/env bash
# Purge leaked secrets from git history. Run AFTER revoking tokens.
# Usage: bash scripts/purge-secrets.sh

set -euo pipefail

echo "⚠️  This will rewrite git history and force-push to origin/main."
echo "   Make sure you have already:"
echo "   1. Revoked the Telegram bot token in @BotFather"
echo "   2. Revoked the Cloudflare tunnel tokens in CF dashboard"
echo ""
read -p "Type 'YES' to proceed: " CONFIRM

if [ "$CONFIRM" != "YES" ]; then
    echo "Aborted."
    exit 1
fi

cd "$(dirname "$0")/.."

FILES_TO_PURGE=(
    "deploy/nas/hermes-data/.env"
    ".certs/cert.pem"
    ".certs/cert (1).pem"
)

echo "Purging from git history:"
for f in "${FILES_TO_PURGE[@]}"; do
    echo "  $f"
done

git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch ${FILES_TO_PURGE[*]}" \
  --prune-empty --tag-name-filter cat -- --all

echo ""
echo "Pushing to origin..."
git push origin main --force

echo ""
echo "✅ Done. Secrets purged from history. Update .env with new tokens."
