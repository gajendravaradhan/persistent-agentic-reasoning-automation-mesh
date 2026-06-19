#!/usr/bin/env -S /Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/python
"""param_hermes_mcp.py — MCP server exposing all Hermes agent tools as MCP tools.

Pure functions (_to_mcp_schema, _build_tool_entries, _build_call_response)
contain all logic and are testable without Pydantic. MCP imports are deferred
to _create_server() so the module can be imported cleanly in test environments.
"""

import json, os, sys
from typing import Any

if not os.environ.get("HERMES_HOME"):
    os.environ["HERMES_HOME"] = "/Users/gajendra/.hermes"

_hermes_agent_src = os.path.join(os.environ["HERMES_HOME"], "hermes-agent")
if _hermes_agent_src not in sys.path:
    sys.path.insert(0, _hermes_agent_src)

from tools.registry import registry, discover_builtin_tools  # noqa: E402
discover_builtin_tools()

PREFIX = "hermes__"


def _to_mcp_schema(entry) -> dict:
    params = entry.schema.get("parameters", {})
    if not isinstance(params, dict):
        params = {"type": "object", "properties": {}, "required": []}
    if "type" not in params:
        params["type"] = "object"
    if "properties" not in params:
        params["properties"] = {}
    return params


def _build_tool_entries(entries, prefix=PREFIX) -> list:
    tools = []
    for entry in entries:
        mcp_name = f"{prefix}{entry.name}"
        try:
            tools.append({
                "name": mcp_name,
                "description": entry.schema.get("description", entry.description or ""),
                "inputSchema": _to_mcp_schema(entry),
            })
        except Exception:
            print(f"[param_hermes_mcp] WARNING: failed to create MCP tool for {entry.name}", file=sys.stderr)
    return tools


def _build_call_response(name, arguments, dispatch_fn, prefix=PREFIX) -> dict:
    if not name.startswith(prefix):
        return {"text": json.dumps({"error": f"Unknown tool (no {prefix} prefix): {name}"}), "is_error": True}
    hermes_name = name[len(prefix):]
    try:
        result_json = dispatch_fn(hermes_name, arguments)
        return {"text": str(result_json), "is_error": False}
    except Exception as exc:
        print(f"[param_hermes_mcp] dispatch error for {hermes_name}: {exc}", file=sys.stderr)
        return {"text": json.dumps({"error": f"Tool execution failed: {type(exc).__name__}: {exc}"}), "is_error": True}


def _create_server():
    from mcp.server import Server
    import mcp.types as types
    srv = Server("param-hermes-mcp")

    @srv.list_tools()
    async def handle_list_tools():
        entries = registry._snapshot_entries()
        return [types.Tool(name=t["name"], description=t["description"], inputSchema=t["inputSchema"]) for t in _build_tool_entries(entries)]

    @srv.call_tool()
    async def handle_call_tool(name, arguments):
        r = _build_call_response(name, arguments, registry.dispatch)
        return [types.TextContent(type="text", text=r["text"])]

    return srv


async def main():
    from mcp.server.stdio import stdio_server
    srv = _create_server()
    async with stdio_server() as (read_stream, write_stream):
        await srv.run(read_stream, write_stream, srv.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
