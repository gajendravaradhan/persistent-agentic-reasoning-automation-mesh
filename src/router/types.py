"""Intent Router — shared type definitions.

Intent enum, Route enum, and dataclasses for classification,
routing decisions, and audit logging.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class Intent(Enum):
    """All supported intent types for the PARAM Intent Router."""

    CODE_SEARCH = "code_search"
    CODE_CHANGE = "code_change"
    MEMORY_RETRIEVAL = "memory"
    MEMORY_WRITE = "memory_write"
    INFRASTRUCTURE = "infra"
    DEPLOYMENT = "deploy"
    SECURITY = "security"
    CASUAL_CHAT = "casual"
    ANALYSIS = "analysis"
    MULTI_INTENT = "multi"
    UNKNOWN = "unknown"


class Route(Enum):
    """Routing decisions produced by guards and the router."""

    PROCEED = "proceed"
    FALLBACK_LLM = "fallback_llm"
    BLOCK = "block"
    SPLIT = "split"


@dataclass
class AgentRoute:
    """Maps an intent to a target agent and invocation method."""

    agent: str
    method: str
    requires_approval: bool = False


@dataclass
class ClassifiedIntent:
    """Result of classifying a user request."""

    intent: Intent
    confidence: float
    method: str = "rule"  # "rule" | "llm"


@dataclass
class RouteDecision:
    """Decision produced by a guard or the router itself."""

    route: Route
    reason: str
    intents: Optional[list[tuple[Intent, str]]] = None


@dataclass
class AuditEntry:
    """Single audit-log entry recording every routing decision."""

    timestamp: datetime
    request_hash: str
    original_request: str
    intent: str
    confidence: float
    classification_method: str
    route: str
    guard_decisions: list[dict[str, Any]]
    outcome: str
    latency_ms: int
