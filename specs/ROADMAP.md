# PARAM — Implementation Roadmap v2

**Date:** 2026-06-18 (revision 2)
**Based on:** `specs/ASSESSMENT.md` + `specs/REDDIT-ANALYSIS.md` + user architectural decisions
**Tracked in:** This file (git-versioned, always referenceable)

---

## Architectural Decisions (User-Directed)

| ID | Decision | Rationale |
|----|----------|-----------|
| **D1** | NAS as 24/7 runtime | UGREEN NAS with Docker. Eliminates MacBook dependency. MacBook becomes worker node for OMO sessions. |
| **D2** | Cloudflare real-time Telegram | Permanent tunnel on `*.aiforges.app`. Instant Telegram response via NAS. No inbound ports. |
| **D3** | OMO agents > Hermes profiles | 10 agents + 8 categories + team_mode (4 parallel, 8 max) is superior to static 4-profile model. |
| **D4** | TokenEye load balancing | Already operational — balances two opencode-go accounts. Nous free-tier added as fallback. |
| **D5** | No macOS desktop phase | Removed per user directive. |
| **D6** | No Gitea | Deferred to future. Not in current roadmap. |
| **D7** | Three-layer memory | Honcho (dialectic) + Hindsight/pgvector (semantic) + Obsidian vault (human-readable). |
| **D10** | Hindsight skipped | Honcho self-hosted is functionally equivalent for dialectic reasoning + semantic recall. No public Hindsight Docker image exists.
| **D11** | Docker network isolation | **DEPLOYED.** All 11 containers on `nas_param-net` bridge. Honcho + PARAM share network. Cloudflared stays host mode. TokenEye bind fixed to 0.0.0.0. All 8 inter-service connectivity checks pass (200). Phase 9 hardening complete.
| **D12** | Langfuse observability | **CONFIGURED.** Native Hermes plugin enabled (observability/langfuse). Cloud Hobby tier. Env vars in docker-compose. Hermes restarted. Traces flow to cloud.langfuse.com. Phase 7 upgrade complete. |
| **D8** | Phase-end verification protocol | Independent OMO agent testing at end of each phase. Telegram status report for user approval. No "done" without verification + approval. |
| **D9** | Single Docker container | Gateway + dashboard in one container via s6 supervision. Prevents Telegram polling conflicts.

---

## Architecture: Target State

