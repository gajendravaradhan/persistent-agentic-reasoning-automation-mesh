# PARAM Security Remediation Plan

**Status:** ACTIVE INCIDENT — Public repo leaks credentials  
**Date:** 2026-06-28  
**Severity:** CRITICAL  
**Approver:** Gajendra  
**Repo:** github.com/gajendravaradhan/persistent-agentic-reasoning-automation-mesh (PUBLIC)

---

## Incident Summary

The repository `persistent-agentic-reasoning-automation-mesh` is PUBLIC on GitHub. The file `deploy/nas/docker-compose.yml` (committed in HEAD and across multiple historical commits) contains live production credentials:

| Credential | Type | Status |
|---|---|---|
| `HERMES_LANGFUSE_PUBLIC_KEY=pk-lf-<REDACTED>` | Langfuse observability public key | LEAKED |
| `HERMES_LANGFUSE_SECRET_KEY=sk-lf-<REDACTED>` | Langfuse observability SECRET key | **LEAKED — read access to all production traces** |
| `BW_CLIENTID=user.<REDACTED>` | Vaultwarden service account ID | LEAKED |
| `BW_CLIENTSECRET=REDACTED-BW-SECRET` | Vaultwarden service account SECRET | **LEAKED — full Bitwarden vault access** |

Other credentials (TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY, etc.) live in `deploy/nas/hermes-data/.env` which IS properly gitignored and NOT in git history. Verified via `git ls-files deploy/nas/hermes-data/.env` → empty.

---

## Remediation Phases

### Phase 1 — Containment (USER-MUST-DO, IMMEDIATE)

**Action: Rotate the leaked credentials.** Only you can do this — I cannot.

1. **Langfuse** — Cloud Langfuse dashboard (`cloud.langfuse.com`)
   - Project Settings → API Keys → Revoke `sk-lf-<REDACTED>`
   - Create new key pair → update new values in your local `deploy/nas/hermes-data/.env` (under `HERMES_LANGFUSE_PUBLIC_KEY` and `HERMES_LANGFUSE_SECRET_KEY` keys — add them if missing)
   - Traces are now safe — old key cannot be used to read production agent data

2. **Vaultwarden Service Account** — Vaultwarden admin UI on NAS (`https://vault.param.aiforges.app`)
   - Settings → API Key → revoke `user.<REDACTED>`
   - Generate new service account → update `BW_CLIENTID` and `BW_CLIENTSECRET` in `deploy/nas/hermes-data/.env`
   - Old creds can no longer read your vault

3. **Telegram Bot Token** — @BotFather (REVOKE as precaution)
   - Send `/revoke` to @BotFather → old token invalidated
   - Send `/newbot` or `/token` → get fresh token → update `TELEGRAM_BOT_TOKEN` in `deploy/nas/hermes-data/.env`
   - Prevents token theft if any other leak surfaces

**Do this BEFORE Phase 2-3. The leaked keys are still valid right now.**

### Phase 2 — Source Code Fix (PARAM-APPLIES, AFTER USER CONFIRMS ROTATION)

Move secrets from `deploy/nas/docker-compose.yml` into `deploy/nas/hermes-data/.env` (already gitignored). Use Docker Compose variable substitution.

1. Edit `deploy/nas/docker-compose.yml` hermes service environment section:
   ```yaml
   environment:
     - HERMES_UID=${HERMES_UID:-1000}
     - HERMES_GID=${HERMES_GID:-1001000}
     - HERMES_DASHBOARD=1
     - HERMES_DASHBOARD_HOST=0.0.0.0
     - HERMES_DASHBOARD_INSECURE=1
     - HERMES_LANGFUSE_PUBLIC_KEY=${HERMES_LANGFUSE_PUBLIC_KEY}
     - HERMES_LANGFUSE_SECRET_KEY=${HERMES_LANGFUSE_SECRET_KEY}
     - HERMES_LANGFUSE_BASE_URL=${HERMES_LANGFUSE_BASE_URL:-https://cloud.langfuse.com}
     - HERMES_LANGFUSE_ENV=${HERMES_LANGFUSE_ENV:-production}
     - HERMES_LANGFUSE_SAMPLE_RATE=${HERMES_LANGFUSE_SAMPLE_RATE:-1.0}
     - BW_CLIENTID=${BW_CLIENTID}
     - BW_CLIENTSECRET=${BW_CLIENTSECRET}
   ```

