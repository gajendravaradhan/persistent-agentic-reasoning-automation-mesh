# PARAM — Implementation Roadmap & Task Tracker

**Date:** 2026-06-18
**Based on:** `specs/ASSESSMENT.md` gap analysis
**Tracked in:** This file (git-versioned, always referenceable)

---

## How To Use This Document

- Each task has a checkbox `[ ]`, a priority (`P0`-`P3`), and estimated effort (`S`/`M`/`L`/`XL`)
- Mark `[x]` when verified complete with evidence
- Tasks are ordered by dependency; P0 must complete before P1
- Every task includes a **verification criterion** — must be provably done, not "probably working"

---

## Phase 0: Foundation Hardening (P0 — Prerequisites)

> Rationale: Fix broken things before building new things. A house with a cracked foundation cannot support new walls.

### 0.1 Fix `hermes__memory` Tool
- [ ] **0.1.1** Diagnose why `hermes__memory` returns "not available" despite `memory_enabled: true` in config
  - **Verify:** `hermes__memory` tool returns successful response with action=list
  - **Effort:** S
- [ ] **0.1.2** Fix the tool or document the root cause and workaround
  - **Verify:** Tool works or documented limitation with approved bypass
  - **Effort:** S

### 0.2 Fix Hermes CLI PATH
- [ ] **0.2.1** Add Hermes CLI to PATH so `hermes` command works from any directory
  - **Verify:** `which hermes` returns a valid path
  - **Effort:** S
- [ ] **0.2.2** Symlink or add to shell profile
  - **Verify:** New terminal sessions have `hermes` in PATH
  - **Effort:** S

### 0.3 Verify Telegram End-to-End
- [ ] **0.3.1** Send a test message to PARAM via Telegram
  - **Verify:** Message appears in Hermes gateway logs
  - **Effort:** S
- [ ] **0.3.2** Read the message via `hermes__messages_read`
  - **Verify:** Message content retrievable programmatically
  - **Effort:** S
- [ ] **0.3.3** Send a response via `hermes__messages_send`
  - **Verify:** Response delivered to Telegram chat
  - **Effort:** S
- [ ] **0.3.4** Document the full roundtrip in TROUBLESHOOTING.md
  - **Verify:** Doc updated with working commands and expected output
  - **Effort:** S

### 0.4 Update Stale Documentation
- [ ] **0.4.1** Update README.md to reflect actual MVP state (not aspirational claims)
  - **Verify:** README accurately describes what works vs what's planned
  - **Effort:** S
- [ ] **0.4.2** Remove caveman references from ARCHITECTURE.md session flow diagram (line 186)
  - **Verify:** No "caveman" in ARCHITECTURE.md
  - **Effort:** S
- [ ] **0.4.3** Add ASSESSMENT.md reference to README
  - **Verify:** README links to ASSESSMENT.md for "current state"
  - **Effort:** S

### 0.5 Git Commit Baseline
- [ ] **0.5.1** Commit all Phase 0 changes with descriptive message
  - **Verify:** `git status` clean, all files committed
  - **Effort:** S

---

## Phase 1: Memory & Learning Engine (P0)

> Rationale: Memory is the single highest-impact gap. Without memory, PARAM is amnesiac between sessions. With memory, every interaction compounds.

### 1.1 Activate Honcho Memory Provider
- [ ] **1.1.1** Install Honcho Python package in PARAM venv
  - **Verify:** `pip show honcho-ai` succeeds
  - **Effort:** S
- [ ] **1.1.2** Obtain and configure Honcho API key in `~/.hermes/.env`
  - **Verify:** `HONCHO_API_KEY` set in environment
  - **Effort:** S
- [ ] **1.1.3** Configure Honcho as active memory provider in `~/.hermes/config.yaml`
  - **Verify:** Hermes config references honcho under `memory.provider`
  - **Effort:** S