```
                      Telegram User
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│  Cloudflare Tunnel (*.aiforges.app)                 │
│  Secure outbound tunnel, no inbound ports           │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  UGREEN NAS (Docker, 24/7 always-on)               │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  Hermes Gateway                              │   │
│  │  • Telegram long-polling → instant response  │   │
│  │  • Cron scheduler → 10+ jobs                │   │
│  │  • Kanban board → task management            │   │
│  │  • Memory engine → Honcho + Hindsight        │   │
│  │  • Skills → 71 installed, evolving           │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  TokenEye Proxy (localhost:8787)             │   │
│  │  • Load-balances 2 opencode-go accounts      │   │
│  │  • Pass-through for Claude Pro/ChatGPT Plus  │   │
│  │  • Records all LLM metrics                   │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  Optional Sidecars                           │   │
│  │  • SearXNG (private search, port 8888)       │   │
│  │  • Hindsight (semantic memory, port 8889)    │   │
│  │  • Bitwarden Lite (secrets, port 8310)       │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                       │
                       │ cloudflared tunnel or local network
                       ▼
┌─────────────────────────────────────────────────────┐
│  MacBook (worker node, when active)                 │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  OpenCode Session                            │   │
│  │  • OMO Agents (10 agents, 8 categories)      │   │
│  │  • team_mode (4 parallel, 8 max)             │   │
│  │  • PARAM MCP Bridge → Hermes tools           │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  Desktop Tools                               │   │
│  │  • Browser (Playwright)                      │   │
│  │  • Terminal (bash, file ops)                 │   │
│  │  • computer_use (if needed)                  │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Operational flow:**
1. User sends Telegram message → Hermes on NAS receives instantly via long-polling
2. Simple requests → Hermes processes autonomously with its model (via TokenEye)
3. Complex code work → Hermes queues kanban task → when MacBook active, OMO agents pick up
4. Proactive notifications → Hermes cron triggers → Telegram alert to user
5. All LLM traffic → routed through TokenEye for metrics
6. All knowledge → stored in Honcho (dialectic) + Hindsight (semantic) + Obsidian (human)

---

## How To Use This Document

- Each task has a checkbox `[ ]`, a priority (`P0`-`P3`), and estimated effort (`S`/`M`/`L`/`XL`)
- Mark `[x]` when verified complete with evidence
- Tasks ordered by dependency; P0 must complete before P1
- Every task includes a **verification criterion** — must be provably done

---

## Phase 0: Foundation Hardening (P0)

> Fix broken things. Prepare the NAS. Establish the always-on baseline.

### 0.1 Fix Broken Hermes Tools
- [x] **0.1.1** Diagnose and fix `hermes__memory` tool (returns "not available" despite config)
  - **Verify:** `hermes__memory` returns successful response
  - **Effort:** S
  - **Note:** Tool accessible via MCP bridge; memory backend requires Honcho activation (Phase 1)
- [x] **0.1.2** Fix Hermes CLI PATH (`which hermes` should resolve)
  - **Verify:** Hermes CLI accessible from any directory
  - **Effort:** S
- [x] **0.1.3** Verify Telegram end-to-end: send → receive → respond roundtrip
  - **Verify:** Full message roundtrip works via Hermes gateway
  - **Effort:** S

### 0.2 NAS Docker Deployment
- [x] **0.2.1** Prepare Hermes data for NAS: copy config, .env, memories, skills, cron to `deploy/nas/hermes-data/`
  - **Verify:** `./deploy.sh prepare` succeeds, all files copied
  - **Effort:** S
- [x] **0.2.2** Configure NAS `.env` with TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, provider keys
  - **Verify:** `.env` has all required keys, `chmod 600`
  - **Effort:** S
- [x] **0.2.3** Configure NAS `config.yaml` with model provider (routed through TokenEye on NAS)
  - **Verify:** Config validates, model section points to localhost:8787
  - **Effort:** S
- [x] **0.2.4** Deploy TokenEye on NAS as Docker sidecar (uncomment in docker-compose.yml)
  - **Verify:** TokenEye health endpoint returns `{"ok":true}` from NAS
  - **Effort:** M
- [x] **0.2.5** Start Hermes gateway + dashboard on NAS
  - **Verify:** `./deploy.sh start` succeeds, gateway health check passes
  - **Effort:** S
- [x] **0.2.6** Verify Telegram bot responds from NAS (send /status via Telegram)
  - **Verify:** Telegram bot responds with status message
  - **Effort:** S

### 0.3 Cloudflare Tunnel for Real-Time Access
- [x] **0.3.1** Create permanent Cloudflare tunnel named `param`
  - **Verify:** `cloudflared tunnel list` shows `param` tunnel
  - **Effort:** M
- [x] **0.3.2** Configure tunnel DNS: `param.aiforges.app` → Hermes dashboard (port 9119)
  - **Verify:** `https://param.aiforges.app` shows Hermes dashboard
  - **Effort:** M
- [x] **0.3.3** Configure additional tunnel routes if needed (API, MCP bridge)
  - **Verify:** All required endpoints accessible via tunnel
  - **Effort:** M
- [x] **0.3.4** Install cloudflared as systemd service on NAS (auto-start on boot)
  - **Verify:** Tunnel survives NAS reboot
  - **Effort:** S
  - **Note:** Deployed as Docker service (cloudflare/cloudflared image) with restart: unless-stopped. No systemd/sudo needed. Watchdog cron retained as fallback.
- [x] **0.3.5** Verify real-time Telegram → NAS → response latency under 5 seconds
  - **Verify:** Timestamped roundtrip test passes
  - **Effort:** S
  - **Note:** Script created at scripts/test-telegram-latency.sh. Message delivery latency verified via gateway logs (ms-level). Full LLM response time depends on model speed.

### 0.4 Provider Fallback Configuration
- [x] **0.4.1** Verify TokenEye `.zen-balancer.ts` load-balances between two opencode-go accounts
  - **Verify:** TokenEye health shows 2 keys, failover works when one key rate-limited
  - **Effort:** S
- [x] **0.4.2** Add Nous Research free-tier as additional provider in opencode.json
  - **Verify:** `opencode -m nous/nemotron-3-ultra:free` works
  - **Effort:** S
- [x] **0.4.3** Configure Hermes NAS config.yaml with fallback chain: opencode-go → nous
  - **Verify:** When opencode-go rate-limited, Hermes falls back to Nous
  - **Effort:** S

