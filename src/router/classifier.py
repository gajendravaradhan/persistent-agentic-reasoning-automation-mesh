"""Intent classifier — rule-based classification engine.

Two-tier architecture (Tier 1 only in this module; Tier 2 LLM
fallback lives in the pipeline orchestrator).

All 10 non-UNKNOWN intent types have 2+ keyword patterns.
Confidence scoring: single match < 0.90, 3+ matches >= 0.90.
"""

import re
from collections import defaultdict
from typing import Optional

from .types import ClassifiedIntent, Intent

# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------
# Each entry: (compiled_pattern, intent, base_score)
# At least 2 patterns per intent type (excluding UNKNOWN).

RAW_RULES: list[tuple[str, Intent, float]] = [
    # -- CODE_SEARCH (3 patterns) --
    (r"\b(find|search|grep|locate|where is|look for)\b.*\b(code|file|function|class|module|definition)\b",
     Intent.CODE_SEARCH, 0.85),
    (r"\b(show|get|list|read|open|print|dump|display|cat)\b.*\b(file|config|code|source|definition|content|contents)\b",
     Intent.CODE_SEARCH, 0.80),
    (r"\b(where|how).*\b(defined|declared|implemented|used|called|imported)\b",
     Intent.CODE_SEARCH, 0.80),

    # -- CODE_CHANGE (3 patterns) --
    (r"\b(add|create|implement|build|write|fix|change|update|modify)\b.*\b(code|function|endpoint|route|module|feature|class|method)\b",
     Intent.CODE_CHANGE, 0.85),
    (r"\b(refactor|rename|move|delete|remove|rewrite|replace|extract)\b.*\b(function|class|file|code|method|variable|block)\b",
     Intent.CODE_CHANGE, 0.80),
    (r"\b(commit|push|submit|merge)\b.*\b(change|code|patch|diff|pr|pull request)\b",
     Intent.CODE_CHANGE, 0.80),

    # -- MEMORY_RETRIEVAL (2 patterns) --
    (r"\b(what did we|recall|retrieve|yesterday|last time|remember when|do you remember)\b",
     Intent.MEMORY_RETRIEVAL, 0.85),
    (r"\b(what|where|who)\b.*\b(did we|was.*said|mentioned|discussed|talked about|decided|covered)\b",
     Intent.MEMORY_RETRIEVAL, 0.80),

    # -- MEMORY_WRITE (3 patterns) --
    (r"\b(remember|save|store)\b.*\b(prefer|setting|config|preference|choice|option|layout)\b",
     Intent.MEMORY_WRITE, 0.85),
    (r"\b(save|keep|store|note|record|log|write down)\b.*\b(this|that|it|the)\b.*\b(memory|note|preference|fact|detail|info)\b",
     Intent.MEMORY_WRITE, 0.80),
    (r"\bremember that\b", Intent.MEMORY_WRITE, 0.85),

    # -- INFRASTRUCTURE (2 patterns) --
    (r"\b(restart|docker compose|ssh|systemctl|service)\b",
     Intent.INFRASTRUCTURE, 0.85),
    (r"\b(container|service|server|daemon|process|port|network|volume)\b.*\b(start|stop|restart|status|check|list|inspect|logs|up|down)\b",
     Intent.INFRASTRUCTURE, 0.80),

    # -- DEPLOYMENT (2 patterns) --
    (r"\b(push to|deploy|publish|release|rollout)\b.*\b(nas|production|staging|compose|server|live|prod|stage)\b",
     Intent.DEPLOYMENT, 0.85),
    (r"\b(update compose|upgrade service|stack deploy|rolling update|canary|blue.green|cut over)\b",
     Intent.DEPLOYMENT, 0.80),

    # -- SECURITY (2 patterns) --
    (r"\b(audit|scan|vulnerability|secret|CVE|security|exploit)\b",
     Intent.SECURITY, 0.85),
    (r"\b(encrypt|decrypt|key|token|certificate|password|credential|api key|auth)\b.*\b(check|verify|audit|review|rotate|inspect|validate)\b",
     Intent.SECURITY, 0.80),

    # -- CASUAL_CHAT (2 patterns) --
    (r"\b(hello|hi|hey|thanks|thank you|ok|bye|goodbye|cheers|np|no problem)\b",
     Intent.CASUAL_CHAT, 0.95),
    (r"\b(how are you|what can you do|who are you|good morning|good evening|nice to meet|what.up|sup)\b",
     Intent.CASUAL_CHAT, 0.90),

    # -- ANALYSIS (3 patterns) --
    (r"\b(analyze|compare|evaluate|assess|trade.?off|review)\b",
     Intent.ANALYSIS, 0.85),
    (r"\b(complexity|performance|benchmark|profile|metric|statistics|trend|distribution)\b.*\b(analysis|report|summary|review|of|for|across)\b",
     Intent.ANALYSIS, 0.80),
    (r"\b(pros and cons|tradeoffs|comparison|versus|vs)\b",
     Intent.ANALYSIS, 0.85),

    # -- MULTI_INTENT (2 patterns — conjunction-based) --
    (r"\band\b.*\b(deploy|restart|docker|code|function|search|find|build|create|add|push|fix|change)\b",
     Intent.MULTI_INTENT, 0.85),
    (r"\bthen\b.*\b(deploy|push|build|run|execute|start|restart|commit)\b",
     Intent.MULTI_INTENT, 0.80),
]