2. Append rotated values from Phase 1 to `deploy/nas/hermes-data/.env`:
   ```env
   # Observability — ROTATED 2026-06-28
   HERMES_LANGFUSE_PUBLIC_KEY=pk-lf-<NEW>
   HERMES_LANGFUSE_SECRET_KEY=sk-lf-<NEW>
   HERMES_LANGFUSE_BASE_URL=https://cloud.langfuse.com
   HERMES_LANGFUSE_ENV=production
   HERMES_LANGFUSE_SAMPLE_RATE=1.0

   # Vaultwarden service account — ROTATED 2026-06-28
   BW_CLIENTID=user.<NEW>
   BW_CLIENTSECRET=<NEW>
   ```

3. Verify `.gitignore` includes the .env paths:
   - `deploy/nas/hermes-data/.env` (already there ✓)
   - `deploy/nas/hermes-data/sessions/` (already there ✓)
   - Add `**/.env` (catch-all)

### Phase 3 — Git History Scrub (PARAM-APPLIES, DESTRUCTIVE — needs explicit approval)

Even after Phase 2 fixes HEAD, the secrets remain in past commits. Anyone with the repo URL can checkout old commits and read them. **History must be rewritten.**

**Approach:** Use `git filter-repo` (the modern replacement for `git filter-branch`). Steps:

1. Install `git-filter-repo`:
   ```bash
   brew install git-filter-repo
   ```

2. Create a `secrets-removal.txt` file:
   ```
   REDACTED-LANGFUSE-SECRET==>REDACTED-LANGFUSE-SECRET
   REDACTED-LANGFUSE-PUBLIC==>REDACTED-LANGFUSE-PUBLIC
   REDACTED-BW-SECRET==>REDACTED-BW-SECRET
   REDACTED-BW-CLIENTID==>REDACTED-BW-CLIENTID
   ```

3. Run filter-repo against the entire history:
   ```bash
   cd ~/projects/persistent-agentic-reasoning-automation-mesh
   git filter-repo --replace-text secrets-removal.txt --force
   ```

4. Force-push the rewritten history:
   ```bash
   git push origin --force --all
   git push origin --force --tags
   ```

5. Notify any forks / clones to re-clone from scratch (GitHub cache may still serve old commits for ~24h via API, but cloned repos will be unaffected for fresh clones).

**WARNING:** Force-push rewrites commit SHAs. Anyone with an active branch off the old history will need to reset. Since this is a personal project, low impact.

### Phase 4 — Dashboard Auth Hardening (PARAM-APPLIES)

TokenEye dashboard (`https://tokeneye.aiforges.app`) currently exposes usage analytics without auth. Two fix options:

**Option A (recommended, fastest):** Remove the `tokeneye.aiforges.app` ingress rule from cloudflared-config.yml. Reach dashboard via LAN only (`http://192.168.1.167:8788` after exposing port 8788 on LAN).

**Option B (keep public URL + add auth):** Add Cloudflare Access policy in Zero Trust dashboard:
- Applications → Add Application → Self-hosted
- Domain: `tokeneye.aiforges.app`
- Policy: require email equals gajendra's email
- Saves public reachability but gates to user-only

### Phase 5 — Stale Mac Hermes Config (PARAM-APPLIES)

Update `~/.hermes/config.yaml` `model.base_url` from `http://127.0.0.1:8787/zen/go/v1` (dead) to either:
- `http://192.168.1.167:8787/zen/go/v1` (LAN-direct to NAS, requires exposing 8787 on NAS LAN — currently only 127.0.0.1:8787 bound)
- Or: switch Mac's local Hermes model provider entirely to direct Anthropic/OpenAI with API keys (drop depend on tokeneye)

---

## Verification (After All Phases)

1. `git grep -E 'sk-lf-|pk-lf-|BW_CLIENTSECRET|UIufNyU4' $(git rev-list --all)` — should return ZERO hits across full history
2. `gh repo view --json visibility` — remains PUBLIC (intentional; repo is for portfolio)
3. NAS `param` container env: `docker exec param env | grep -E 'LANGFUSE|BW_'` — shows new rotated values (not old)
4. NAS app starts and traces still flow to Langfuse (new keys work)
5. `curl https://tokeneye.aiforges.app/` — returns 403/redirect (Option A) OR login challenge (Option B)

---

## Action Owners

| Phase | Owner | Status |
|---|---|---|
| 1. Rotate keys (Langfuse, Vaultwarden, Telegram) | **USER** | Pending — must do |
| 2. Source code fix (docker-compose.yml) | PARAM | Pending user approval to apply |
| 3. Git history scrub + force-push | PARAM | Explicit approval needed for force-push |
| 4. TokenEye dashboard auth | PARAM | Awaiting user's choice A vs B |
| 5. Mac Hermes config refresh | PARAM | Awaiting user's choice of endpoint |

---
