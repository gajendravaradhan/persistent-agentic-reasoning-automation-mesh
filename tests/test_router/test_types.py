"""Tests for Intent Router types and data classes."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

# These imports will fail until core-dev delivers types.py
# We import dynamically in each test to give clear error messages


class TestIntentEnum:
    def test_all_intents_defined(self):
        from router.types import Intent
        expected = [
            "CODE_SEARCH", "CODE_CHANGE", "MEMORY_RETRIEVAL", "MEMORY_WRITE",
            "INFRASTRUCTURE", "DEPLOYMENT", "SECURITY", "CASUAL_CHAT",
            "ANALYSIS", "MULTI_INTENT", "UNKNOWN",
        ]
        values = [i.value for i in Intent]
        for e in expected:
            assert e in values, f"Missing intent: {e}"
        assert len(Intent) == len(expected)

    def test_no_duplicate_values(self):
        from router.types import Intent
        values = [i.value for i in Intent]
        assert len(values) == len(set(values))


class TestClassifiedIntent:
    def test_creation(self):
        from router.types import ClassifiedIntent, Intent
        ci = ClassifiedIntent(Intent.CODE_SEARCH, 0.92, "rule")
        assert ci.intent == Intent.CODE_SEARCH
        assert ci.confidence == 0.92
        assert ci.method == "rule"

    def test_default_method(self):
        from router.types import ClassifiedIntent, Intent
        ci = ClassifiedIntent(Intent.CASUAL_CHAT, 0.95)
        assert ci.method == "rule"

    def test_confidence_bounds(self):
        from router.types import ClassifiedIntent, Intent
        # Min
        ci = ClassifiedIntent(Intent.UNKNOWN, 0.0)
        assert ci.confidence == 0.0
        # Max
        ci = ClassifiedIntent(Intent.CASUAL_CHAT, 1.0)
        assert ci.confidence == 1.0

    def test_multi_intent_with_data(self):
        from router.types import ClassifiedIntent, Intent
        ci = ClassifiedIntent(Intent.MULTI_INTENT, 0.88, "rule")
        assert ci.intent == Intent.MULTI_INTENT


class TestRouteDecision:
    def test_proceed(self):
        from router.types import RouteDecision
        rd = RouteDecision(route="PROCEED", reason="Confidence OK")
        assert rd.route == "PROCEED"
        assert rd.reason == "Confidence OK"

    def test_block(self):
        from router.types import RouteDecision
        rd = RouteDecision(route="BLOCK", reason="Dangerous intent")
        assert rd.route == "BLOCK"

    def test_split_with_sub_intents(self):
        from router.types import RouteDecision, ClassifiedIntent, Intent
        sub = [
            ClassifiedIntent(Intent.CODE_SEARCH, 0.90, "rule"),
            ClassifiedIntent(Intent.DEPLOYMENT, 0.88, "rule"),
        ]
        rd = RouteDecision(route="SPLIT", reason="Multi-intent detected", intents=sub)
        assert rd.route == "SPLIT"
        assert len(rd.intents) == 2

    def test_fallback_llm(self):
        from router.types import RouteDecision
        rd = RouteDecision(route="FALLBACK_LLM", reason="Low confidence")
        assert rd.route == "FALLBACK_LLM"

    def test_serialize_deserialize(self):
        from router.types import RouteDecision, ClassifiedIntent, Intent
        rd = RouteDecision(route="PROCEED", reason="OK")
        d = {"route": rd.route, "reason": rd.reason, "intents": None}
        rd2 = RouteDecision(**d)
        assert rd2.route == "PROCEED"
        assert rd2.reason == "OK"


class TestAuditEntry:
    def test_creation(self):
        from datetime import datetime
        from router.types import AuditEntry
        ts = datetime.now()
        ae = AuditEntry(
            timestamp=ts,
            request_hash="abc123",
            original_request="find auth middleware",
            intent="CODE_SEARCH",
            confidence=0.92,
            classification_method="rule",
            route="explore",
            guard_decisions=["PROCEED"],
            outcome="routed",
            latency_ms=5,
        )
        assert ae.request_hash == "abc123"
        assert ae.confidence == 0.92
        assert ae.outcome == "routed"