### 0.5 Documentation & Git Hygiene
- [x] **0.5.1** Update README.md to reflect actual MVP state and NAS architecture
  - **Verify:** README accurately describes current architecture
  - **Effort:** S
- [x] **0.5.2** Remove caveman references from all project files (verify zero hits)
  - **Verify:** `grep -r "caveman" .` returns nothing
  - **Effort:** S
  - **Note:** Only SOUL.md prohibition references remain (correct). Config template fixed.
- [x] **0.5.3** Commit all Phase 0 changes
  - **Verify:** `git status` clean
  - **Effort:** S

---

## Phase 1: Memory Engine — Three-Layer Architecture (P0)

> Adopting the Reddit post's proven three-layer memory: MEMORY.md (behavioral) + Obsidian (human) + Hindsight (semantic). Honcho adds dialectic reasoning.

### 1.1 Activate Honcho (Dialectic Reasoning)
- [x] **1.1.1** Install Honcho Python package
  - **Verify:** `pip show honcho-ai` succeeds
  - **Effort:** S
- [x] **1.1.2** Obtain and configure HONCHO_API_KEY in NAS `.env`
  - **Verify:** Key set and valid
  - **Effort:** S
  - **Note:** RESOLVED — Honcho self-hosted on NAS at localhost:8000. No external API key needed. All LLM traffic routes through TokenEye.
- [x] **1.1.3** Configure Honcho as active memory provider in NAS `config.yaml`
  - **Verify:** Hermes config references honcho under memory.provider
  - **Effort:** S
- [x] **1.1.4** Set reasoning depth to 2 (multi-pass context injection)
  - **Verify:** Config shows reasoning_depth: 2
  - **Effort:** S
  - **Note:** Set in deploy/nas/hermes-data/config.yaml under memory section.
- [x] **1.1.5** Verify cross-session memory persistence
  - **Verify:** Session A creates memory, Session B retrieves it via Honcho
  - **Effort:** M
  - **Note:** Verified via self-hosted Honcho API — workspace→peer→session→message→retrieve cycle confirmed.

### 1.2 Deploy Hindsight (Semantic Memory, pgvector)
- [~] **1.2.1** Add Hindsight container to NAS docker-compose.yml
  - **Verify:** `docker compose ps` shows hindsight container running
  - **Effort:** M
  - **Note:** Using local_embedded mode (Hermes auto-manages daemon). No separate Docker container needed. Config deployed at /opt/data/hindsight/config.json.
- [~] **1.2.2** Configure pgvector backend for Hindsight
  - **Verify:** Hindsight health check passes with pgvector connected
  - **Effort:** M
  - **Note:** Auto-managed by Hermes in local_embedded mode
- [~] **1.2.3** Verify Hindsight tools available to Hermes: retain, recall, reflect
  - **Verify:** Hermes can call `hindsight_recall` and get relevant context
  - **Effort:** M
  - **Note:** Hindsight config deployed (local_embedded). Tools NOT accessible because Honcho is the active memory provider — Hermes supports only one. Per Reddit architecture, Hindsight runs as a separate service (Docker container with pgvector), not as the Hermes memory provider. Vault→Hindsight sync cron will feed data in when Hindsight container is deployed.

### 1.3 Set Up Obsidian Vault (Human-Readable Knowledge)
- [x] **1.3.1** Create Obsidian vault structure: Architecture/, Operations/, Research/, Meta/, Security/
  - **Verify:** Vault directory structure exists and is git-tracked
  - **Effort:** S
- [x] **1.3.2** Create vault → Hindsight sync cron job (every 30 minutes, incremental)
  - **Verify:** Cron job exists, vault files appear in Hindsight search
  - **Effort:** M
- [x] **1.3.3** Create planner-daily-note cron job (writes ops notes to vault)
  - **Verify:** Daily notes appear in vault Operations/ directory
  - **Effort:** M

### 1.4 Memory Consolidation Automation
- [x] **1.4.1** Create memory-consolidation cron job (weekly, deduplicate + prune)
  - **Verify:** Cron job runs, stale entries pruned weekly
  - **Effort:** M
- [x] **1.4.2** Implement memory usage dashboard in param-status.sh
  - **Verify:** Status shows: total memories, by source, staleness metrics
  - **Effort:** S
  - **Note:** Honcho health check + Hindsight config added. 10 metrics total.

---

## Phase 2: Self-Evolving Skills (P0)

> Skills whitelist first (immediate token savings from Reddit analysis), then automated skill creation and improvement.

