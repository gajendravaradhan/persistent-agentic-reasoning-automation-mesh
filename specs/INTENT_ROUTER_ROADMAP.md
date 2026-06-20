# PARAM Intent Router — Implementation Roadmap

**Date:** 2026-06-20
**Architecture:** `specs/INTENT_ROUTER_ARCHITECTURE.md`
**Verification:** Machine-backed via `scripts/verify-roadmap.py` — every [x] requires a corresponding `@check` function. No manual checkbox fraud.

---

## Phase IR-0: Foundation (P0)

### IR-0.1 Module Structure
- [ ] **IR-0.1.1** Create `src/router/` directory with `__init__.py`
  - **Verify:** Directory exists, `__init__.py` is importable
- [ ] **IR-0.1.2** Create `src/router/types.py` — Intent enum, ClassifiedIntent dataclass, RouteDecision dataclass, AuditEntry dataclass
  - **Verify:** All types importable, all enums have defined values
- [ ] **IR-0.1.3** Set up `tests/test_router/` directory with `__init__.py`
  - **Verify:** Test directory exists, pytest discovers tests

### IR-0.2 Classifier Core
- [ ] **IR-0.2.1** Implement rule engine with weighted keyword matching in `classifier.py`
  - **Verify:** All 10 intent types have at least 2 keyword patterns each
- [ ] **IR-0.2.2** Implement confidence scoring — rule matches produce confidence 0.0-1.0
  - **Verify:** Single keyword match produces confidence < 0.90; 3+ matches ≥ 0.90
- [ ] **IR-0.2.3** Implement multi-intent detection via conjunction patterns
  - **Verify:** "find the bug AND deploy the fix" → MULTI_INTENT
- [ ] **IR-0.2.4** Implement `classify()` — main entry: request → ClassifiedIntent
  - **Verify:** Clear text classification works for all defined intents

### IR-0.3 Safety Gates
- [ ] **IR-0.3.1** Implement `guard.py` with ConfidenceGuard (< 85% → fallback)
  - **Verify:** Confidence 0.70 routes to FALLBACK_LLM, 0.95 routes to PROCEED
- [ ] **IR-0.3.2** Implement SafetyGate — DANGEROUS intents block, MULTI_INTENT splits
  - **Verify:** DEPLOYMENT intent → BLOCKED. "find and deploy" → SPLIT with 2 sub-intents
- [ ] **IR-0.3.3** Implement RouteDecision — carries route, reason, and sub-intents
  - **Verify:** RouteDecision can be serialized to dict and reconstructed

### IR-0.4 Agent Routes
- [ ] **IR-0.4.1** Implement `routes.py` — INTENT_ROUTES mapping (intent → agent + method)
  - **Verify:** All 11 Intent values have a defined route
- [ ] **IR-0.4.2** Implement `get_route(intent) → AgentRoute` function
  - **Verify:** CODE_SEARCH → explore, CASUAL_CHAT → llm, UNKNOWN → llm

### IR-0.5 Audit System
- [ ] **IR-0.5.1** Implement `audit.py` — AuditLogger with JSONL persistence
  - **Verify:** Audit entries written to file, readable, parseable
- [ ] **IR-0.5.2** Implement `get_stats()` — accuracy, confidence distribution, route distribution
  - **Verify:** Stats function returns valid dict with all required fields
- [ ] **IR-0.5.3** Implement request de-duplication via SHA256 hash
  - **Verify:** Same request twice → single audit entry (de-duped)

### IR-0.6 Router Orchestrator
- [ ] **IR-0.6.1** Implement `__init__.py` — `classify_and_route(request, context)` main entry
  - **Verify:** Full pipeline: classify → conf. guard → safety gate → route → audit
- [ ] **IR-0.6.2** Implement fallback chain: rule → LLM → direct LLM answer
  - **Verify:** Unknown intent → routed to LLM with full request context
- [ ] **IR-0.6.3** Implement split routing for multi-intent requests
  - **Verify:** MULTI_INTENT with 2 sub-intents → each routed independently

---

## Phase IR-1: Quality & Safety (P0)

### IR-1.1 Test Suite (>90% coverage)
- [ ] **IR-1.1.1** Type tests — Intent enum, dataclass validation
  - **Verify:** All enum values unique, all dataclass fields typed
- [ ] **IR-1.1.2** Classifier tests — rule engine accuracy on 50+ labeled examples
  - **Verify:** ≥ 90% accuracy on validation set, all intents covered
