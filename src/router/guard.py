"""Confidence guard and safety gate for intent routing.

ConfidenceGuard rejects low-confidence classifications (<85%) by routing
to FALLBACK_LLM. SafetyGate blocks dangerous intents (DEPLOY, INFRA, SEC)
requiring user approval, and splits MULTI_INTENT into sub-intents.
"""

from __future__ import annotations

import re
from typing import Any

from .types import ClassifiedIntent, Intent, Route, RouteDecision


CONFIDENCE_THRESHOLD = 0.85

DANGEROUS_INTENTS: set[Intent] = {
    Intent.DEPLOYMENT,
    Intent.INFRASTRUCTURE,
    Intent.SECURITY,
}


def serialize_route_decision(decision: RouteDecision) -> dict[str, Any]:
    """Serialize a RouteDecision to a JSON-compatible dictionary.

    Enums are converted to their ``.value`` strings. The ``intents`` list
    is serialised as ``[{"intent": str, "text": str | None}, ...]``.
    """
    intents_raw = decision.intents
    return {
        "route": decision.route.value,
        "reason": decision.reason,
        "intents": (
            [
                {"intent": intent.value, "text": text}
                for intent, text in (intents_raw or [])
            ]
            if intents_raw
            else None
        ),
    }


def deserialize_route_decision(data: dict[str, Any]) -> RouteDecision:
    """Restore a RouteDecision from a dictionary produced by
    :func:`serialize_route_decision`."""
    route = Route(data["route"])
    intents = None
    if data.get("intents"):
        intents = [
            (Intent(item["intent"]), item.get("text") or "")
            for item in data["intents"]
        ]
    return RouteDecision(
        route=route,
        reason=data.get("reason", ""),
        intents=intents,
    )


class ConfidenceGuard:
    """Rejects classifications whose confidence is below the threshold.

    When confidence < 85 % the request is safe-fallback routed to an LLM so
    the user never gets a wrong automated action.
    """

    def check(self, classified: ClassifiedIntent) -> RouteDecision:
        """Check confidence; return PROCEED or FALLBACK_LLM."""
        if classified.confidence < CONFIDENCE_THRESHOLD:
            return RouteDecision(
                route=Route.FALLBACK_LLM,
                reason=(
                    f"Confidence {classified.confidence:.2f}"
                    f" < {CONFIDENCE_THRESHOLD}"
                ),
            )
        return RouteDecision(
            route=Route.PROCEED,
            reason="Confidence meets threshold",
        )


class SafetyGate:
    """Blocks dangerous intents and splits multi-intent requests.

    * Intent in *DANGEROUS_INTENTS* → :attr:`Route.BLOCK`
    * Intent is *MULTI_INTENT*       → :attr:`Route.SPLIT`
    * Everything else                → :attr:`Route.PROCEED`
    """

    def check(self, classified: ClassifiedIntent) -> RouteDecision:
        """Inspect the classified intent and return a guard decision."""
        if classified.intent in DANGEROUS_INTENTS:
            return RouteDecision(
                route=Route.BLOCK,
                reason=(
                    f"Intent {classified.intent.value}"
                    " requires user approval"
                ),
            )

        if classified.intent == Intent.MULTI_INTENT:
            return self._handle_multi_intent(classified)

        return RouteDecision(
            route=Route.PROCEED,
            reason="Safe single intent",
        )

    # ------------------------------------------------------------------
    # Multi-intent handling
    # ------------------------------------------------------------------

    def _handle_multi_intent(
        self, classified: ClassifiedIntent
    ) -> RouteDecision:
        """Split a multi-intent into sub-intents and return SPLIT."""
        sub_intents = self._split_intents(classified)
        return RouteDecision(
            route=Route.SPLIT,
            reason="Multi-intent detected, splitting",
            intents=sub_intents,
        )

    def _split_intents(
        self, classified: ClassifiedIntent
    ) -> list[tuple[Intent, str]]:
        """Attempt to split the request text into sub-intents.

        Tries to read a ``text`` attribute from *classified* (duck-typing)
        so that if the upstream caller attached the original request it can
        be split on conjunctions.  Falls back to returning the whole intent
        as a single sub-intent.
        """
        text: str | None = getattr(classified, "text", None)
        if not text:
            return [(Intent.UNKNOWN, "")]

        parts = self._split_text(text)
        if len(parts) <= 1:
            return [(Intent.UNKNOWN, text)]

        return [(Intent.UNKNOWN, part.strip()) for part in parts if part.strip()]

    @staticmethod
    def _split_text(text: str) -> list[str]:
        """Split *text* on common conjunction boundaries."""
        # Try the most specific pattern first; fall back to splitting on
        # each conjunction individually.
        combined = re.compile(
            r"\s+(and|then)\s+",
            re.IGNORECASE,
        )
        parts = combined.split(text, maxsplit=1)

        if len(parts) >= 3:
            # Split succeeded — parts is [left, conjunction, right].
            # Recursively split the right side.
            head = parts[0]
            tail = SafetyGate._split_text(parts[2])
            return [head, *tail]

        # Try semicolons.
        if ";" in text:
            return [p.strip() for p in text.split(";") if p.strip()]

        # No split possible.
        return [text]