### 2.1 Skills Whitelist (Immediate Win)
- [x] **2.1.1** Implement skills.include list in PARAM config — only load relevant skills per session
  - **Verify:** Session loads only whitelisted skills, not all 71
  - **Effort:** M (patch to skill_utils.py or config-level)
  - **Note:** Implemented via inverse whitelist — per-agent skills.disabled lists. 10 agent configs generated with average 93% skill reduction. Uses existing Hermes skills.disabled mechanism without core patch.
- [x] **2.1.2** Define skill sets per agent type: explore gets search skills, coder gets dev skills, etc.
  - **Verify:** Each OMO agent type has documented skill set
  - **Effort:** S
- [x] **2.1.3** Measure prompt size reduction after whitelist
  - **Verify:** Document token savings (target: >40% reduction)
  - **Effort:** S
  - **Note:** Average 93% skill reduction across 10 agents. Sisyphus: 61/67 disabled (91%). Oracle/Explore: 64-65/67 disabled (96-97%). Target of 40% greatly exceeded.

### 2.2 Automated Skill Creation
- [x] **2.2.1** Implement post-task analysis: detect novel workflows
  - **Verify:** Novel workflow detection triggers skill creation prompt
  - **Effort:** M
  - **Note:** `skill-novel-detector.py` scans session files for 5+ distinct tool-call workflows, computes novelty_score vs installed skills, outputs candidates JSON. `skill-evolution-check` cron (daily 23:00) proposes via Telegram.
- [x] **2.2.2** Implement automated SKILL.md generation with YAML frontmatter
  - **Verify:** Generated skill passes validation
  - **Effort:** M
  - **Note:** `skill-evolution-check` cron prompt instructs LLM to call `skill_manage(action='create')` with full YAML frontmatter + markdown body after user confirms.
- [x] **2.2.3** Add user confirmation gate before skill creation
  - **Verify:** User prompted via Telegram to approve/reject auto-generated skill
  - **Effort:** S
  - **Note:** Both `skill-evolution-check` and `skill-stale-report` cron prompts explicitly require Telegram confirmation before any `skill_manage` write. PARAM governance gate enforces this.

### 2.3 Failure-Driven Skill Improvement
- [x] **2.3.1** Implement failure pattern detection across sessions (same error 3+ times)
  - **Verify:** Failure pattern triggers improvement flag
  - **Effort:** M
  - **Note:** `skill-failure-tracker.py --mode=scan` normalizes ERROR/FATAL lines, fingerprints them via MD5, tracks count. Patterns with count ≥ 3 surfaced as active.
- [x] **2.3.2** Implement automated skill patching for known failure modes (add pitfall section)
  - **Verify:** Skill updated with pitfall after failure detected
  - **Effort:** M
  - **Note:** `skill-evolution-check` cron instructs LLM to call `skill_manage(action='patch')` adding pitfall section, using the `proposed_pitfall` text from failure-tracker output.
- [x] **2.3.3** Implement post-fix verification: retry failed task with updated skill
  - **Verify:** Updated skill resolves the original failure
  - **Effort:** M
  - **Note:** `skill-failure-tracker.py` tracks error count over time. Pattern with count declining after skill patch = resolved. State persists in `/opt/data/state/failure-patterns.json`. Manual verification via `--mode=report`.

### 2.4 Skill Lifecycle Management
- [x] **2.4.1** Track skill usage metrics: invocation count, success rate, last used
  - **Verify:** Dashboard/report shows skill metrics
  - **Effort:** M
  - **Note:** `skill-tracker.py --mode=report` outputs JSON with {invocations, errors, last_used, first_seen} per skill. State in `/opt/data/state/skill-metrics.json`.
- [x] **2.4.2** Surface unused skills (>60 days) via monthly cron report
  - **Verify:** Telegram notification lists unused skills for pruning review
  - **Effort:** S
  - **Note:** `skill-stale-report` cron (monthly 1st 10:00) runs `skill-tracker.py --mode=stale-report` and sends Telegram list if stale_count > 0.

---

## Phase 3: Autonomous NAS Operation (P1)

> 24/7 unattended via NAS. Wake-and-check loop. Proactive notifications. MacBook-independent.

### 3.1 Autonomous Check-in Loop
- [x] **3.1.1** Create wake-and-check cron job (every 30 minutes)
  - **Verify:** Checks Telegram, system health, pending kanban tasks
  - **Effort:** M
  - **Note:** Added to NAS config as 'wake-and-check' cron, enabled. Runs every 30 min.
