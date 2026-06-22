"""PARAM Intent Router — Hermes gateway plugin.

Registers a pre_gateway_dispatch hook that classifies every incoming
message via the Intent Router before it reaches the LLM.

Classification outcomes:
  - Safe intents (CODE_SEARCH, MEMORY, CASUAL, ANALYSIS, UNKNOWN):
    Returns {"action": "allow"} — normal LLM processing.
  - Gated intents (INFRASTRUCTURE, DEPLOYMENT, SECURITY):
    Returns {"action": "skip"} — message dropped, plugin sends an
    "approval required" reply to the user instead.
  - Low confidence (< 0.85):
    Returns {"action": "allow"} — falls back to LLM (by design).

The router module is loaded from /opt/data/router/router/ (staged on the
NAS volume). Audit entries are written to /opt/data/router/audit_log.jsonl
by the router's own AuditLogger.
"""

import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROUTER_BASE = Path("/opt/data/router")
ROUTER_PKG = ROUTER_BASE / "router"


def _load_router():
    if not ROUTER_PKG.exists():
        logger.warning("param-intent-router: router package not found at %s", ROUTER_PKG)
        return None
    if str(ROUTER_BASE) not in sys.path:
        sys.path.insert(0, str(ROUTER_BASE))
    try:
        from router import classify_and_route
        return classify_and_route
    except ImportError as e:
        logger.warning("param-intent-router: cannot import router: %s", e)
        return None


def _send_approval_required(gateway, event, classification: dict) -> None:
    intent = classification.get("intent", "unknown")
    confidence = classification.get("confidence", 0)
    route = classification.get("route", "unknown")
    reason = classification.get("reason", "")

    message_text = (
        f"⚠️ **Approval Required**\n\n"
        f"Intent: `{intent}` (confidence: {confidence:.0%})\n"
        f"Route: `{route}`\n"
        f"Reason: {reason}\n\n"
        f"This request was classified as requiring explicit approval "
        f"by the PARAM Intent Router. The governance gate in AGENTS.md "
        f"handles infrastructure, deployment, and security requests."
    )

    try:
        source = event.source
        platform = source.platform
        if hasattr(gateway, "platforms") and platform:
            platform_name = platform.value if hasattr(platform, "value") else str(platform)
            adapter = gateway.platforms.get(platform_name)
            if adapter and hasattr(adapter, "send_message"):
                import asyncio
                asyncio.ensure_future(
                    adapter.send_message(
                        chat_id=source.chat_id,
                        text=message_text,
                        reply_to_message_id=getattr(event, "message_id", None),
                    )
                )
                logger.info(
                    "param-intent-router: sent approval-required reply for intent=%s",
                    intent,
                )
                return
    except Exception as e:
        logger.warning("param-intent-router: failed to send approval reply: %s", e)

    logger.info(
        "param-intent-router: skipped %s (intent=%s confidence=%.2f) — no adapter reply sent",
        getattr(event, "message_id", "?"),
        intent,
        confidence,
    )


def _pre_gateway_dispatch(event=None, gateway=None, **kwargs) -> dict | None:
    message_text = getattr(event, "text", "") or ""
    if not message_text or len(message_text.strip()) < 3:
        return None

    classify_and_route = _load_router()
    if classify_and_route is None:
        return None

    try:
        result = classify_and_route(message_text)
    except Exception as e:
        logger.warning("param-intent-router: classification error: %s", e)
        return None

    intent = result.get("intent", "unknown")
    confidence = result.get("confidence", 0)
    route = result.get("route", "unknown")
    requires_approval = result.get("requires_approval", False)
    method = result.get("method", "?")

    logger.info(
        "param-intent-router: intent=%s confidence=%.2f route=%s method=%s approval=%s",
        intent, confidence, route, method, requires_approval,
    )

    if requires_approval:
        _send_approval_required(gateway, event, result)
        return {"action": "skip", "reason": f"param-router: {intent} requires approval"}

    return {"action": "allow"}


def register(ctx) -> None:
    ctx.register_hook("pre_gateway_dispatch", _pre_gateway_dispatch)
    logger.info("param-intent-router: registered pre_gateway_dispatch hook")
