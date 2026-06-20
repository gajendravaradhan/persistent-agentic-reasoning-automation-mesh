"""Intent routing orchestrator — main entry point for the PARAM intent router.

Implements the full classify → guard → safety → route → audit pipeline.
"""
import hashlib
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .audit import AuditLogger
from .classifier import IntentClassifier
from .guard import ConfidenceGuard, SafetyGate
from .routes import get_route
from .types import AuditEntry, ClassifiedIntent, Route, RouteDecision


def _compute_hash(request: str) -> str:
    normalized = request.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def _build_response(
    classified: ClassifiedIntent,
    route_name: str,
    reason: str,
    requires_approval: bool = False,
    sub_routes: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    response: Dict[str, Any] = {
        "intent": classified.intent.value,
        "confidence": classified.confidence,
        "route": route_name,
        "method": classified.method,
        "reason": reason,
        "requires_approval": requires_approval,
    }
    if sub_routes:
        response["sub_routes"] = sub_routes
    return response


def _log_and_return(
    auditor: AuditLogger,
    request: str,
    classified: ClassifiedIntent,
    route: str,
    guard_decisions: List[Dict[str, Any]],
    outcome: str,
    latency_ms: int,
    response_dict: Dict[str, Any],
) -> Dict[str, Any]:
    entry = AuditEntry(
        timestamp=datetime.now(),
        request_hash=_compute_hash(request),
        original_request=request[:200],
        intent=classified.intent.value,
        confidence=classified.confidence,
        classification_method=classified.method,
        route=route,
        guard_decisions=guard_decisions,
        outcome=outcome,
        latency_ms=latency_ms,
    )
    auditor.log(entry)
    return response_dict


def classify_and_route(
    request: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Full intent routing pipeline: classify → guard → safety → route → audit.

    Args:
        request: The user's raw input string.
        context: Optional context dict (previous intent, session state, etc.)

    Returns:
        Dict with keys: intent, confidence, route, method, reason,
        requires_approval, and optionally sub_routes for multi-intent.
    """
    ctx: Dict[str, Any] = context or {}
    guard_decisions: List[Dict[str, Any]] = []
    start_time: float = time.time()

    classifier = IntentClassifier()
    conf_guard = ConfidenceGuard()
    safety_gate = SafetyGate()
    auditor = AuditLogger()

    classified: ClassifiedIntent = classifier.classify(request, ctx)

    conf_decision: RouteDecision = conf_guard.check(classified)
    guard_decisions.append({"route": conf_decision.route.value, "reason": conf_decision.reason})

    if conf_decision.route == Route.FALLBACK_LLM:
        elapsed = int((time.time() - start_time) * 1000)
        return _log_and_return(
            auditor=auditor,
            request=request,
            classified=classified,
            route="fallback_llm",
            guard_decisions=guard_decisions,
            outcome="fallback",
            latency_ms=elapsed,
            response_dict=_build_response(
                classified=classified,
                route_name="fallback_llm",
                reason=conf_decision.reason,
                requires_approval=False,
            ),
        )

    safety_decision: RouteDecision = safety_gate.check(classified)
    guard_decisions.append({"route": safety_decision.route.value, "reason": safety_decision.reason})

    if safety_decision.route == Route.BLOCK:
        elapsed = int((time.time() - start_time) * 1000)
        return _log_and_return(
            auditor=auditor,
            request=request,
            classified=classified,
            route="blocked",
            guard_decisions=guard_decisions,
            outcome="blocked",
            latency_ms=elapsed,
            response_dict=_build_response(
                classified=classified,
                route_name="blocked",
                reason=safety_decision.reason,
                requires_approval=True,
            ),
        )

    if safety_decision.route == Route.SPLIT:
        sub_results: List[Dict[str, Any]] = []
        for sub_intent, sub_request_text in (safety_decision.intents or []):
            sub_results.append(classify_and_route(sub_request_text, ctx))
        elapsed = int((time.time() - start_time) * 1000)
        return _log_and_return(
            auditor=auditor,
            request=request,
            classified=classified,
            route="split",
            guard_decisions=guard_decisions,
            outcome="split",
            latency_ms=elapsed,
            response_dict=_build_response(
                classified=classified,
                route_name="split",
                reason="Multi-intent split into independent sub-routes",
                requires_approval=False,
                sub_routes=sub_results,
            ),
        )

    agent_route = get_route(classified.intent)

    elapsed = int((time.time() - start_time) * 1000)
    return _log_and_return(
        auditor=auditor,
        request=request,
        classified=classified,
        route=agent_route.agent,
        guard_decisions=guard_decisions,
        outcome="routed",
        latency_ms=elapsed,
        response_dict=_build_response(
            classified=classified,
            route_name=agent_route.agent,
            reason=f"Routed to {agent_route.agent} via {agent_route.method}",
            requires_approval=getattr(agent_route, "requires_approval", False),
        ),
    )