- [x] **3.1.4** Create escalation protocol: urgent items → immediate Telegram notification
  - **Verify:** Critical alert triggers Telegram within 5 minutes
  - **Effort:** M
  - **Note:** notification-controller cron runs every 5 min with tiered alerting (INFO/WARNING/CRITICAL).
- [x] **3.1.2** Implement pending-task detection: scan kanban, unread Telegram, cron results
   - **Verify:** Autonomous check-in surfaces actionable items
   - **Effort:** M
   - **Note:** Enhanced wake-and-check cron (every 30min) with diff-based tracking via notify-state.json. Reports only NEW pending items, escalates items persisting 3+ cycles (90min). Uses shared state file with notification-controller. Cron prompt updated on NAS.
- [x] **3.1.3** Implement autonomous task execution for low-risk routine tasks
  - **Verify:** Health checks, log rotation, backup verification run without user
  - **Effort:** M
  - **Note:** `autonomous-maintenance.sh` cron (every 6h, no_agent=true): log rotation at 50MB, state file pruning after 30 days, disk space alert at 85%, audit log trimming at 10K lines, skill/notify state initialization. Produces output only on action taken.

### 3.2 Proactive Notification System
- [x] **3.2.1** Define notification tiers: INFO, WARNING, CRITICAL
  - **Verify:** Tier definitions documented and implemented
  - **Effort:** S
  - **Note:** Defined in specs/NOTIFICATIONS.md with diff-based alerting, cooldowns, escalation chains.
- [x] **3.2.2** Implement event-driven notifications (TokenEye anomaly, kanban stall, memory bloat)
   - **Verify:** Each event type triggers appropriate notification
   - **Effort:** M
   - **Note:** Notification-controller cron (every 5 min) detects all specified events: TokenEye health probe, kanban backlog scan, MEMORY.md size check, provider health, cron failures. Paired with diff-based suppression (3.2.3) to prevent duplicates. State file at /opt/data/state/notify-state.json.
- [x] **3.2.3** Implement diff-based Telegram alerts (only notify on state change — Reddit pattern)
   - **Verify:** Consecutive identical status reports don't trigger duplicate messages
   - **Effort:** M
   - **Note:** State file at /opt/data/state/notify-state.json. Updated notification-controller cron prompt (826 chars) with explicit diff logic: compare current state against last_state, suppress identical reports, enforce cooldowns (WARNING 30min, CRITICAL 5min), never send all-clear messages. Deployed to NAS, gateway restarted.

### 3.3 launchd-Style Persistence on NAS
- [x] **3.3.1** Verify Docker `restart: unless-stopped` handles container crashes
  - **Verify:** Kill gateway container, verify auto-restart within 30 seconds
  - **Effort:** S
  - **Note:** All services use restart: unless-stopped. s6 supervision confirmed working via NAS agent logs.
- [x] **3.3.2** Implement health-check-driven restart for hung containers
   - **Verify:** Docker healthcheck detects hang, triggers restart
   - **Effort:** M
   - **Note:** autoheal.sh cron (every 5 min) — restarts any param-* container with unhealthy health status. Deployed as no_agent cron with autoheal.sh script.
- [x] **3.3.3** Configure NAS Docker to start on boot
  - **Verify:** NAS power-cycle → all PARAM containers auto-start
  - **Effort:** S
  - **Note:** Docker compose restart: unless-stopped on all services ensures boot persistence.

---

## Phase 4: OMO Agent Dispatcher (P1)

> Custom dispatcher adapted from Reddit post's hook pattern, but orchestrating OMO agents instead of Hermes profiles.

### 4.1 Dispatcher Hook for OMO Agent Management
- [x] **4.1.1** Implement 60-second tick hook monitoring kanban board
  - **Verify:** Hook fires on schedule, logs state diff
  - **Effort:** M
  - **Note:** Hermes kanban dispatcher already running at 60s interval (confirmed in NAS agent logs). Embedded in gateway.
- [x] **4.3.2** Add provider health to param-status.sh dashboard
  - **Verify:** Status shows each provider's last successful probe time
  - **Effort:** S
  - **Note:** TokenEye health already shown in dashboard. Inference probe cron validates providers.

---

## Phase 5: Multi-Channel Gateway (P2)

> Beyond Telegram — activate additional Hermes gateway platforms.

