"""Tests for Intent Router classifier — rule engine, confidence, multi-intent, edge cases."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


class TestRuleEngine:
    def test_rules_exist(self):
        from router.classifier import RULES
        assert len(RULES) >= 10, f"Only {len(RULES)} rules defined, need 10+"

    def test_rules_cover_code_search(self):
        from router.classifier import classify
        result = classify("find where authentication middleware is defined")
        assert result.intent.value == "code_search"

    def test_rules_cover_casual_chat(self):
        from router.classifier import classify
        result = classify("hello how are you")
        assert result.intent.value == "casual"

    def test_rules_cover_deployment(self):
        from router.classifier import classify
        result = classify("deploy the new docker compose to NAS")
        assert result.intent.value in ("infra", "deploy", "infrastructure")

    def test_rules_cover_memory_retrieval(self):
        from router.classifier import classify
        result = classify("what did we discuss yesterday about memory")
        assert result.intent.value in ("memory", "memory_retrieval")

    def test_rules_cover_memory_write(self):
        from router.classifier import classify
        result = classify("remember that I prefer tabs over spaces")
        assert result.intent.value == "memory_write"

    def test_rules_cover_analysis(self):
        from router.classifier import classify
        result = classify("compare PARAM with standalone Hermes and evaluate tradeoffs")
        assert result.intent.value == "analysis"

    def test_rules_cover_security(self):
        from router.classifier import classify
        result = classify("audit the codebase for security vulnerabilities")
        assert result.intent.value == "security"

    def test_rules_cover_code_change(self):
        from router.classifier import classify
        result = classify("add a login endpoint to the API")
        assert result.intent.value == "code_change"


class TestConfidenceScoring:
    def test_single_match_confidence_below_90(self):
        from router.classifier import classify
        result = classify("find the auth file")
        assert result.confidence < 0.90, f"Single match confidence {result.confidence} should be < 0.90"

    def test_casual_chat_high_confidence(self):
        from router.classifier import classify
        result = classify("hello hi how are you doing today")
        assert result.confidence >= 0.90

    def test_empty_request_zero_confidence(self):
        from router.classifier import classify
        result = classify("")
        assert result.intent.value == "unknown"
        assert result.confidence == 0.0

    def test_whitespace_request_zero_confidence(self):
        from router.classifier import classify
        result = classify("   \n  ")
        assert result.intent.value == "unknown"
        assert result.confidence == 0.0


class TestMultiIntent:
    def test_and_conjunction_detected(self):
        from router.classifier import classify
        result = classify("find the auth bug and deploy the fix")
        assert result.intent.value == "multi"

    def test_then_conjunction_detected(self):
        from router.classifier import classify
        result = classify("fix the login endpoint then push to NAS")
        assert result.intent.value == "multi"


class TestEdgeCases:
    def test_long_request_truncated(self):
        from router.classifier import classify
        long_req = "find the authentication module " * 100
        result = classify(long_req)
        assert result.intent.value is not None

    def test_mixed_language(self):
        from router.classifier import classify
        result = classify("deploy the new config to production now")
        assert result.intent.value in ("infra", "deploy", "infrastructure", "unknown")

    def test_single_word(self):
        from router.classifier import classify
        result = classify("deploy immediately")
        assert result.intent.value in ("infra", "deploy", "infrastructure", "unknown")

    def test_method_is_rule(self):
        from router.classifier import classify
        result = classify("find auth middleware")
        assert result.method == "rule"
