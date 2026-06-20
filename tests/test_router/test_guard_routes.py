"""Tests for guard.py (ConfidenceGuard + SafetyGate) and routes.py."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


class TestConfidenceGuard:
    def test_high_confidence_proceeds(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import ConfidenceGuard, Route
        g = ConfidenceGuard()
        ci = ClassifiedIntent(Intent.CODE_SEARCH, 0.95, "rule")
        rd = g.check(ci)
        assert rd.route in (Route.PROCEED, "proceed")

    def test_low_confidence_falls_back(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import ConfidenceGuard, Route
        g = ConfidenceGuard()
        ci = ClassifiedIntent(Intent.CODE_SEARCH, 0.60, "rule")
        rd = g.check(ci)
        assert rd.route in (Route.FALLBACK_LLM, "fallback_llm")

    def test_exact_threshold_proceeds(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import ConfidenceGuard, Route
        g = ConfidenceGuard()
        ci = ClassifiedIntent(Intent.CODE_SEARCH, 0.85, "rule")
        rd = g.check(ci)
        assert rd.route in (Route.PROCEED, "proceed")

    def test_just_below_threshold_falls_back(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import ConfidenceGuard, Route
        g = ConfidenceGuard()
        ci = ClassifiedIntent(Intent.CODE_SEARCH, 0.849, "rule")
        rd = g.check(ci)
        assert rd.route in (Route.FALLBACK_LLM, "fallback_llm")


class TestSafetyGate:
    def test_dangerous_intent_blocked(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import SafetyGate, Route
        g = SafetyGate()
        for intent in [Intent.DEPLOYMENT, Intent.INFRASTRUCTURE, Intent.SECURITY]:
            ci = ClassifiedIntent(intent, 0.95, "rule")
            rd = g.check(ci)
            assert rd.route in (Route.BLOCK, "block"), f"{intent.value} should BLOCK"

    def test_safe_intent_proceeds(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import SafetyGate, Route
        g = SafetyGate()
        for intent in [Intent.CODE_SEARCH, Intent.CASUAL_CHAT, Intent.MEMORY_RETRIEVAL]:
            ci = ClassifiedIntent(intent, 0.95, "rule")
            rd = g.check(ci)
            assert rd.route in (Route.PROCEED, "proceed"), f"{intent.value} should proceed"

    def test_multi_intent_split(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import SafetyGate, Route
        g = SafetyGate()
        ci = ClassifiedIntent(Intent.MULTI_INTENT, 0.90, "rule")
        rd = g.check(ci)
        assert rd.route in (Route.SPLIT, Route.FALLBACK_LLM, "split", "fallback_llm")


class TestRoutes:
    def test_all_intents_have_routes(self):
        from router.types import Intent
        from router.routes import INTENT_ROUTES
        for i in Intent:
            assert i in INTENT_ROUTES, f"Intent {i.value} has no route"

    def test_code_search_routes_to_explore(self):
        from router.types import Intent
        from router.routes import get_route
        route = get_route(Intent.CODE_SEARCH)
        assert route.agent == "explore"

    def test_casual_chat_routes_to_llm(self):
        from router.types import Intent
        from router.routes import get_route
        route = get_route(Intent.CASUAL_CHAT)
        assert route.agent == "llm"

    def test_unknown_routes_to_llm(self):
        from router.types import Intent
        from router.routes import get_route
        route = get_route(Intent.UNKNOWN)
        assert route.agent == "llm"

    def test_memory_retrieval_routes_to_honcho(self):
        from router.types import Intent
        from router.routes import get_route
        route = get_route(Intent.MEMORY_RETRIEVAL)
        assert route.agent == "honcho"

    def test_route_has_method(self):
        from router.types import Intent
        from router.routes import get_route
        route = get_route(Intent.CODE_SEARCH)
        assert hasattr(route, "method")
        assert route.method is not None


class TestSerde:
    def test_serialize_proceed(self):
        from router.guard import serialize_route_decision, Route
        from router.types import RouteDecision
        rd = RouteDecision(route=Route.PROCEED, reason="OK")
        d = serialize_route_decision(rd)
        assert d["route"] == "proceed"
        assert d["reason"] == "OK"

    def test_deserialize_proceed(self):
        from router.guard import deserialize_route_decision, Route
        rd = deserialize_route_decision({"route": "proceed", "reason": "test"})
        assert rd.route == Route.PROCEED

    def test_roundtrip(self):
        from router.guard import serialize_route_decision, deserialize_route_decision, Route
        from router.types import RouteDecision
        original = RouteDecision(route=Route.BLOCK, reason="Dangerous")
        d = serialize_route_decision(original)
        restored = deserialize_route_decision(d)
        assert restored.route == Route.BLOCK
        assert restored.reason == "Dangerous"


class TestSplitText:
    def test_and_split(self):
        from router.guard import SafetyGate
        g = SafetyGate()
        parts = g._split_text("find the bug and deploy the fix")
        assert len(parts) >= 2

    def test_then_split(self):
        from router.guard import SafetyGate
        g = SafetyGate()
        parts = g._split_text("fix the login then push to NAS")
        assert len(parts) >= 2

    def test_semicolon_split(self):
        from router.guard import SafetyGate
        g = SafetyGate()
        parts = g._split_text("check config; restart service")
        assert len(parts) >= 2

    def test_no_split_single_intent(self):
        from router.guard import SafetyGate
        g = SafetyGate()
        parts = g._split_text("find auth middleware")
        assert len(parts) == 1