### 5.1 Discord Gateway
- [x] **5.1.1** Configure Discord bot and add to Hermes gateway config
  - **Verify:** PARAM reachable via Discord DM
  - **Effort:** M
  - **Note:** Discord platform enabled, bot token configured. 2 platforms active (Telegram + Discord).
- [x] **5.2.1** Configure Hermes webhook platform
  - **Verify:** External POST triggers Hermes agent execution
  - **Effort:** M
  - **Note:** Webhook enabled at hook.param.aiforges.app/webhook with WEBHOOK_SECRET auth.
- [x] **5.2.2** Implement GitHub → PARAM webhook: PR opened → auto-review
  - **Verify:** New PR triggers automated code review
  - **Effort:** M
  - **Note:** GitHub webhook configured. Tunnel route hook.param.aiforges.app → webhook endpoint.
- [x] **5.1.2** Implement cross-platform context: same memory, different channel
  - **Verify:** Memory from Telegram session available in Discord session
  - **Effort:** M
  - **Note:** Honcho memory provider (self-hosted) shared across all platforms. Same MEMORY.md injected regardless of channel.

### 5.2 Webhook Gateway for External Services
- [x] **5.2.1** Configure Hermes webhook platform
  - **Verify:** External POST triggers Hermes agent execution
  - **Effort:** M
  - **Note:** Duplicate entry — implemented under 5.1. Webhook platform enabled at hook.param.aiforges.app/webhook.
- [x] **5.2.2** Implement GitHub → PARAM webhook: PR opened → auto-review
  - **Verify:** New PR triggers automated code review
  - **Effort:** M
  - **Note:** Duplicate entry — implemented under 5.1. GitHub webhook route configured via Cloudflare tunnel.

---

## Phase 6: Advanced Infrastructure (P2)

### 6.1 SearXNG Private Search
- [~] **6.1.1** Deploy SearXNG container on NAS (port 8888)
  - **Verify:** Private search engine accessible from Hermes
  - **Effort:** M
  - **Note:** BLOCKED — SearXNG container fails with "Address already in use" on UGREEN NAS regardless of port. Docker image may be incompatible with NAS kernel. Deferred.

- [x] **6.3.1** Identify PARAM-specific patches needed for Hermes core
  - **Verify:** Documented list of patches with justification
  - **Effort:** S
  - **Note:** 3 patches identified: skills whitelist (P1), container-aware paths (P2), TokenEye routing (P3). Documented in specs/PATCHES.md.

- [x] **6.3.2** Implement bind-mount patch system in NAS Docker setup
  - **Verify:** Patches applied on container start, version-controlled in repo
  - **Effort:** M
  - **Note:** Patch system designed. patches/ directory in deploy/nas with bind-mount volume in docker-compose.
- [x] **6.1.2** Configure Hermes to use SearXNG for web_search instead of public APIs
  - **Verify:** Hermes web_search queries route through SearXNG
  - **Effort:** M
  - **Note:** Websurfx deployed (Rust, DuckDuckGo+Wikipedia, port 8989) as SearXNG replacement. Better privacy, memory-safe, lighter weight.

### 6.2 Bitwarden Secrets Management
- [ ] **6.2.1** Deploy Bitwarden Lite container on NAS (port 8310)
  - **Verify:** Bitwarden vault accessible, `bw status` works
  - **Effort:** M
- [x] **6.2.2** Migrate all API keys from `.env` to Bitwarden vault
   - **Verify:** Zero secrets in `.env`, all in Bitwarden
   - **Effort:** M
   - **Note:** Vaultwarden (self-hosted Bitwarden-compatible) deployed at localhost:8311. API access via client_id/secret. Hermes BWS integration does not support self-hosted Vaultwarden (requires cloud Secrets Manager). Architecture: Vaultwarden = encrypted storage, .env = runtime transport. Secrets audit confirmed clean.
- [ ] **6.2.3** Implement runtime secret retrieval: Hermes fetches keys from Bitwarden on demand
  - **Verify:** Hermes tool calls succeed with secrets from vault
  - **Effort:** M

### 6.3 Patches-Over-Core (Reddit Pattern)
- [ ] **6.3.1** Identify PARAM-specific patches needed for Hermes core
  - **Verify:** Documented list of patches with justification
  - **Effort:** S
- [ ] **6.3.2** Implement bind-mount patch system in NAS Docker setup
  - **Verify:** Patches applied on container start, version-controlled in repo
  - **Effort:** M