- [ ] **1.1.4** Restart Hermes gateway and verify memory provider activates
  - **Verify:** Gateway logs show Honcho initialization without errors
  - **Effort:** S
- [ ] **1.1.5** Run a test session and verify memories persist across sessions
  - **Verify:** Session A creates memory, Session B retrieves it
  - **Effort:** M

### 1.2 Configure Honcho Dialectic Reasoning
- [ ] **1.2.1** Set reasoning depth to 2 (multi-pass context injection)
  - **Verify:** Config shows `reasoning_depth: 2`
  - **Effort:** S
- [ ] **1.2.2** Verify cold prompt (first interaction) vs warm prompt (with context)
  - **Verify:** Logs show different prompt lengths for cold vs warm
  - **Effort:** S
- [ ] **1.2.3** Test proportional reasoning levels
  - **Verify:** Simple queries use depth 1, complex use depth 2-3
  - **Effort:** M

### 1.3 Memory Consolidation Automation
- [ ] **1.3.1** Create cron job for automated memory consolidation (weekly)
  - **Verify:** Cron job exists and triggers consolidation
  - **Effort:** S
- [ ] **1.3.2** Implement stale memory pruning (entries older than 30 days with no recall)
  - **Verify:** Stale entries auto-removed after 30 days
  - **Effort:** M
- [ ] **1.3.3** Implement deduplication of semantically similar memories
  - **Verify:** Two memories about same topic merged into one
  - **Effort:** M

### 1.4 Memory Verification Framework
- [ ] **1.4.1** Create test: write memory → read memory → verify content
  - **Verify:** Test passes
  - **Effort:** S
- [ ] **1.4.2** Create test: cross-session memory persistence
  - **Verify:** Test passes across two simulated sessions
  - **Effort:** M

---

## Phase 2: Self-Evolving Skills (P0)

> Rationale: Skills are PARAM's procedural memory. Static skills are documentation. Evolving skills are compounding capability.

### 2.1 Skill Creation from Task Outcomes
- [ ] **2.1.1** Implement post-task analysis: detect if a task involved a novel workflow
  - **Verify:** Novel workflow detection triggers skill creation prompt
  - **Effort:** M
- [ ] **2.1.2** Implement automated SKILL.md generation with YAML frontmatter
  - **Verify:** Generated skill passes `hermes skill validate`
  - **Effort:** M
- [ ] **2.1.3** Add user confirmation gate before skill creation
  - **Verify:** User prompted to approve/reject auto-generated skill
  - **Effort:** S
- [ ] **2.1.4** Create cron job for skill review (monthly): check usage, suggest pruning
  - **Verify:** Monthly report lists unused skills and suggests actions
  - **Effort:** M

### 2.2 Skill Improvement from Failures
- [ ] **2.2.1** Implement failure pattern detection across sessions
  - **Verify:** Same error type across 3+ sessions triggers improvement flag
  - **Effort:** M
- [ ] **2.2.2** Implement automated skill patching for known failure modes
  - **Verify:** Skill updated with pitfall section after failure detected
  - **Effort:** M
- [ ] **2.2.3** Add post-fix verification: retry the task that failed with updated skill
  - **Verify:** Updated skill resolves the original failure
  - **Effort:** M

### 2.3 Skill Metrics Dashboard
- [ ] **2.3.1** Track skill usage: invocation count, success rate, last used
  - **Verify:** Dashboard or report shows skill metrics
  - **Effort:** M
- [ ] **2.3.2** Surface unused skills (>60 days) for pruning review
  - **Verify:** List of unused skills surfaced in monthly report
  - **Effort:** S

---

## Phase 3: Autonomous Operation (P1)

> Rationale: PARAM's name includes "Persistent" and "Automation." Currently, it does neither without an active session.

### 3.1 Autonomous Check-in Loop
- [ ] **3.1.1** Create PARAM wake-and-check cron job (every 30 minutes)
  - **Verify:** Cron job fires, checks Telegram, system health, pending tasks
  - **Effort:** M
