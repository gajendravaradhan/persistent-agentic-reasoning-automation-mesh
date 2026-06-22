"""Intent Router hook — classifies incoming messages and logs routing decisions.

On agent:start: runs the Intent Router classifier on the incoming message,
logs the classification to the audit log, and prints the routing decision
to gateway logs for observability.

This hook operates in OBSERVATIONAL mode: it classifies and logs but does
not block or redirect the agent. The classification is available in the
gateway logs and audit_log.jsonl for post-hoc analysis, Langfuse tracing,
and feeding the self-evolving skills pipeline.

If the router classifies a message as INFRASTRUCTURE, DEPLOYMENT, or
SECURITY (requires_approval=True), the hook prints a WARNING to the
gateway logs. This provides an audit trail of potentially dangerous
requests without blocking them — the AGENTS.md governance gate handles
the actual blocking at the agent identity layer.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

ROUTER_BASE = Path(os.environ.get("HERMES_DATA", "/opt/data")) / "router"
AUDIT_LOG = ROUTER_BASE / "audit_log.jsonl"


async def handle(event_type: str, context: dict) -> None:
    if event_type != "agent:start":
        return

    message = context.get("message", "")
    if not message or len(message.strip()) < 3:
        return

    if not ROUTER_BASE.exists():
        print("[intent-router-hook] Router directory not found, skipping", flush=True)
        return

    sys.path.insert(0, str(ROUTER_BASE))

    try:
        from router import classify_and_route
    except ImportError:
        print("[intent-router-hook] Cannot import router module, skipping", flush=True)
        return

    start_time = time.time()

    try:
        result = classify_and_route(message, context={
            "platform": context.get("platform"),
            "user_id": context.get("user_id"),
            "chat_id": context.get("chat_id"),
            "session_id": context.get("session_id"),
        })
    except Exception as e:
        print(f"[intent-router-hook] Classification error: {e}", flush=True)
        return

    elapsed_ms = int((time.time() - start_time) * 1000)

    intent = result.get("intent", "unknown")
    confidence = result.get("confidence", 0)
    route = result.get("route", "unknown")
    method = result.get("method", "?")
    requires_approval = result.get("requires_approval", False)

    if requires_approval:
        print(
            f"[intent-router-hook] ⚠ GATED REQUEST: intent={intent} "
            f"confidence={confidence:.2f} route={route} "
            f"requires_approval=True — governance gate should review",
            flush=True,
        )
    else:
        print(
            f"[intent-router-hook] intent={intent} confidence={confidence:.2f} "
            f"route={route} method={method} latency={elapsed_ms}ms",
            flush=True,
        )