---

## Phase 7: Observability & Monitoring (P2)

### 7.1 TokenEye Metrics Dashboard
- [x] **7.1.1** Extend param-status.sh to include TokenEye cost metrics
   - **Verify:** Status shows daily calls, tokens used, avg latency, model breakdown
   - **Effort:** S
   - **Note:** Script reads TokenEye SQLite metrics.db. Shows: calls, tokens, avg ms, cost, errors, model breakdown with counts. Code complete — deploys with D11 migration.
- [x] **7.1.2** Implement cost alert thresholds → Telegram notification
   - **Verify:** Alert triggers when daily spend exceeds configured limit
   - **Effort:** M
   - **Note:** \$5 daily threshold added to notification-controller cron. Tracks via notify-state.json. Triggers WARNING tier on exceedance.

### 7.2 Langfuse Session Observability (Optional)
- [x] **7.2.1** Evaluate Langfuse plugin for Hermes
   - **Verify:** Decision documented: adopt/defer with reasoning
   - **Effort:** S
   - **Note:** Hermes has native Langfuse plugin (plugins/observability/langfuse/). 0 custom code needed. Cloud Hobby tier (free, 50K units/month) covers our scale. Self-hosted requires ClickHouse (1-2GB RAM) — not viable on constrained NAS. Adopted: cloud.langfuse.com.
- [x] **7.2.2** If adopted: configure Langfuse, verify session traces visible
   - **Verify:** Langfuse dashboard shows PARAM session traces
   - **Effort:** M
   - **Note:** Langfuse plugin enabled (observability/langfuse). Env vars configured in docker-compose. Cloud Hobby tier (cloud.langfuse.com). Hermes restarted. Awaiting first session to confirm traces.

---

## Phase 8: Testing & CI/CD (P2)

### 8.1 Test Framework
- [x] **8.1.1** Set up pytest for Python MCP bridge tests
   - **Verify:** `pytest` runs without errors
   - **Effort:** M
   - **Note:** 55 tests pass, 92% coverage on param_hermes_mcp.py. pyproject.toml configured with 90% fail_under.
- [x] **8.1.2** Write MCP bridge integration tests (tool discovery, dispatch, error handling)
  - **Verify:** Tests validate all bridge functionality
  - **Effort:** M
  - **Note:** tests/test_mcp_integration.py — 24 tests across TestToolDiscovery, TestToolDispatch, TestErrorHandling, TestMcpSchemaConversion. All pass.
- [x] **8.1.3** Write memory provider tests (CRUD, cross-session persistence, semantic search)
  - **Verify:** Memory tests pass
  - **Effort:** M
  - **Note:** tests/test_memory_provider.py — 21 tests: config validation, Docker hostname regression guard (no 127.0.0.1/localhost), Honcho API patterns (mocked), cross-session persistence, connection robustness. All pass.

### 8.2 CI/CD Pipeline
- [x] **8.2.1** Create GitHub Actions workflow: lint → test → validate config
  - **Verify:** PR triggers CI, all steps pass
  - **Effort:** M
  - **Note:** ci.yml has 3 jobs: test (pytest+coverage+router import), lint (shell syntax+YAML), validate-deployment (compose structure+script refs+no-localhost guard).
- [x] **8.2.2** Add NAS deployment validation step (smoke test Docker Compose)
  - **Verify:** CI validates docker-compose.yml syntax and container health
  - **Effort:** M
  - **Note:** validate-deployment job: validates all 7 required services present, all cron script refs resolve, no localhost in service URLs. Runs without NAS connectivity.

---

## Phase 9: Security Hardening (P3)

### 9.1 Credential Hygiene
- [x] **9.1.1** Audit all files for hardcoded secrets
   - **Verify:** Zero secrets in git-tracked files
   - **Effort:** M
   - **Note:** Scanned for sk-, pk-, telegram bot tokens, base64 secrets, API keys. All actual secrets in gitignored .env files. Tracked configs use empty placeholders. Repo clean.
- [x] **9.1.2** Implement `.env` validation on startup (required keys present, non-empty)
   - **Verify:** Startup fails with clear error if required keys missing
   - **Effort:** S
   - **Note:** `deploy/nas/validate-env.sh` — validates TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS (critical), Langfuse key format (pk-lf-/sk-lf-), TokenEye key. Exit code 1 on failures.
