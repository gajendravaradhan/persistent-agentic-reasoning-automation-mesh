"""Tests for guard.py (ConfidenceGuard + SafetyGate) and routes.py."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


class TestConfidenceGuard:
    def test_high_confidence_proceeds(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import ConfidenceGuard
        g = ConfidenceGuard()
        ci = ClassifiedIntent(Intent.CODE_SEARCH, 0.95, "rule")
        rd = g.check(ci)
        assert rd.route == "PROCEED"

    def test_low_confidence_falls_back(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import ConfidenceGuard
        g = ConfidenceGuard()
        ci = ClassifiedIntent(Intent.CODE_SEARCH, 0.60, "rule")
        rd = g.check(ci)
        assert rd.route == "FALLBACK_LLM"

    def test_exact_threshold_proceeds(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import ConfidenceGuard
        g = ConfidenceGuard()
        ci = ClassifiedIntent(Intent.CODE_SEARCH, 0.85, "rule")
        rd = g.check(ci)
        assert rd.route == "PROCEED"

    def test_just_below_threshold_falls_back(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import ConfidenceGuard
        g = ConfidenceGuard()
        ci = ClassifiedIntent(Intent.CODE_SEARCH, 0.849, "rule")
        rd = g.check(ci)
        assert rd.route == "FALLBACK_LLM"


class TestSafetyGate:
    def test_dangerous_intent_blocked(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import SafetyGate
        g = SafetyGate()
        for intent in [Intent.DEPLOYMENT, Intent.INFRASTRUCTURE, Intent.SECURITY]:
            ci = ClassifiedIntent(intent, 0.95, "rule")
            rd = g.check(ci)
            assert rd.route == "BLOCK", f"{intent.value} should be BLOCKED, got {rd.route}"

    def test_safe_intent_proceeds(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import SafetyGate
        g = SafetyGate()
        for intent in [Intent.CODE_SEARCH, Intent.CASUAL_CHAT, Intent.MEMORY_RETRIEVAL]:
            ci = ClassifiedIntent(intent, 0.95, "rule")
            rd = g.check(ci)
            assert rd.route == "PROCEED", f"{intent.value} should PROCEED, got {rd.route}"

    def test_multi_intent_split(self):
        from router.types import ClassifiedIntent, Intent
        from router.guard import SafetyGate
        g = SafetyGate()
        ci = ClassifiedIntent(Intent.MULTI_INTENT, 0.90, "rule")
        rd = g.check(ci)
        assert rd.route in ("SPLIT", "FALLBACK_LLM"), f"Expected SPLIT or FALLBACK_LLM, got {rd.route}"


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
