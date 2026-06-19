# PARAM — Honest Gap Analysis

**Date:** 2026-06-18
**Author:** PARAM / Jarvis
**Status:** Complete and unvarnished

---

## Executive Summary

PARAM today is an **MVP** — a thin but functional integration of OMO (OhMyOpenCode) and Hermes Agent via a 111-line Python MCP bridge (`param_hermes_mcp.py`) plus a dual-file identity system (`SOUL.md` + `AGENTS.md`). It adds concrete value over standalone Hermes, but the README oversells what actually exists. The ARCHITECTURE.md is honest about this — it explicitly labels the planned TypeScript core as "Conceptual Architecture (Future Source Layout)" and acknowledges the current implementation is an MVP.

---

## Q1: Is PARAM better than Hermes standalone?

**Answer: Marginally better in specific domains. Not transformative.**

### What PARAM genuinely adds:

| Layer | What It Is | Actual Value |
|-------|-----------|--------------|
| **MCP Bridge** | 111-line Python server exposing all Hermes tools to OMO with `hermes__` prefix | Working. Pass-through wrapper. No orchestration logic. |
| **Identity System** | SOUL.md (374 lines) + AGENTS.md | Real. Hermes has personalities but nothing this structured and persistent. PARAM's most genuine innovation. |
| **OMO Agent Pool** | Specialized agents (explore, librarian, oracle, metis, momus) for codebase work | Real. Hermes has `delegate_task` but OMO's pool is richer for software engineering tasks. |

### What PARAM claims but doesn't deliver:

| Claimed Feature | Reality |
|----------------|---------|
| **"Intent Router"** | No router code exists. The LLM decides which tool to call ad-hoc. ARCHITECTURE.md diagrams show a Router component that doesn't exist. |
| **"Self-evolving memory"** | Uses basic `MEMORY.md` + `USER.md` (77 lines total). Zero of Hermes's 8 pluggable memory providers activated. `hermes__memory` tool returns errors. |
| **"Multi-agent routing"** | Just OMO's built-in `task()` delegation. No PARAM-specific routing logic. |
| **"Full MCP tool surface"** | 1:1 pass-through. No unification, composition, or cross-tool orchestration. |

### Verdict

A user running Hermes standalone + OpenCode separately would get ~90% of what PARAM delivers. PARAM's differentiating value is: unified single-identity interaction, and access to OMO's code-specialized agents. The rest is aspiration documented as if it were reality.

---

## Q2: Is PARAM complete?

**Answer: No. It is an MVP with 10 planned core components, none built.**

The ARCHITECTURE.md lists these as "Conceptual Architecture (Future Source Layout)":

| Planned Component | Status | What It Would Do |
|------------------|--------|------------------|
| `src/index.ts` — Entry point | ❌ Not built | Standalone PARAM daemon |
| `src/core/memory.ts` — Memory engine | ❌ Not built | Self-evolving memory with dialectic reasoning |
| `src/core/scheduler.ts` — Cron/triggers | ❌ Not built | PARAM's own scheduler (using Hermes cron as stopgap) |
| `src/core/router.ts` — Intent routing | ❌ Not built | Actual code-based intent classification and routing |
| `src/bridges/api.ts` — HTTP API | ❌ Not built | REST API for external triggers |
| `src/agents/opencode.ts` — OMO bridge | ❌ Not built | Dedicated OMO integration (MCP bridge is stopgap) |
| `src/agents/hermes.ts` — Hermes bridge | ❌ Not built | Dedicated Hermes integration |
| `src/mcp/unified.ts` — Unified MCP | ❌ Not built | Cross-tool composition and orchestration |
| Hermes Telegram gateway adapter | ❌ Not built | Dedicated Telegram routing adapter |
| Tests | ❌ Empty | `tests/` directory exists but contains zero files |
| CI/CD | ❌ Empty | `.github/workflows/` directory empty |

---

## Detailed Capability Gaps

### 1. Persistent Memory — ⚠️ PARTIAL

**Current:** `MEMORY.md` (38 lines) + `USER.md` (39 lines). Updated manually. `hermes__memory` tool broken.

**Hermes offers 8 memory providers — none activated:**
- **Honcho**: Dialectic reasoning, multi-pass depth, cold/warm prompts, 5 bidirectional tools
- **Mem0**: LLM fact extraction, semantic search, reranking
- **Supermemory**: Full-session conversation ingest, multi-container mode
- **Byterover, Hindsight, Holographic, OpenViking, RetainDB**: Additional backends

**Gap:** Zero memory providers configured. No semantic recall. No dialectic reasoning loop.

### 2. Self-Learning & Evolving Skills — ❌ MISSING

**Current:** 71 static skills from Hermes catalog. No automated evolution.

**Hermes has:** Curator system for skill lifecycle management, but no automated creation from task outcomes.

**Gap:** No feedback loop from task completion → skill creation. No automated improvement of existing skills based on failures.

### 3. 24/7 Unattended Operation — ⚠️ PARTIAL

**Current:** 5 cron jobs total (2 PARAM + 3 Hermes). Sessions require active user.