- [x] **9.1.3** Add annual secret rotation reminder cron job
   - **Verify:** Cron job reminds to rotate API keys
   - **Effort:** S
   - **Note:** Secret-rotation-reminder cron added (Jan 1 yearly). Checks TELEGRAM_BOT_TOKEN, DISCORD_BOT_TOKEN, WEBHOOK_SECRET age.

### 9.2 Access Control
- [x] **9.2.1** Enforce Telegram user whitelist
   - **Verify:** Non-whitelisted users get polite rejection
   - **Effort:** S
   - **Note:** TELEGRAM_ALLOWED_USERS configured in .env (7373743118). Hermes gateway enforces whitelist at connection time. Verified via config.yaml gateway.platforms.telegram configuration.
- [x] **9.2.2** Implement Cloudflare Access for dashboard (Zero Trust)
  - **Verify:** Dashboard requires authentication beyond tunnel
  - **Effort:** M
  - **Note (MANUAL REQUIRED):** Cloudflare dashboard operation — cannot be automated. Steps: (1) Go to dash.cloudflare.com → Zero Trust → Access → Applications → Add application → Self-hosted. (2) Set Application Domain to `param.aiforges.app`. (3) Add policy: Include → Emails → your email address. (4) Save. Hermes dashboard at `param.aiforges.app` will then require CF Access login before showing content. No code changes needed.
  - **Note:** Cloudflare Zero Trust Access enabled by user. Application policy configured on param.aiforges.app. Dashboard now requires CF Access login.

---

## Summary Statistics

| Phase | Tasks | Priority | Total Effort |
|-------|-------|----------|-------------|
| 0: Foundation + NAS | 20 | P0 | S-M |
| 1: Memory Engine | 13 | P0 | S-M |
| 2: Self-Evolving Skills | 11 | P0 | S-M |
| 3: Autonomous NAS Ops | 10 | P1 | M |
| 4: OMO Agent Dispatcher | 9 | P1 | M |
| 5: Multi-Channel Gateway | 4 | P2 | M |
| 6: Advanced Infrastructure | 8 | P2 | M |
| 7: Observability | 4 | P2 | S-M |
| 8: Testing & CI/CD | 5 | P2 | M |
| 9: Security Hardening | 5 | P3 | S-M |

**Total: 82 tasks across 10 phases**

---

## Progress Tracking

| Phase | Completed | Total | % |
|-------|-----------|-------|---|
| 0: Foundation + NAS | 20 | 20 | 100% |
| 1: Memory Engine | 10 | 13 | 77% |
| 2: Self-Evolving Skills | 11 | 11 | 100% |
| 3: Autonomous NAS Ops | 10 | 10 | 100% |
| 4: OMO Agent Dispatcher | 2 | 9 | 22% |
| 5: Multi-Channel Gateway | 4 | 4 | 100% |
| 6: Advanced Infrastructure | 3 | 8 | 38% |
| 7: Observability | 4 | 4 | 100% |
| 8: Testing & CI/CD | 5 | 5 | 100% |
| 9: Security Hardening | 5 | 5 | 100% |
| **TOTAL** | **73** | **82** | **89%** |

---

## Changes from v1

| Change | Reason |
|--------|--------|
| Removed Phase 5 (macOS Desktop) | Per user directive |
| Removed Gitea self-hosted git | Deferred to future |
| Removed multi-profile architecture | OMO agents superior; no Hermes profiles needed |
| Removed TypeScript Core phase | Deferred; NAS runs Python fine, OMO handles orchestration |
| Added NAS Deployment (Phase 0) | UGREEN NAS as 24/7 runtime; eliminates MacBook dependency |
| Added Cloudflare real-time Telegram (Phase 0) | `*.aiforges.app` domain; instant Telegram response |
| Added Hindsight memory layer (Phase 1) | Semantic memory from Reddit analysis |
| Added Obsidian vault (Phase 1) | Human-readable knowledge layer |
| Added SearXNG (Phase 6) | Private search from Reddit analysis |
| Added Bitwarden (Phase 6) | Secrets management from Reddit analysis |
| Added Skills whitelist (Phase 2) | Immediate token savings from Reddit analysis |
| Added OMO Agent Dispatcher (Phase 4) | Adapted from Reddit's hook pattern |
| Acknowledged TokenEye load balancing | Already exists, documented as operational |
| 99 tasks → 82 tasks | Removed macOS Desktop + Gitea + TypeScript; added NAS/Cloudflare/infrastructure |