- [ ] **IR-1.1.3** Confidence guard tests — threshold behavior, edge cases
  - **Verify:** Boundary values (0.84, 0.85, 0.86) produce correct decisions
- [ ] **IR-1.1.4** Safety gate tests — dangerous intents blocked, multi-intent split
  - **Verify:** All 3 DANGEROUS intents blocked, MULTI_INTENT correctly split
- [ ] **IR-1.1.5** Route mapping tests — every intent has a valid route
  - **Verify:** No intent produces None route
- [ ] **IR-1.1.6** Orchestrator integration tests — end-to-end pipeline
  - **Verify:** Request → routed to correct agent with correct params
- [ ] **IR-1.1.7** Audit logger tests — write, read, stats, de-dup
  - **Verify:** 100 entries written → all parseable, stats correct
- [ ] **IR-1.1.8** Multi-intent tests — split, sub-intent routing
  - **Verify:** "find X and deploy Y" → CODE_SEARCH + DEPLOYMENT (blocked)
- [ ] **IR-1.1.9** Coverage threshold met: >90% overall
  - **Verify:** `pytest --cov=src/router --cov-fail-under=90` passes

### IR-1.2 Edge Case Hardening
- [ ] **IR-1.2.1** Empty request → UNKNOWN, routed to LLM
  - **Verify:** "" → confidence 0.0, route FALLBACK_LLM
- [ ] **IR-1.2.2** Very long request (>2000 chars) → truncated, classified on first 500
  - **Verify:** 3000-char request classified correctly from first 500 chars
- [ ] **IR-1.2.3** Mixed-language requests → handled gracefully
  - **Verify:** "deploy करना है" → detected as INFRASTRUCTURE
- [ ] **IR-1.2.4** Rapid repeated classification → cache hit, no re-classification
  - **Verify:** Same request 5x in 1 second → 1 audit entry, 5 cache hits
- [ ] **IR-1.2.5** No regex catastrophic backtracking — all patterns bounded
  - **Verify:** Timeout test: worst-case input classifies in < 100ms

---

## Phase IR-2: Integration & Verification (P1)

### IR-2.1 Verification System
- [ ] **IR-2.1.1** Add `@check` functions to `scripts/verify-roadmap.py` for all IR-0.x and IR-1.x tasks
  - **Verify:** Every task in this roadmap has a corresponding check function
- [ ] **IR-2.1.2** Run `python3 scripts/verify-roadmap.py --roadmap specs/INTENT_ROUTER_ROADMAP.md`
  - **Verify:** All verifiable [x] tasks pass. 0 failed. Manual-only tasks flagged.
- [ ] **IR-2.1.3** Ensure no manual checkbox fraud — progress table derived from verification

### IR-2.2 CI Integration
- [ ] **IR-2.2.1** Add router tests to CI workflow (`.github/workflows/ci.yml`)
  - **Verify:** Router tests run on push, coverage checked
- [ ] **IR-2.2.2** Add router import validation to CI
  - **Verify:** `from src.router import classify_and_route` succeeds in CI

### IR-2.3 Langfuse Tracing
- [ ] **IR-2.3.1** Add router classification events to Langfuse traces
  - **Verify:** Router decisions appear in Langfuse dashboard alongside LLM traces

---

## Summary Statistics

| Phase | Tasks | Priority | Effort |
|-------|-------|----------|--------|
| IR-0: Foundation | 15 | P0 | M-L |
| IR-1: Quality & Safety | 14 | P0 | M |
| IR-2: Integration | 5 | P1 | S |

**Total: 34 tasks across 3 phases**

---

## Progress Tracking

| Phase | Completed | Total | % |
|-------|-----------|-------|---|
| IR-0: Foundation | 0 | 15 | 0% |
| IR-1: Quality & Safety | 0 | 14 | 0% |
| IR-2: Integration | 0 | 5 | 0% |
| **TOTAL** | **0** | **34** | **0%** |

---

## Success Criteria

1. **Classification accuracy ≥ 90%** on a held-out test set of 50+ labeled prompts
2. **Zero unapproved infrastructure actions** — DEPLOY/INFRA/SEC always gated
3. **Token savings measurable** — rule-based classification costs 0 tokens, avoidable LLM calls reduced
4. **100% machine-verifiable** — every [x] task has a `@check` function
5. **>90% test coverage** — pytest with coverage threshold enforced
6. **Full audit trail** — every routing decision logged and queryable