- [ ] **3.1.2** Implement pending-task detection: scan Hermes kanban, Huly issues, cron results
  - **Verify:** Autonomous check-in surfaces actionable items
  - **Effort:** M
- [ ] **3.1.3** Implement autonomous task execution for low-risk routine tasks
  - **Verify:** Health checks, log rotation, cache cleanup run without user
  - **Effort:** M
- [ ] **3.1.4** Create escalation protocol: urgent items → immediate Telegram notification
  - **Verify:** Critical alert triggers Telegram message within 5 minutes
  - **Effort:** M

### 3.2 Session-Less Cron Execution
- [ ] **3.2.1** Configure cron jobs to execute with full Hermes context (model, memory)
  - **Verify:** Cron job has access to memory, skills, tools
  - **Effort:** M
- [ ] **3.2.2** Add delivery confirmation: cron output delivered to Telegram
  - **Verify:** Telegram receives cron job results
  - **Effort:** S
- [ ] **3.2.3** Implement context injection for cron: last session summary fed into prompt
  - **Verify:** Cron job prompt includes relevant past context
  - **Effort:** M

### 3.3 Proactive Notification System
- [ ] **3.3.1** Define notification tiers: INFO, WARNING, CRITICAL
  - **Verify:** Tier definitions documented and implemented
  - **Effort:** S
- [ ] **3.3.2** Implement event-driven notifications (not just time-based)
  - **Verify:** TokenEye anomaly → notification; build failure → notification
  - **Effort:** M
- [ ] **3.3.3** Create notification preferences: per-user frequency, channels, quiet hours
  - **Verify:** User can configure notification preferences
  - **Effort:** M

---

## Phase 4: TypeScript Core (P1)

> Rationale: The ARCHITECTURE.md's planned TypeScript core is PARAM's long-term differentiator. A daemon that orchestrates OMO + Hermes independently.

### 4.1 Core Daemon Skeleton
- [ ] **4.1.1** Initialize TypeScript project with Bun runtime
  - **Verify:** `bun run src/index.ts` starts without error
  - **Effort:** M
- [ ] **4.1.2** Implement process lifecycle: start, health check, graceful shutdown
  - **Verify:** Daemon starts, responds to SIGTERM, logs clean shutdown
  - **Effort:** M
- [ ] **4.1.3** Implement config loading from YAML/JSON
  - **Verify:** Daemon reads config on startup, validates schema
  - **Effort:** M

### 4.2 Memory Engine (`src/core/memory.ts`)
- [ ] **4.2.1** Implement memory CRUD with Hermes memory provider abstraction
  - **Verify:** Write, read, update, delete memory entries programmatically
  - **Effort:** M
- [ ] **4.2.2** Implement semantic search over memory store
  - **Verify:** Query "what did I say about tokeneye" returns relevant memories
  - **Effort:** M
- [ ] **4.2.3** Implement context window assembly: relevant memories injected into prompts
  - **Verify:** Session startup includes contextually relevant memories
  - **Effort:** M

### 4.3 Scheduler (`src/core/scheduler.ts`)
- [ ] **4.3.1** Implement cron parser (human-readable + standard cron syntax)
  - **Verify:** "every 30m" and "0 */6 * * *" both parse correctly
  - **Effort:** M
- [ ] **4.3.2** Implement job queue with priority, retry, timeout
  - **Verify:** Job retries on failure, times out after limit
  - **Effort:** M
- [ ] **4.3.3** Implement job dependency graph (job B runs after job A succeeds)
  - **Verify:** Chained jobs execute in correct order
  - **Effort:** M

### 4.4 Intent Router (`src/core/router.ts`)
- [ ] **4.4.1** Define intent taxonomy (CODE, RESEARCH, COMMUNICATE, AUTOMATE, MONITOR)
  - **Verify:** Taxonomy documented with examples
  - **Effort:** S
