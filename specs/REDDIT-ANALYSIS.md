# PARAM — Reddit Setup Analysis & Applicable Patterns

**Source:** [r/hermesagent: "My Hermes setup, roast me"](https://www.reddit.com/r/hermesagent/comments/1u9fa2w/my_hermes_setup_roast_me/) by u/riceinmybelly
**Date:** 2026-06-18
**Status:** Analyzed for PARAM applicability

---

## The Setup (211 upvotes, 65 comments)

A solo developer running Hermes on Apple Silicon Mac to build a full-stack app (Next.js + NestJS + PostgreSQL + Redis). Hermes files its own tasks, writes code, runs QA, deploys, and keeps documentation current. User reviews work over Telegram.

### Architecture

```
Docker Host (macOS)
├── Hermes Container (4 profiles)
│   ├── local-admin: orchestrator, Telegram, cron (nous/free models)
│   ├── coder: implementation (Z.ai GLM-5.1 → opencode → nous → LM Studio)
│   ├── planner: research, task filing, daily notes (SearXNG-backed)
│   └── qa-tester: E2E browser testing (Playwright)
├── SearXNG Container (private search, port 8888)
├── Hindsight Container (semantic memory, pgvector, port 8889)
├── Bitwarden Lite Container (secrets, port 8310)
├── hermes-pi Container (cloud inference wrapper)
├── App Stack (separate docker-compose)
├── Gitea (self-hosted git, port 8300, with CI runner)
└── Host Services (launchd)
    ├── hermes-bridge.py (HTTP API for build/deploy/git)
    ├── git-backup (daily at 03:00)
    └── kanban-backup (kanban.db copy at 03:05)
```

---

## Patterns PARAM Should Adopt (Priority-Ordered)

### 🔴 CRITICAL — Add to Phase 0

#### 1. Skills Whitelist
**Problem:** PARAM has 71+ skills. Every session loads ALL of them, bloating the system prompt.
**Solution:** Patch `skill_utils.py` to support `skills.include` list per profile/agent.
**PARAM Impact:** Reduces token waste, improves focus. Each OMO agent type should only see relevant skills.

```
# In config.yaml or AGENTS.md:
skills:
  include:
    - systematic-debugging
    - requesting-code-review
    - test-driven-development
```

#### 2. Three-Layer Memory Architecture
**Problem:** PARAM has flat MEMORY.md + USER.md (77 lines). Single-layer, no semantic search.
**Solution:** Adopt the three-layer pattern:
| Layer | What | Purpose | Injected |
|-------|------|---------|----------|
| MEMORY.md | Behavioral rules, preferences | Every turn | Always |
| Obsidian vault | Long-form knowledge, case studies | Human-readable reference | On demand |
| Hindsight (pgvector) | Semantic memory, machine-searchable | Context injection | Via tools |

**PARAM Impact:** Transforms memory from static files to compounding knowledge. Hindsight offers `retain`, `recall`, `reflect` tools — complementary to Honcho's dialectic reasoning.

#### 3. Bitwarden Secrets Management
**Problem:** PARAM has API keys in `.env` files, some visible in config.
**Solution:** Bitwarden Lite container + CLI. `bw get item` at runtime.
**PARAM Impact:** Zero secrets in files. Rotated centrally. Audit trail.

### 🟡 HIGH — Add to Phase 1-3

#### 4. Custom Dispatcher Hook (60s Tick)
**Problem:** PARAM relies on cron for task dispatch. No live worker management.
**Solution:** Custom `asyncio` hook replacing built-in dispatcher:
- Promotes tasks when dependencies clear
- Reaps stalled workers (15min heartbeat, 4hr max runtime)
- Per-profile spawn caps
- Diff-based Telegram notifications (only alerts on state change)
- Cooldowns: 10min normal, 2min fast-retry, 30min after 3+ failures

**PARAM Impact:** Replaces half the Phase 3 items. Much more sophisticated than cron-based dispatch.

#### 5. Multi-Profile Architecture
**Problem:** PARAM is a single identity. No task specialization.
**Solution:** Multiple HERMES_PROFILES, each with different model, skills, and purpose:
- **orchestrator**: Telegram + cron dispatch + monitoring (cheap model)
- **coder**: Implementation (best coding model)
- **planner**: Research + task decomposition (online/search model)
- **reviewer**: QA + audit (verification model)

**PARAM Impact:** Different models for different tasks. Cheaper models for orchestration = lower costs. Specialized skills per profile.

#### 6. Provider Fallback Chain
**Problem:** PARAM uses single provider (opencode-go). No fallback.
**Solution:** Chain: `primary → fallback1 → fallback2 → local` like the post does with `zai → opencode → nous → LM Studio`.
**PARAM Impact:** Resilience. If opencode-go is rate-limited, fallback to Nous free tier or local model.

#### 7. Patches-Over-Core Pattern
**Problem:** PARAM currently edits Hermes config directly. No version-controlled patches.
**Solution:** Bind-mount patch files over Hermes core. Eight patches fix bugs without forking:
- `credential_pool.py`: fix rate limit reset timing
- `skill_utils.py`: add whitelist support
- `gateway_status.py`: fix virtiofs lock file issue
- `kanban_tools.py`: read-only for workers
- `hermes_state.py`: fix SQLite WAL crash on startup

**PARAM Impact:** Isolate PARAM customizations from Hermes core. Survives updates. Version-controlled.

### 🟢 MEDIUM — Add to Phase 4-7

#### 8. SearXNG Private Search
**Problem:** PARAM uses `web_search` which hits public APIs with rate limits.
**Solution:** Self-hosted SearXNG container. Private, unlimited, configurable.
**PARAM Impact:** No search API costs. Privacy. Configurable engines.

#### 9. Host Bridge Pattern
**Problem:** PARAM MCP bridge runs inside the same process. No separation.
**Solution:** `hermes-bridge.py` on macOS host (launchd-managed) exposing HTTP endpoints:
- `/build` - trigger project build
- `/deploy` - deploy to target
- `/git-pull` - pull latest
- `/restart` - restart services
- `/logs` - tail logs
- `/status` - health check

**PARAM Impact:** Operations can run even when Hermes session is down.

#### 10. launchd for Persistent Services
**Problem:** PARAM relies on cron for everything. No persistent services.
**Solution:** macOS launchd plists with `KeepAlive`:
- hermes-bridge keepalive
- git backup at 03:00
- kanban.db copy at 03:05

**PARAM Impact:** More robust than cron for always-on services.

#### 11. Gitea Self-Hosted Git
**Problem:** PARAM code on GitHub. No private CI.
**Solution:** Gitea on port 8300 with `act_runner` CI. Hermes has no admin access.
**PARAM Impact:** Private repos. Self-hosted CI. Independence from GitHub.

#### 12. Obsidian Vault as Knowledge Layer
**Problem:** PARAM knowledge lives only in MEMORY.md (machine-readable, not human-browsable).
**Solution:** Obsidian vault with directories like Architecture/, Operations/, Research/, Meta/. Human-readable + machine-indexed via Hindsight sync.
**PARAM Impact:** Knowledge is both human-browsable AND machine-searchable.

---

## Killer Cron Jobs Worth Adopting

| Cron Job | Interval | What It Does | PARAM Phase |
|----------|----------|-------------|-------------|
| **stale-worker-watchdog** | 15m | Kills workers whose kanban tasks no longer in_progress | Phase 6 |
| **kanban-flowkeeper** | 30m | LLM agent performing board hygiene: clears orphans, propagates unblocks | Phase 6 |
| **kanban-post-work-audit** | 30m | Audits completed tasks against checklist | Phase 6 |
| **inference-live-probe** | 4h | Tests every provider with real completions | Phase 3 |
| **web-image-staleness-check** | 1h | Compares deployed git SHA vs HEAD, triggers redeploy | Phase 4 |
| **vault-hindsight-sync** | 30m | Incremental vault → Hindsight sync with 90s budget | Phase 1 |

---

## What to NOT Adopt (Not Relevant to PARAM)

- **Dockerized Hermes**: PARAM runs via OMO session, not Docker. Not applicable unless we build TypeScript daemon.
- **hermes-pi container**: PARAM uses TokenEye + opencode-go for inference routing. `pi` is redundant.
- **NestJS/Next.js app stack**: Project-specific, not a pattern.

---

## Updated Priorities for PARAM ROADMAP

These findings suggest reordering some ROADMAP items:

| ROADMAP Item | Change | Reason |
|-------------|--------|--------|
| Skills whitelist | **New P0** (Phase 0.5) | Immediate token savings, enables Phase 2 (Skills) |
| Three-layer memory | Upgrade Phase 1 | Add Hindsight alongside Honcho; Obsidian vault as knowledge layer |
| Bitwarden secrets | **New P1** | Critical for security before any Phase 4+ work |
| Custom dispatcher hook | Upgrade Phase 6 | More sophisticated than planned kanban workflow |
| Provider fallback | **New P1** | Resilience for autonomous operation (Phase 3 dependency) |
| SearXNG | **New P2** | Replaces public search API dependency |
| launchd services | **New P2** | Host-level persistence for 24/7 operation |
