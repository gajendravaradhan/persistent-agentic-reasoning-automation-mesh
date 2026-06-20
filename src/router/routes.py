"""Intent-to-agent routing table and lookup.

Every :class:`Intent` value must have exactly one entry in
:data:`INTENT_ROUTES`.  The :func:`get_route` function provides safe
lookup with a KeyError for undefined intents.
"""

from __future__ import annotations

from .types import AgentRoute, Intent


# ---------------------------------------------------------------------------
# Route table — every Intent value MUST be present.
# ---------------------------------------------------------------------------

INTENT_ROUTES: dict[Intent, AgentRoute] = {
    Intent.CODE_SEARCH: AgentRoute(agent="explore", method="task"),
    Intent.CODE_CHANGE: AgentRoute(agent="llm", method="delegate"),
    Intent.MEMORY_RETRIEVAL: AgentRoute(agent="honcho", method="recall"),
    Intent.MEMORY_WRITE: AgentRoute(agent="hermes", method="memory_write"),
    Intent.CASUAL_CHAT: AgentRoute(agent="llm", method="direct"),
    Intent.ANALYSIS: AgentRoute(agent="oracle", method="task"),
    Intent.SECURITY: AgentRoute(
        agent="llm", method="direct", requires_approval=True
    ),
    Intent.INFRASTRUCTURE: AgentRoute(
        agent="llm", method="direct", requires_approval=True
    ),
    Intent.DEPLOYMENT: AgentRoute(
        agent="llm", method="direct", requires_approval=True
    ),
    Intent.UNKNOWN: AgentRoute(agent="llm", method="direct"),
    Intent.MULTI_INTENT: AgentRoute(agent="router", method="split"),
}


def get_route(intent: Intent) -> AgentRoute:
    """Return the :class:`AgentRoute` for *intent*.

    Raises:
        KeyError: If *intent* is not present in :data:`INTENT_ROUTES`
            (all 11 values should be defined).
    """
    return INTENT_ROUTES[intent]