- [ ] **4.4.2** Implement rule-based intent classification
  - **Verify:** "fix the login bug" → CODE, "check tokeneye" → MONITOR
  - **Effort:** M
- [ ] **4.4.3** Implement routing: intent → agent selection (OMO agent vs Hermes handler)
  - **Verify:** Intent routes to correct execution path
  - **Effort:** M

### 4.5 Bridges (`src/bridges/`)
- [ ] **4.5.1** Implement OMO bridge: spawn agents, collect results, handle errors
  - **Verify:** Bridge spawns explore agent and returns results
  - **Effort:** M
- [ ] **4.5.2** Implement Hermes bridge: call tools, handle tool errors, retry
  - **Verify:** Bridge calls `hermes__cronjob` and parses response
  - **Effort:** M
- [ ] **4.5.3** Implement HTTP API bridge (`src/bridges/api.ts`): REST endpoints for external triggers
  - **Verify:** `POST /api/trigger` accepts webhook and dispatches to router
  - **Effort:** M

### 4.6 Unified MCP Surface (`src/mcp/unified.ts`)
- [ ] **4.6.1** Implement cross-tool composition (chain hermes__search + omo_read)
  - **Verify:** Unified tool call orchestrates Hermes + OMO tools in sequence
  - **Effort:** M
- [ ] **4.6.2** Implement tool result normalization (unified response format)
  - **Verify:** Both Hermes and OMO tool results share common JSON schema
  - **Effort:** M

---

## Phase 5: macOS Desktop Integration (P1)

> Rationale: "My macOS independent operations" — explicit user requirement. PARAM must operate the desktop.

### 5.1 Orchestrated Desktop Workflows
- [ ] **5.1.1** Implement screenshot → analyze → act loop
  - **Verify:** PARAM captures screen, identifies an issue, performs corrective action
  - **Effort:** M
- [ ] **5.1.2** Implement scheduled desktop health checks (app responsiveness, disk, memory)
  - **Verify:** Cron job checks desktop health and reports to Telegram
  - **Effort:** M
- [ ] **5.1.3** Implement file-system monitoring and automated organization
  - **Verify:** Downloads folder auto-sorted, stale files flagged
  - **Effort:** M

### 5.2 Background Operation
- [ ] **5.2.1** Verify `computer_use` works with screen locked / user away
  - **Verify:** Desktop automation runs while screen is locked
  - **Effort:** M
- [ ] **5.2.2** Implement safe-mode: never click destructive buttons without confirmation
  - **Verify:** "Delete" / "Format" / "Uninstall" buttons require explicit approval
  - **Effort:** M

---

## Phase 6: Kanban Workflow (P1)

> Rationale: Structured multi-agent work execution. Currently accessible but unused.

### 6.1 PARAM Kanban Board
- [ ] **6.1.1** Create PARAM-specific kanban board
  - **Verify:** `hermes__kanban_list` shows PARAM board
  - **Effort:** S
- [ ] **6.1.2** Define workflow columns: Backlog → Ready → In Progress → Review → Done
  - **Verify:** Board has correct column structure
  - **Effort:** S
- [ ] **6.1.3** Implement auto-promotion from Backlog → Ready when dependencies clear
  - **Verify:** Task with cleared blockers auto-moves to Ready
  - **Effort:** M

### 6.2 Task Decomposition Playbook
- [ ] **6.2.1** Implement automated epic → task decomposition
  - **Verify:** "Implement memory engine" → 8-12 concrete sub-tasks
  - **Effort:** M
- [ ] **6.2.2** Implement task estimation with historical accuracy feedback
  - **Verify:** Estimations improve over time based on actual completion data
  - **Effort:** M

### 6.3 Autonomous Worker Dispatch
- [ ] **6.3.1** Implement worker claim: when task enters Ready, assign to appropriate agent
  - **Verify:** Ready task auto-assigned to correct agent profile
  - **Effort:** M
