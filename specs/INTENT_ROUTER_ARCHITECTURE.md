# PARAM Intent Router — Architecture

## Problem

Every user request currently hits the Hermes LLM directly. The LLM decides ad-hoc what to do — spawn an explore agent, call a tool, answer directly. This wastes tokens on simple tasks and gives the LLM inappropriate authority over infrastructure decisions.

## Solution

A lightweight intent classification and routing layer that sits between the user and the LLM. When confident, routes to the cheapest appropriate agent. When uncertain, falls back to the LLM. When dangerous, gates the request.

## Architecture

```
                        ┌──────────────────────┐
                        │    User Request        │
                        └──────────┬───────────┘
                                   │
                        ┌──────────▼───────────┐
                        │   IntentClassifier    │
                        │   (rule-based + LLM    │
                        │    fallback)           │
                        └──────────┬───────────┘
                                   │ (intent, confidence)
                        ┌──────────▼───────────┐
                        │   ConfidenceGuard     │
                        │   confidence < 85%?    │───► fallback to LLM
                        └──────────┬───────────┘
                                   │ confidence ≥ 85%
                        ┌──────────▼───────────┐
                        │   SafetyGate          │
                        │   INFRA/DEPLOY/SEC?    │───► require user approval
                        │   or multi-intent?     │───► split and route
                        └──────────┬───────────┘
                                   │ safe, single intent
                        ┌──────────▼───────────┐
                        │   AgentRouter         │
                        │   intent → agent map   │
                        │   CODE_SEARCH → explore│
                        │   MEMORY → honcho      │
                        │   CASUAL → LLM         │
                        └──────────┬───────────┘
                                   │
                        ┌──────────▼───────────┐
                        │   AuditLogger         │
                        │   log: intent, conf,   │
                        │   route, outcome       │
                        └──────────────────────┘
```

## Component Design

### 1. Intent Types (`types.py`)

```python
class Intent(Enum):
    CODE_SEARCH = "code_search"       # "find where auth is defined"
    CODE_CHANGE = "code_change"       # "add a login endpoint"
    MEMORY_RETRIEVAL = "memory"       # "what did we discuss yesterday"
    MEMORY_WRITE = "memory_write"     # "remember that I prefer tabs"
    INFRASTRUCTURE = "infra"          # "deploy docker", "restart service"
    DEPLOYMENT = "deploy"             # "push to NAS", "update compose"
    SECURITY = "security"             # "audit", "scan for secrets"
    CASUAL_CHAT = "casual"            # "hello", "what can you do"
    ANALYSIS = "analysis"             # "evaluate", "compare", "assess"
    MULTI_INTENT = "multi"            # "find the bug AND deploy the fix"
    UNKNOWN = "unknown"               # cannot classify → LLM
```

### 2. Classifier (`classifier.py`)

Two-tier classification:

**Tier 1 — Rule-based (fast, deterministic, no token cost):**
- Keyword matching with weighted scoring
- Pattern recognition (regex, command patterns)
- Context awareness (previous intent, session state)

**Tier 2 — LLM fallback (slow, expensive, accurate):**
- Only invoked when rule-based confidence < 85%
- Uses a small, fast model for classification prompt
- Returns intent + confidence score

```python
class IntentClassifier:
    def classify(self, request: str, context: dict = None) -> ClassifiedIntent:
        # Tier 1: rule-based
        intent, confidence = self._classify_rules(request, context)
        if confidence >= 0.85:
            return ClassifiedIntent(intent, confidence, method="rule")

        # Tier 2: LLM fallback
        intent, confidence = self._classify_llm(request, context)
        return ClassifiedIntent(intent, confidence, method="llm")
```

### 3. Rule Engine (`classifier.py` — internal)

```python
RULES = [
    # Pattern: (regex, intent, base_score)
    (r"\b(find|search|grep|locate|where is|look for)\b.*\b(code|file|function|class|module)\b", Intent.CODE_SEARCH, 0.90),
    (r"\b(deploy|push|restart|docker compose|ssh)\b", Intent.INFRASTRUCTURE, 0.85),
    (r"\b(remember|save|store)\b.*\b(prefer|setting|config)\b", Intent.MEMORY_WRITE, 0.90),
    (r"\b(what did we|recall|retrieve|yesterday|last time)\b", Intent.MEMORY_RETRIEVAL, 0.85),
    (r"\b(hello|hi|hey|thanks|ok|bye)\b", Intent.CASUAL_CHAT, 0.95),
    (r"\b(audit|scan|vulnerability|secret|CVE|security)\b", Intent.SECURITY, 0.85),
    (r"\b(analyze|compare|evaluate|assess|tradeoff)\b", Intent.ANALYSIS, 0.85),
    (r"\b(add|create|implement|build|write|fix|change|update|modify)\b.*\b(code|function|endpoint|route|module)\b", Intent.CODE_CHANGE, 0.85),
]

# Multi-intent detection: conjunctions + 2+ intent matches
MULTI_INTENT_PATTERNS = [
    r"\band\b.*\b(deploy|restart|docker|code|function)\b",
    r"\bthen\b.*\b(deploy|push|build)\b",
]
```

