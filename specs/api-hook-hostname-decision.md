# Decision Pending: api.param + hook.param — Execution Plan

**Status:** AWAITING USER DECISION  
**Date:** 2026-06-29  
**Governance:** PARAM AGENTS.md gate items 2, 3, 7, 8 — requires explicit user approval

## Context

Two Cloudflare tunnel hostnames have broken TLS (3rd-level subdomains not covered by free Universal SSL) and were researched for architectural intent:

- **`api.param.aiforges.app`** — VESTIGIAL. Designed (Phase 0.3.3) as "API/Health endpoint for MCP bridge remote access." No API server was ever built. Currently a dead alias for the dashboard (nginx:9090).
- **`hook.param.aiforges.app`** — REAL BUT UNIMPLEMENTED. Designed (Phase 5) as Hermes webhook ingestion endpoint (GitHub PR auto-review, external POST → agent execution). Hermes has a documented webhook platform (port 8644, HMAC auth, subscriptions) but only 4 lines of config were ever added (`webhook: enabled: true`). No port exposed, no secret, no nginx route, no DNS record, no subscriptions. ROADMAP falsely marks Phase 5 as 100% complete.

## Two Options

### Option A: Drop both (clean slate, ~10 min)

**What gets removed:**
- `api.param.aiforges.app` — tunnel route, DNS record, Access app
- `hook.param.aiforges.app` — tunnel route, DNS record, Access app
- Set `gateway.platforms.webhook.enabled: false` in config.yaml
- Correct ROADMAP Phase 5 false completion claim

**What's lost:**
- Nothing functional (neither ever worked)
- The webhook capability (which was never implemented) — would need full rebuild later if desired

**Execution steps:**
1. Remove `api.param` and `hook.param` ingress lines from `~/.cloudflared/config.yml` on NAS
2. Remove Access apps via CF API (or leave to auto-expire)
3. Set `webhook.enabled: false` in `deploy/nas/hermes-data/config.yaml`
4. Restart cloudflared
5. Update ROADMAP.md: mark Phase 5.2.1/5.2.2 as `[ ]` with note "webhook platform disabled — was never functionally wired"
6. Update README.md tunnel table: remove api.param and hook.param rows
7. Update `cloudflared-setup-noninteractive.sh`: remove "api.param" from DNS loop
8. Commit all changes

### Option B: Drop api, complete hook (~30 min)

**What gets removed:**
- `api.param.aiforges.app` — same as Option A

**What gets built (hook → hook.aiforges.app for free TLS):**
1. Add webhook config to `deploy/nas/hermes-data/config.yaml`:
   ```yaml
   gateway:
     platforms:
       webhook:
         enabled: true
         extra:
           host: "0.0.0.0"
           port: 8644
           secret: "${WEBHOOK_SECRET}"
   ```
2. Expose port 8644 in `deploy/nas/docker-compose.yml`:
   ```yaml
   hermes:
     ports:
       - "127.0.0.1:9119:9119"
       - "127.0.0.1:8644:8644"
   ```
3. Add `WEBHOOK_SECRET=<strong-random>` to NAS `.env`
4. Create `hook.aiforges.app` (2nd-level, free Universal SSL):
   - DNS route: `cloudflared tunnel route dns <tunnel-id> hook.aiforges.app`
   - Cloudflared ingress: `hook.aiforges.app → http://localhost:8644`
   - CF Access app with 3-email allow-list (same as vault/param)
5. Remove old `hook.param.aiforges.app` (broken TLS, won't work)
6. Restart Hermes gateway + cloudflared on NAS
7. Verify: `curl https://hook.aiforges.app/health` → `{"status":"ok"}`
8. Create a test subscription: `hermes webhook subscribe test ...`
9. Update ROADMAP Phase 5 notes to reflect actual completion
10. Commit all changes

**What's gained:**
- Working webhook ingestion endpoint (GitHub PR auto-review, CI/CD events, external triggers)
- Zero-LLM-cost direct delivery to Telegram/Discord
- Free TLS (2nd-level subdomain)

## Recommendation

**Option B** — the webhook platform is real, documented, and valuable (GitHub PR auto-review, external triggers, direct-delivery notifications). It's 30 minutes to complete something that was falsely claimed done. Dropping it loses a capability you designed and wanted. `api.param` should be dropped either way — it's purely vestigial.

## Files Prepared (execution-ready, awaiting approval)

- This file: decision context
- On approval, changes will be applied to:
  - `deploy/nas/configs/cloudflared-config.yml` (local working copy ready)
  - `deploy/nas/docker-compose.yml` (local working copy ready)
  - `deploy/nas/hermes-data/config.yaml` (on NAS)
  - NAS `.env` (on NAS)
  - `specs/ROADMAP.md` (local)
  - `deploy/nas/README.md` (local)