- [ ] **6.3.2** Implement progress tracking: worker heartbeats, timeout detection
  - **Verify:** Stalled task detected and reassigned after timeout
  - **Effort:** M

---

## Phase 7: Multi-Channel Gateway (P2)

> Rationale: Current single-channel (Telegram) limits reach. Hermes supports 35 platforms.

### 7.1 Additional Platform Activation
- [ ] **7.1.1** Activate Discord gateway
  - **Verify:** PARAM reachable via Discord DM
  - **Effort:** M
- [ ] **7.1.2** Activate Email gateway (send/receive)
  - **Verify:** PARAM sends email report, receives commands via email
  - **Effort:** M
- [ ] **7.1.3** Activate Webhook gateway for external service integration
  - **Verify:** GitHub webhook → PARAM processes event → responds
  - **Effort:** M

### 7.2 Unified Inbox
- [ ] **7.2.1** Implement cross-platform message aggregation
  - **Verify:** Messages from Telegram + Discord + Email visible in unified view
  - **Effort:** M
- [ ] **7.2.2** Implement response routing: reply via same channel message arrived on
  - **Verify:** Telegram message gets Telegram reply, Discord gets Discord
  - **Effort:** M

---

## Phase 8: Cloudflare & Remote Access (P2)

> Rationale: "Through Cloudflare" — explicit user requirement for remote PARAM access.

### 8.1 Cloudflare Tunnel Deployment
- [ ] **8.1.1** Install and configure `cloudflared`
  - **Verify:** `cloudflared tunnel list` shows active tunnel
  - **Effort:** M
- [ ] **8.1.2** Configure tunnel to expose PARAM dashboard and API
  - **Verify:** Dashboard accessible via `https://param.yourdomain.com`
  - **Effort:** M
- [ ] **8.1.3** Implement access controls (Cloudflare Access / Zero Trust)
  - **Verify:** Dashboard requires authentication
  - **Effort:** M
- [ ] **8.1.4** Add health check for tunnel status to PARAM monitoring
  - **Verify:** Tunnel health reported in status dashboard
  - **Effort:** S

---

## Phase 9: Observability & Monitoring (P2)

> Rationale: Can't improve what you can't measure.

### 9.1 Monitoring Infrastructure
- [ ] **9.1.1** Activate Hermes Langfuse plugin for session observability
  - **Verify:** Langfuse dashboard shows session traces
  - **Effort:** M
- [ ] **9.1.2** Create PARAM-specific metrics dashboard
  - **Verify:** Dashboard shows: sessions/day, tasks completed, errors, memory growth
  - **Effort:** M
- [ ] **9.1.3** Implement anomaly detection: unusual error rates, slow responses, memory bloat
  - **Verify:** Anomaly triggers Telegram notification
  - **Effort:** M

### 9.2 TokenEye Integration
- [ ] **9.2.1** Extend param-status.sh to include TokenEye cost metrics
  - **Verify:** Status dashboard shows: daily spend, tokens used, cost per task
  - **Effort:** S
- [ ] **9.2.2** Implement cost alert thresholds
  - **Verify:** Telegram alert when daily spend exceeds configured limit
  - **Effort:** M

---

## Phase 10: Testing & CI/CD (P2)

> Rationale: Zero tests today. Unacceptable for production aspirations.

### 10.1 Test Framework
- [ ] **10.1.1** Create test infrastructure: pytest for Python, bun test for TypeScript
  - **Verify:** `pytest` and `bun test` run without errors
  - **Effort:** M
- [ ] **10.1.2** Write MCP bridge integration tests
  - **Verify:** Tests validate tool discovery, dispatch, error handling
  - **Effort:** M
- [ ] **10.1.3** Write memory provider tests
  - **Verify:** CRUD operations, cross-session persistence, semantic search
  - **Effort:** M