### 4. Confidence Guard (`guard.py`)

```python
CONFIDENCE_THRESHOLD = 0.85

class ConfidenceGuard:
    def check(self, classified: ClassifiedIntent) -> RouteDecision:
        if classified.confidence < CONFIDENCE_THRESHOLD:
            return RouteDecision(
                route=Route.FALLBACK_LLM,
                reason=f"Confidence {classified.confidence:.2f} < {CONFIDENCE_THRESHOLD}"
            )
        return RouteDecision(route=Route.PROCEED)

class RouteDecision:
    route: Route          # PROCEED, FALLBACK_LLM, BLOCK, SPLIT
    reason: str           # Human-readable explanation
    intents: list = None  # For SPLIT: list of (intent, text)
```

### 5. Safety Gate (`guard.py`)

```python
DANGEROUS_INTENTS = {Intent.DEPLOYMENT, Intent.INFRASTRUCTURE, Intent.SECURITY}

class SafetyGate:
    def check(self, classified: ClassifiedIntent) -> RouteDecision:
        if classified.intent in DANGEROUS_INTENTS:
            return RouteDecision(
                route=Route.BLOCK,
                reason=f"Intent {classified.intent.value} requires user approval"
            )
        if classified.intent == Intent.MULTI_INTENT:
            return self._handle_multi_intent(classified)
        return RouteDecision(route=Route.PROCEED)

    def _handle_multi_intent(self, classified):
        sub_intents = self._split_intents(classified)
        return RouteDecision(route=Route.SPLIT, intents=sub_intents)
```

### 6. Agent Router (`routes.py`)

```python
INTENT_ROUTES = {
    Intent.CODE_SEARCH: AgentRoute(agent="explore", method="task"),
    Intent.CODE_CHANGE: AgentRoute(agent="llm", method="delegate"),
    Intent.MEMORY_RETRIEVAL: AgentRoute(agent="honcho", method="recall"),
    Intent.MEMORY_WRITE: AgentRoute(agent="hermes", method="memory_write"),
    Intent.CASUAL_CHAT: AgentRoute(agent="llm", method="direct"),
    Intent.ANALYSIS: AgentRoute(agent="oracle", method="task"),
    Intent.SECURITY: AgentRoute(agent="llm", method="direct", requires_approval=True),
    Intent.INFRASTRUCTURE: AgentRoute(agent="llm", method="direct", requires_approval=True),
    Intent.DEPLOYMENT: AgentRoute(agent="llm", method="direct", requires_approval=True),
    Intent.UNKNOWN: AgentRoute(agent="llm", method="direct"),
    Intent.MULTI_INTENT: AgentRoute(agent="router", method="split"),
}
```

### 7. Audit Logger (`audit.py`)

```python
@dataclass
class AuditEntry:
    timestamp: datetime
    request_hash: str       # SHA256 of normalized request (de-duplication)
    original_request: str   # First 200 chars
    intent: str
    confidence: float
    classification_method: str  # "rule" or "llm"
    route: str
    guard_decisions: list
    outcome: str            # "routed", "fallback", "blocked", "split"
    latency_ms: int

class AuditLogger:
    def log(self, entry: AuditEntry):
        # Write to JSONL file
        # Also update metrics (accuracy tracking)

    def get_stats(self) -> dict:
        # Return classification accuracy, confidence distribution,
        # route distribution, guard trigger rate
```

## Safety Properties

| Property | How |
|----------|-----|
| **Default to safe** | Unknown/low-confidence → LLM. Never guess. |
| **Infrastructure gate** | DEPLOY/INFRA/SEC → block, require approval |
| **Multi-intent handling** | "find AND deploy" → split, route separately |
| **Audit trail** | Every routing decision logged with reason |
| **Override** | User can always say "no, route as CASUAL" |
| **Rollback** | Any infrastructure action is reversible |
| **Token savings** | Rule-based classification costs zero tokens |
| **Drift detection** | Audit stats show if classification accuracy degrades |

## Integration Points

1. **MCP Bridge**: Router is callable as `router.classify_and_route(request)`
2. **Hermes**: Router runs before the LLM sees the request
3. **OMO**: Router dispatches to `task(subagent_type="explore", ...)` or equivalent
4. **Verification**: Every router function has a `@check` in verify-roadmap.py
5. **Langfuse**: Router decisions traced alongside LLM traces

## Performance Budget

- Rule-based classification: < 5ms per request
- LLM fallback classification: < 500ms per request
- Audit logging: < 1ms per request
- Total overhead when routing: < 10ms
