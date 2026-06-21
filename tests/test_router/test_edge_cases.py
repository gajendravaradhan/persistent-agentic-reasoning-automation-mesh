"""Edge case tests for the Intent Router (IR-1.2)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


class TestEdgeCaseEmptyRequest:
    """IR-1.2.1: Empty request -> UNKNOWN, routed to LLM."""

    def test_empty_request_routes_to_fallback_llm(self):
        from router import classify_and_route
        result = classify_and_route("")
        assert result["intent"] == "unknown"
        assert result["confidence"] == 0.0
        assert result["route"] == "fallback_llm"

    def test_whitespace_request_routes_to_fallback_llm(self):
        from router import classify_and_route
        result = classify_and_route("   \n  \t  ")
        assert result["intent"] == "unknown"
        assert result["route"] == "fallback_llm"

    def test_single_space_request(self):
        from router.classifier import classify
        result = classify(" ")
        assert result.intent.value == "unknown"
        assert result.confidence == 0.0


class TestEdgeCaseLongRequest:
    """IR-1.2.2: Very long request (>2000 chars) truncated, classified on first 500."""

    def test_very_long_request_classified_by_first_500(self):
        from router.classifier import classify
        prefix = "deploy the new docker compose to production staging environment "
        filler = "and also check some random stuff and " * 100
        request = prefix + filler
        assert len(request) > 2000, f"Request too short: {len(request)} chars"
        result = classify(request)
        assert result.intent.value in ("deploy", "infra"), f"Expected deploy/infra, got {result.intent.value}"
        assert result.confidence > 0.0

    def test_very_long_request_no_crash(self):
        from router.classifier import classify
        request = "hello " * 2000
        assert len(request) > 2000
        result = classify(request)
        assert result is not None
        assert result.intent.value is not None

    def test_long_request_reasonable_latency(self):
        from router.classifier import classify
        request = "find the authentication middleware and check its configuration " * 100
        start = time.time()
        classify(request)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < 500, f"Long request took {elapsed_ms:.1f}ms"


class TestEdgeCaseMixedLanguage:
    """IR-1.2.3: Mixed-language requests handled gracefully."""

    def test_mixed_language_hindi_english(self):
        from router import classify_and_route
        result = classify_and_route("deploy the new configuration to production now \u0915\u0930\u0928\u093e \u0939\u0948")
        assert result is not None
        assert "intent" in result
        assert result["confidence"] > 0.0

    def test_mixed_language_chinese_english(self):
        from router.classifier import classify
        result = classify("find the code file please \u8c22\u8c22")
        assert result.intent.value == "code_search"

    def test_mixed_language_non_latin_does_not_crash(self):
        from router.classifier import classify
        result = classify("\uc548\ub155\ud558\uc138\uc694 how are you")
        assert result is not None
        assert result.intent.value == "casual"

    def test_mixed_language_rtl_does_not_break_regex(self):
        from router.classifier import classify
        result = classify("deploy to production \u05dc\u05d1\u05d3\u05d5\u05e7")
        assert result is not None
        assert result.intent.value in ("deploy", "infra")


class TestEdgeCaseRapidRepeated:
    """IR-1.2.4: Rapid repeated classification dedup via SHA256."""

    def test_five_same_requests_one_audit_entry(self):
        from router import _compute_hash
        from router.audit import AuditLogger
        from router.types import AuditEntry, Intent
        import tempfile
        import os
        from datetime import datetime, timedelta

        request = "find the auth middleware"
        h = _compute_hash(request)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            tmp = f.name
        try:
            logger = AuditLogger(tmp)
            ts = datetime.now()
            for i in range(5):
                entry = AuditEntry(
                    ts + timedelta(seconds=i), h, request,
                    Intent.CODE_SEARCH.value, 0.92, "rule",
                    "explore", [], "routed", 2,
                )
                logger.log(entry)
            stats = logger.get_stats()
            assert stats["total_entries"] == 1
        finally:
            os.unlink(tmp)


class TestEdgeCaseRegexBacktracking:
    """IR-1.2.5: No regex catastrophic backtracking."""

    def test_worst_case_input_classifies_under_100ms(self):
        from router.classifier import classify
        worst_case = "a" * 1000
        start = time.time()
        result = classify(worst_case)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < 100, f"Classification took {elapsed_ms:.1f}ms, expected < 100ms"
        assert result is not None

    def test_nested_repetition_input(self):
        from router.classifier import classify
        worst_case = "a" * 500 + " b " + "a" * 500
        start = time.time()
        result = classify(worst_case)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < 100, f"Nested repetition took {elapsed_ms:.1f}ms"
        assert result is not None

    def test_many_boundary_characters(self):
        from router.classifier import classify
        worst_case = " ".join(["a" * 10 for _ in range(200)])
        start = time.time()
        result = classify(worst_case)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < 100, f"Boundary chars took {elapsed_ms:.1f}ms"
        assert result is not None
