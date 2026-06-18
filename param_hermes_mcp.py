#!/usr/bin/env -S /Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/python
"""param_hermes_mcp.py — MCP server exposing all Hermes agent tools as MCP tools."""

import json
import os
import sys
from typing import Any

if not os.environ.get("HERMES_HOME"):
    os.environ["HERMES_HOME"] = "/Users/gajendra/.hermes"

_hermes_agent_src = os.path.join(os.environ["HERMES_HOME"], "hermes-agent")
if _hermes_agent_src not in sys.path:
    sys.path.insert(0, _hermes_agent_src)

from tools.registry import registry, discover_builtin_tools  # noqa: E402

discover_builtin_tools()

from mcp.server import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402
import mcp.types as types  # noqa: E402

PREFIX = "hermes__"
server = Server("param-hermes-mcp")


def _to_mcp_schema(entry) -> dict:
    """Convert a Hermes tool schema to an MCP inputSchema dict.

    Hermes schema: {name, description, parameters: {type, properties, required}}
    MCP inputSchema = the ``parameters`` block (JSON Schema object).
    """
    params = entry.schema.get("parameters", {})
    if not isinstance(params, dict):
        params = {"type": "object", "properties": {}, "required": []}
    if "type" not in params:
        params["type"] = "object"
    if "properties" not in params:
        params["properties"] = {}
    return params


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    tools: list[types.Tool] = []
    for entry in registry._snapshot_entries():
        mcp_name = f"{PREFIX}{entry.name}"
        try:
            tools.append(
                types.Tool(
                    name=mcp_name,
                    description=entry.schema.get("description", entry.description or ""),
                    inputSchema=_to_mcp_schema(entry),
                )
            )
        except Exception:
            print(
                f"[param_hermes_mcp] WARNING: failed to create MCP tool for {entry.name}",
                file=sys.stderr,
            )
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if not name.startswith(PREFIX):
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool (no {PREFIX} prefix): {name}"}),
            )
        ]

    hermes_name = name[len(PREFIX):]

    try:
        result_json: str = registry.dispatch(hermes_name, arguments)
    except Exception as exc:
        print(
            f"[param_hermes_mcp] dispatch error for {hermes_name}: {exc}",
            file=sys.stderr,
        )
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Tool execution failed: {type(exc).__name__}: {exc}"}
                ),
            )
        ]

    return [types.TextContent(type="text", text=result_json)]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
