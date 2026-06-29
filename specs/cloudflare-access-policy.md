# Phase 4 — Cloudflare Access Policy for tokeneye.aiforges.app

**Status:** Pending user dashboard action  
**Date:** 2026-06-28

---

## Why

`https://tokeneye.aiforges.app` is currently publicly accessible with no auth gate. Anyone on the internet can browse your LLM usage analytics, model spend patterns, and provider breakdown. This is a privacy leak (not credential leak — no key material exposed), but it reveals operational signals that could inform a targeted attack.

## Fix: Cloudflare Access Policy (Option B from remediation plan)

This adds an authentication gate using your Cloudflare Zero Trust account, without changing the underlying Cloudflare tunnel or the tokeneye container.

## Steps (Perform in Cloudflare Dashboard)

1. Log in to [Cloudflare Zero Trust](https://one.dash.cloudflare.com/)
   - Account: whatever account owns the `aiforges.app` domain
2. Navigate to: **Access → Applications → Add Application → Self-hosted**
3. Configure the application:
   - **Application name:** `TokenEye Dashboard`
   - **Session Duration:** 24 hours (re-authenticate daily)
   - **Public domain:** `tokeneye.aiforges.app`
   - **Path:** leave blank (covers all paths)
4. Under **Identity providers:** enable **One-time PIN** (uses your email — no IdP setup needed) and your existing Cloudflare account login
5. Create a **Policy** named "Owner only":
   - **Action:** Allow
   - **Include rules:**
     - Emails ending with `gajendravaradhan@gmail.com` (or whichever email you use for Cloudflare)
   - **Block rules:** none
6. Click **Save**

## Effect

After saving, hitting `https://tokeneye.aiforges.app/` from any unauthenticated browser will redirect to a Cloudflare-hosted login page. After authenticating (with one-time PIN emailed to you), you get a 24-hour session and land on the dashboard.

## Verification

```bash
# Should return 302 redirect (not 200) to cloudflare access login
curl -sS -o /dev/null -w "HTTP %{http_code}\n" https://tokeneye.aiforges.app/
```
Expected after policy is set: `HTTP 302` with `Location: /cdn-cgi/access/login/...`

## Rollback

If the policy breaks legitimate access unexpectedly:
- Cloudflare dashboard → Access → Applications → click the TokenEye Dashboard entry → Delete
- Optionally also clear your DNS cache: `sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder` on Mac

## Why Not Option A (Remove Ingress Rule Entirely)

Option A would mean unsyncing `tokeneye.aiforges.app` from cloudflared ingress — quick fix but loses the convenience of public dashboard access from your phone. Cloudflare Access (Option B) keeps the convenience with auth.

---

**Status:** This doc is for your reference. The actual policy must be created in the Cloudflare dashboard — only you (the account owner) can do this. I cannot apply it programmatically without your Cloudflare API token, which we agreed not to exchange.