**Gap:** No PARAM daemon that runs autonomously. No "wake and check" loop. No autonomous task discovery and execution.

### 4. macOS Desktop Operations — REMOVED FROM ROADMAP

**Decision:** macOS desktop automation phase removed per user directive. PARAM's primary runtime is NAS (Docker). MacBook is a worker node for OMO agent sessions — desktop automation is a capability available if needed, not a roadmap phase.

### 5. Kanban Workflow — ⚠️ AVAILABLE BUT UNCONFIGURED

**Current:** All kanban tools accessible (create, list, show, complete, block, unblock, link).

**Gap:** No PARAM-specific kanban board. No workflow configuration. No task decomposition playbook integrated.

### 6. Live 2-Way Telegram — ⚠️ LIKELY WORKS, UNVERIFIED

**Current:** Hermes gateway running. Telegram configured in config.yaml. `messages_read`/`messages_send` tools available.

**Gap:** Never verified end-to-end. No proactive message polling loop. No intent classification for incoming messages.

### 7. Cloudflare Tunnel — ❌ NOT DEPLOYED

**Current:** `cloudflared-setup.sh` script exists in `deploy/nas/`.

**Gap:** Not configured. No remote dashboard access. No secure tunnel to PARAM.

### 8. Multi-Channel Gateway — ⚠️ TELEGRAM ONLY (with Cloudflare in v2)

**Current:** Only Telegram enabled. Cloudflare tunnel on `*.aiforges.app` added in v2 roadmap for real-time access. Hermes supports 35 platforms.

**Available but not configured:** Discord, Slack, WhatsApp, Signal, Matrix, Email, SMS, DingTalk, WeCom, Feishu, QQ Bot, Google Chat, Teams, Home Assistant, Webhook, API server.

**Gap:** Single-channel. No multi-platform presence.

### 9. Gitea Self-Hosted Git — REMOVED FROM ROADMAP

**Decision:** Deferred to future per user directive. Not in current implementation plan.

### 9. Observability & Monitoring — ❌ MISSING

**Current:** No monitoring. No Langfuse. No middleware plugins.

**Gap:** No session metrics. No tool-call tracking beyond TokenEye. No performance monitoring.

### 10. Testing & CI/CD — ❌ MISSING

**Current:** `tests/` directory empty. `.github/workflows/` empty.

**Gap:** Zero automated tests. No CI pipeline. No integration validation.

### 11. Huly Integration — ✅ WORKS (via separate MCP)

**Current:** Huly MCP tools available through separate registration.

**Note:** This works but isn't through PARAM's bridge or orchestration.

---

## Architecture Honesty Note

The ARCHITECTURE.md (521 lines, located at `specs/ARCHITECTURE.md`) is the most honest document in the project. In Section "Conceptual Architecture (Future Source Layout)" it explicitly states:

> "The current implementation architecture (Python MCP bridge + AGENTS.md-based identity + OpenCode session integration) is the MVP. The TypeScript core represents the next evolution: a standalone PARAM daemon with integrated scheduling, memory, and multi-channel bridges."

This document aligns with that honesty. PARAM has a solid foundation and a clear architecture vision. The gap between the two is what this assessment documents.

---

## Reference: What Hermes Standalone Offers

- 91 tool implementations (browser, terminal, file, code execution, search, vision, TTS, image/video gen, kanban, cron, memory, delegation, etc.)
- 8 pluggable memory providers
- 35 platform gateway adapters
- Built-in cron scheduler with webhook triggers
- Kanban (SQLite-backed multi-agent work queue)
- Curator (automated skill lifecycle management)
- macOS desktop automation (computer_use)
- 6 terminal backends (local, Docker, SSH, Singularity, Modal, Daytona)
- Electron desktop app + TUI + CLI + dashboard
- Observability middleware (Langfuse, NeMo Relay)
- Plugin system with lifecycle hooks

PARAM currently uses ~35% of Hermes's available capabilities through the MCP bridge.

---

## Architecture Decisions (2026-06-18)

Key decisions made after Reddit analysis and user direction:

| Decision | Rationale |
|----------|-----------|
| **NAS as 24/7 runtime** | UGREEN NAS with Docker. Eliminates MacBook dependency for Telegram, cron, memory. |
| **MacBook as worker node** | OMO/OpenCode sessions for complex code work. When off, NAS handles autonomously. |
| **Cloudflare real-time Telegram** | Permanent tunnel on `*.aiforges.app`. Instant response, no inbound ports. |
| **OMO agents > Hermes profiles** | 10 named agents + 8 categories + team_mode is superior to static 4-profile model. |
| **TokenEye load balancing** | Already operational — balances two opencode-go accounts. Adding Nous free-tier. |
| **No macOS desktop phase** | Removed per user directive. |
| **No Gitea** | Deferred to future. |
| **Three-layer memory** | Honcho (dialectic) + Hindsight/pgvector (semantic) + Obsidian (human-readable). |
| **Skills whitelist** | Only load relevant skills per agent type. Immediate token savings. |