# Compiled at module load time
RULES: list[tuple[re.Pattern, Intent, float]] = [
    (re.compile(pattern, re.IGNORECASE), intent, score)
    for pattern, intent, score in RAW_RULES
]

# ---------------------------------------------------------------------------
# Multi-intent conjunction patterns
# ---------------------------------------------------------------------------
MULTI_INTENT_PATTERNS: list[re.Pattern] = [
    re.compile(r"\band\b.*\b(deploy|restart|docker|code|function|search|find|build|create|add|push|fix)\b", re.IGNORECASE),
    re.compile(r"\bthen\b.*\b(deploy|push|build|run|execute|start|restart)\b", re.IGNORECASE),
]


class IntentClassifier:
    """Lightweight rule-based intent classifier.

    Operates as Tier 1 of the two-tier classification system.
    Tier 2 (LLM fallback) is invoked externally when confidence < 85%.
    """

    def classify(self, request: str, context: Optional[dict] = None) -> ClassifiedIntent:
        """Classify a user request into an intent.

        Steps:
          1. Empty / whitespace-only → UNKNOWN (0.0).
          2. Request > 2000 characters → truncate to first 500.
          3. Rule-based matching against all patterns.
          4. Confidence computation + multi-intent detection.

        Args:
            request: Raw user input string.
            context: Optional session context (ignored in Tier 1).

        Returns:
            ClassifiedIntent with the best-matching intent, confidence, and method.
        """
        if not request or not request.strip():
            return ClassifiedIntent(Intent.UNKNOWN, 0.0, method="rule")

        # Truncate overly long requests
        if len(request) > 2000:
            request = request[:500]

        intent, confidence = self._classify_rules(request, context)
        return ClassifiedIntent(intent, confidence, method="rule")

    def _classify_rules(
        self, request: str, context: Optional[dict] = None
    ) -> tuple[Intent, float]:
        """Apply rule-based pattern matching.

        Returns:
            (Intent, confidence) — the best single intent or MULTI_INTENT.
        """
        matches: list[tuple[Intent, float]] = []

        for pattern, intent, score in RULES:
            if pattern.search(request):
                matches.append((intent, score))

        if not matches:
            return Intent.UNKNOWN, 0.0

        # Multi-intent detection — conjunction patterns or 3+ distinct intents
        if self._is_multi_intent(request, matches):
            return Intent.MULTI_INTENT, self._compute_multi_confidence(matches)

        # Group matches by intent, pick the one with the highest score
        intent_scores: dict[Intent, list[float]] = defaultdict(list)
        for intent, score in matches:
            intent_scores[intent].append(score)

        best_intent = max(intent_scores, key=lambda i: max(intent_scores[i]))
        scores = intent_scores[best_intent]

        return best_intent, self._compute_confidence(scores)

    def _is_multi_intent(self, request: str, matches: list[tuple[Intent, float]]) -> bool:
        """Return True if the request appears to contain multiple intents."""
        # Check explicit conjunction patterns first
        for pattern in MULTI_INTENT_PATTERNS:
            if pattern.search(request):
                return True

        # Check if 3+ *different* intent types matched (strong multi-intent signal)
        unique_intents = {intent for intent, _ in matches if intent != Intent.MULTI_INTENT}
        return len(unique_intents) >= 3

    def _compute_confidence(self, scores: list[float]) -> float:
        """Compute confidence from matched keyword scores.

        Rules:
          - single match → < 0.90
          - 2 matches    → moderate boost (up to 0.95)
          - 3+ matches   → >= 0.90

        Args:
            scores: Raw base scores from matched rules.

        Returns:
            Rounded confidence value.
        """
        count = len(scores)
        max_score = max(scores)

        if count == 0:
            return 0.0
        if count == 1:
            return round(min(max_score, 0.89), 2)
        if count == 2:
            return round(min(max_score + 0.05, 0.95), 2)
        # 3+
        return round(min(0.99, 0.85 + 0.03 * (count - 1)), 2)

    def _compute_multi_confidence(self, matches: list[tuple[Intent, float]]) -> float:
        """Confidence for multi-intent detections based on breadth of signals."""
        unique_count = len({intent for intent, _ in matches})
        return round(min(0.95, 0.80 + 0.05 * unique_count), 2)


_classifier = IntentClassifier()


def classify(request: str, context: dict = None) -> "ClassifiedIntent":
    """Module-level entry point for intent classification."""
    return _classifier.classify(request, context or {})