### 10.2 CI/CD Pipeline
- [ ] **10.2.1** Create GitHub Actions workflow: lint → typecheck → test → build
  - **Verify:** PR triggers CI, all steps pass
  - **Effort:** M
- [ ] **10.2.2** Add integration test stage: spin up Hermes MCP, test tool availability
  - **Verify:** CI validates that all 64 Hermes tools are discoverable
  - **Effort:** M
- [ ] **10.2.3** Add deployment stage for NAS Docker deployment
  - **Verify:** Docker image built and pushed on main merge
  - **Effort:** M

---

## Phase 11: Security Hardening (P3)

> Rationale: Security debt accumulates silently.

### 11.1 Credential Hygiene
- [ ] **11.1.1** Audit all configuration files for hardcoded secrets
  - **Verify:** Zero secrets in git-tracked files
  - **Effort:** M
- [ ] **11.1.2** Implement `.env` validation on startup (required keys present, non-empty)
  - **Verify:** Startup fails with clear error if required keys missing
  - **Effort:** S
- [ ] **11.1.3** Add secret rotation cron job (monthly reminder, annual enforcement)
  - **Verify:** Cron job reminds to rotate API keys
  - **Effort:** S

### 11.2 Access Control
- [ ] **11.2.1** Implement Telegram user whitelist enforcement
  - **Verify:** Non-whitelisted users get polite rejection
  - **Effort:** S
- [ ] **11.2.2** Implement command authorization tiers (admin vs user)
  - **Verify:** Destructive commands require admin role
  - **Effort:** M

---

## Summary Statistics

| Phase | Tasks | Priority | Total Effort |
|-------|-------|----------|-------------|
| 0: Foundation | 13 | P0 | S-M |
| 1: Memory | 11 | P0 | S-M |
| 2: Skills | 9 | P0 | S-M |
| 3: Autonomous | 10 | P1 | M |
| 4: TypeScript Core | 18 | P1 | M-L |
| 5: macOS Desktop | 5 | P1 | M |
| 6: Kanban | 7 | P1 | S-M |
| 7: Multi-Channel | 5 | P2 | M |
| 8: Cloudflare | 4 | P2 | M |
| 9: Observability | 5 | P2 | S-M |
| 10: Testing/CI | 7 | P2 | M |
| 11: Security | 5 | P3 | S-M |

**Total: 99 tasks across 12 phases**

---

## Progress Tracking

| Phase | Completed | Total | % |
|-------|-----------|-------|---|
| 0: Foundation | 0 | 13 | 0% |
| 1: Memory | 0 | 11 | 0% |
| 2: Skills | 0 | 9 | 0% |
| 3: Autonomous | 0 | 10 | 0% |
| 4: TypeScript Core | 0 | 18 | 0% |
| 5: macOS Desktop | 0 | 5 | 0% |
| 6: Kanban | 0 | 7 | 0% |
| 7: Multi-Channel | 0 | 5 | 0% |
| 8: Cloudflare | 0 | 4 | 0% |
| 9: Observability | 0 | 5 | 0% |
| 10: Testing/CI | 0 | 7 | 0% |
| 11: Security | 0 | 5 | 0% |
| **TOTAL** | **0** | **99** | **0%** |

---

## Key Decisions Required From User

Before implementation begins, the following decisions need your input:

1. **Memory provider**: Honcho (most sophisticated) or Mem0 (simpler, semantic)? Or both staged?
2. **TypeScript runtime**: Bun (already installed) or Node.js?
3. **Domain for Cloudflare**: Do you have a domain to use, or should we use a `*.trycloudflare.com` tunnel?
4. **Discord/Email**: Worth activating now or defer to later?
5. **Implementation order**: Start with P0 (Foundation + Memory + Skills) first, or parallelize some P1?
6. **Git strategy**: One branch per phase, or all on main with feature flags?
