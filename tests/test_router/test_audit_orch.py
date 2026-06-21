"""Tests for audit.py and orchestrator (__init__.py)."""
import pytest
import sys
import os
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


class TestAuditLogger:
    def test_log_writes_jsonl(self):
        from router.types import AuditEntry, Intent
        from router.audit import AuditLogger
        ts = datetime.now()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            tmp = f.name
        try:
            logger = AuditLogger(tmp)
            entry = AuditEntry(
                ts, "hash1", "test request", Intent.CODE_SEARCH.value,
                0.92, "rule", "explore", ["PROCEED"], "routed", 5,
            )
            logger.log(entry)
            assert os.path.getsize(tmp) > 0
        finally:
            os.unlink(tmp)

    def test_get_stats(self):
        from router.types import AuditEntry, Intent
        from router.audit import AuditLogger
        from datetime import timedelta
        ts = datetime.now()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            tmp = f.name
        try:
            logger = AuditLogger(tmp)
            for i in range(10):
                entry = AuditEntry(
                    ts + timedelta(seconds=i), f"hash{i}", f"req {i}",
                    Intent.CODE_SEARCH.value, 0.90 + i * 0.01, "rule",
                    "explore", ["PROCEED"], "routed", 3,
                )
                logger.log(entry)
            stats = logger.get_stats()
            assert stats["total_entries"] == 10
            assert "intent_distribution" in stats
            assert stats["confidence_avg"] > 0.90
        finally:
            os.unlink(tmp)

    def test_deduplication(self):
        from router.types import AuditEntry, Intent
        from router.audit import AuditLogger
        ts = datetime.now()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            tmp = f.name
        try:
            logger = AuditLogger(tmp)
            e1 = AuditEntry(ts, "same_hash", "req A", Intent.CODE_SEARCH.value, 0.9, "rule", "explore", [], "routed", 2)
            e2 = AuditEntry(ts, "same_hash", "req B", Intent.CODE_SEARCH.value, 0.9, "rule", "explore", [], "routed", 2)
            logger.log(e1)
            logger.log(e2)
            stats = logger.get_stats()
            assert stats["total_entries"] == 1, "Should de-duplicate same hash"
        finally:
            os.unlink(tmp)

    def test_sha256_same_request_dedup(self):
        """IR-0.5.3: SHA256 dedup — same request text → same hash → single audit entry."""
        from router import _compute_hash
        from router.types import AuditEntry, Intent
        from router.audit import AuditLogger
        ts = datetime.now()
        request = "find the auth middleware implementation"
        h = _compute_hash(request)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            tmp = f.name
        try:
            logger = AuditLogger(tmp)
            e1 = AuditEntry(ts, h, request, Intent.CODE_SEARCH.value, 0.92, "rule", "explore", [], "routed", 5)
            e2 = AuditEntry(ts, h, request + " (duplicate call)", Intent.CODE_SEARCH.value, 0.92, "rule", "explore", [], "routed", 5)
            logger.log(e1)
            logger.log(e2)
            stats = logger.get_stats()
            assert stats["total_entries"] == 1, "Same SHA256 hash must deduplicate"
        finally:
            os.unlink(tmp)

    def test_sha256_different_requests_separate_entries(self):
        """IR-0.5.3: Different requests produce different SHA256 hashes → separate entries."""
        from router import _compute_hash
        from router.types import AuditEntry, Intent
        from router.audit import AuditLogger
        ts = datetime.now()
        h1 = _compute_hash("find the auth middleware")
        h2 = _compute_hash("deploy the new config")
        assert h1 != h2, "Different requests must produce different SHA256 hashes"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            tmp = f.name
        try:
            logger = AuditLogger(tmp)
            e1 = AuditEntry(ts, h1, "req1", Intent.CODE_SEARCH.value, 0.92, "rule", "explore", [], "routed", 5)
            e2 = AuditEntry(ts, h2, "req2", Intent.DEPLOYMENT.value, 0.90, "rule", "llm", [], "blocked", 3)
            logger.log(e1)
            logger.log(e2)
            stats = logger.get_stats()
            assert stats["total_entries"] == 2, "Different SHA256 hashes must both be logged"
        finally:
            os.unlink(tmp)

    def test_sha256_normalization_for_dedup(self):
        """IR-0.5.3: SHA256 normalizes case/whitespace — 'Req A' == 'req a'."""
        from router import _compute_hash
        h1 = _compute_hash("Find the Auth Middleware")
        h2 = _compute_hash("find the auth middleware")
        assert h1 == h2, "Normalized requests must produce identical SHA256 hashes"

    def test_sha256_rapid_five_same_requests_one_entry(self):
        """IR-0.5.3+IR-1.2.4: Same request 5x → 1 audit entry via SHA256 dedup."""
        from router import _compute_hash
        from router.types import AuditEntry, Intent
        from router.audit import AuditLogger
        from datetime import timedelta
        ts = datetime.now()
        request = "find the auth middleware"
        h = _compute_hash(request)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            tmp = f.name
        try:
            logger = AuditLogger(tmp)
            for i in range(5):
                entry = AuditEntry(
                    ts + timedelta(seconds=i), h, request,
                    Intent.CODE_SEARCH.value, 0.92, "rule", "explore",
                    [], "routed", 2,
                )
                logger.log(entry)
            stats = logger.get_stats()
            assert stats["total_entries"] == 1, "5 rapid same-request calls → 1 entry"
        finally:
            os.unlink(tmp)


class TestOrchestrator:
    def test_classify_and_route_code_search(self):
        from router import classify_and_route
        result = classify_and_route("find where auth middleware is defined")
        assert "intent" in result
        assert "confidence" in result
        assert "route" in result
        assert "method" in result
        assert "reason" in result
        assert "requires_approval" in result

    def test_classify_and_route_deployment_blocked(self):
        from router import classify_and_route
        result = classify_and_route("deploy the new docker compose to production")
        assert result["requires_approval"] is True or result["route"] == "blocked"

    def test_classify_and_route_casual(self):
        from router import classify_and_route
        result = classify_and_route("hello how are you")
        assert result["requires_approval"] is False
        assert result["route"] == "llm"

    def test_classify_and_route_empty(self):
        from router import classify_and_route
        result = classify_and_route("")
        assert result["intent"] == "unknown"
        assert result["confidence"] == 0.0

    def test_classify_and_route_context(self):
        from router import classify_and_route
        result = classify_and_route("what was that?", context={"last_intent": "CODE_SEARCH"})
        assert result["confidence"] >= 0.0
