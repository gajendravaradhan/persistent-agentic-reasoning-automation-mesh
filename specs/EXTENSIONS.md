# PARAM Extensions Guide

How to add new integrations to the Persistent Agentic Reasoning Automation Mesh.

---

## 1. Architecture Philosophy

PARAM is not a fixed product. It is a mesh that grows. Every new integration adds a limb. The mesh routes intent to the best subsystem without the user needing to know which one handled it.

Extensibility is built on three layers:

| Layer | Role | Example |
|-------|------|---------|
| **OMO** (OhMyOpenCode) | Agent runtime, tool discovery, task delegation | Multi-agent orchestration, code execution |
| **Hermes** | Persistent-world interface, personal automation | Telegram, cron, notifications, state |
| **MCP plugins** | Any future integration | Slack, email, Jira, HomeKit |

New integrations arrive as MCP servers. OMO discovers their tools automatically. PARAM absorbs them without identity drift.

---

## 2. How MCP Integration Works

### The Discovery Chain

```
New MCP Server
    │
    ▼
~/.mcp.json  ──►  OMO discovers server
    │
    ▼
mcp__<server>__<tool>  ──►  Tools appear in OMO's tool catalog
    │
    ▼
PARAM routes intent  ──►  User never thinks about "which PARAM"
```

### Naming Convention

All MCP tools follow a strict prefix pattern:

```
mcp__<server_name>__<tool_name>
```

- `server_name` is the key you use in `~/.mcp.json` → `mcpServers` block
- `tool_name` is whatever the MCP server advertises via `list_tools()`
- Tools are auto-discovered. No manual registration needed.

Examples from the running mesh:

| Tool | Source |
|------|--------|
| `hermes__messages_read` | Hermes Telegram bridge |
| `hermes__cron_status` | Hermes cron scheduler |
| `hermes__state_set` | Hermes persistent state |
| `mcp__huly__create_issue` | Huly project tracker |

### The Rule

If your MCP server is named `"foo"` in `~/.mcp.json` and exposes a tool called `do_thing`, PARAM sees it as `mcp__foo__do_thing`. Zero configuration beyond that.

---

## 3. Adding a New Integration: Step by Step

### Step 1: Create the MCP Server

Write a Python script (or any language that can speak MCP over stdio) that:

1. Imports or implements the tools you want to expose
2. Wraps them with an MCP `Server` instance
3. Runs over stdio transport

Use `param_hermes_mcp.py` as your template. It already demonstrates every pattern you need:

- Tool discovery from an existing registry
- Schema conversion to MCP `inputSchema` format
- Prefix application for namespace isolation
- Error handling and dispatch

### Step 2: Register in ~/.mcp.json

Add a new entry under `mcpServers`:

```json
{
  "mcpServers": {
    "hermes": {
      "type": "stdio",
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/param_slack_mcp.py"],
      "env": {
        "SLACK_TOKEN": "${SLACK_TOKEN}"
      }
    }
  }
}
```

Fields:

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Always `"stdio"` for local MCP servers |
| `command` | Yes | Path to the interpreter/runtime |
| `args` | Yes | Array; first arg is the MCP server script |
| `env` | No | Environment variables passed to the server process |

### Step 3: Restart OMO

OMO reads `~/.mcp.json` at startup. Restart your OMO session (or open a new one) to pick up the new server.

### Step 4: Verify Discovery

In your OMO session, ask PARAM to list available tools. The new `mcp__<server>__<tool>` entries should appear. If they don't, see [Troubleshooting](TROUBLESHOOTING.md).

### Step 5: Update SOUL.md (Optional)

If the integration is significant (not just a utility), add a section to `SOUL.md` under "Extension Architecture" so future PARAM sessions know about it. Example:

```markdown
### Slack Integration

Slack tools use `mcp__slack__*` prefix. Capabilities:
- `send_message` — post to channels
- `read_channel` — fetch recent messages
- `list_users` — workspace directory

PARAM uses Slack for team communication and alert delivery.
```

### Step 6: Update AGENTS.md (Optional)

Add a tool awareness table row in `~/.config/opencode/AGENTS.md` under "Tool Awareness":

```markdown
### Slack Layer
All Slack tools use `mcp__slack__*` prefix. Core capabilities:

| Domain | Tools |
|--------|-------|
| Messaging | `send_message`, `read_channel` |
| Users | `list_users`, `get_user` |
```

---

## 4. Integration Checklist

For every new integration, verify:

- [ ] MCP server script exists and is executable
- [ ] Entry added to `~/.mcp.json` under `mcpServers`
- [ ] `command` path is absolute (no `~`, no relative paths)
- [ ] Python dependencies installed in the correct venv (`mcp` package at minimum)
- [ ] Server starts without errors (run it directly to test: `python param_foo_mcp.py`)
- [ ] Tools appear in OMO tool list after restart
- [ ] Naming follows `mcp__<server>__<tool>` convention
- [ ] Error handling in the MCP server returns structured JSON, not tracebacks
- [ ] Environment variables are set (tokens, endpoints, etc.)
- [ ] SOUL.md updated if the integration is user-facing
- [ ] AGENTS.md updated with tool awareness section

---

## 5. Reference: Hermes Integration as Template

The Hermes integration (`param_hermes_mcp.py`) is the reference implementation. Here is what it does and why:

### Structure

```
param_hermes_mcp.py
├── Imports hermes-agent tool registry
├── Discovers builtin tools (discover_builtin_tools())
├── Creates MCP Server("param-hermes-mcp")
├── Prefixes every tool: "hermes__" + original_name
├── Converts Hermes schemas → MCP inputSchema (JSON Schema)
├── list_tools()  → returns all Hermes tools as MCP Tools
├── call_tool()   → strips prefix, dispatches to Hermes registry
└── main()        → runs over stdio transport
```

### Key Patterns

**Tool Discovery** — The Hermes agent has its own tool registry. `param_hermes_mcp.py` imports that registry, discovers all builtin tools, and re-exports them as MCP tools. If your integration has an existing API or library, follow the same pattern: import, wrap, export.

**Prefix Isolation** — Every tool gets the `hermes__` prefix. This prevents name collisions between integrations. Your server should use its own prefix (`slack__`, `jira__`, `email__`).

**Schema Translation** — Hermes tools have their own schema format. The adapter converts them to MCP's `inputSchema` (JSON Schema). If your integration's tools have different schema formats, you'll need a similar translation layer.

**Error Boundaries** — All dispatch calls are wrapped in try/except. Errors return structured JSON with `{"error": "message"}`, not Python tracebacks. OMO handles error tool returns gracefully.

---

## 6. Writing an MCP Server from Scratch

If you don't have an existing tool registry to wrap, here is the minimal MCP server skeleton:

```python
#!/usr/bin/env python3
"""param_foo_mcp.py — MCP server for Foo integration."""

import json
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

PREFIX = "foo__"
server = Server("param-foo-mcp")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name=f"{PREFIX}do_thing",
            description="Do something useful with Foo",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "What to act on"
                    }
                },
                "required": ["target"]
            }
        ),
        types.Tool(
            name=f"{PREFIX}get_status",
            description="Get Foo system status",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if not name.startswith(PREFIX):
        return [types.TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    tool_name = name[len(PREFIX):]

    try:
        # Your integration logic here
        if tool_name == "do_thing":
            result = {"ok": True, "acted_on": arguments.get("target")}
        elif tool_name == "get_status":
            result = {"status": "healthy"}
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        return [types.TextContent(type="text", text=json.dumps(result))]
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps({"error": str(exc)}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Requirements

Your MCP server needs the `mcp` Python package:

```bash
pip install mcp
```

For production integrations, also consider:
- `httpx` for HTTP calls to external APIs
- `pyyaml` if your integration has YAML configuration
- The SDK/library for the service you're integrating (e.g., `slack-sdk`, `atlassian-python-api`)

---

## 7. Future Integration Ideas

These are pre-mapped integration targets. Each follows the same MCP server pattern.

### Communication

| Integration | Tools | Value |
|-------------|-------|-------|
| **Slack** | `send_message`, `read_channel`, `list_users`, `react` | Team communication, alert delivery, standup automation |
| **Email** (Gmail/IMAP) | `send_email`, `read_inbox`, `search_messages`, `manage_labels` | Async communication, newsletter triage, ticket creation |
| **Discord** | `send_message`, `read_channel`, `manage_webhooks` | Community management, bot interactions |
| **Telegram** | `send_message`, `read_chat`, `send_photo` | Personal bot, notification delivery |

### Productivity

| Integration | Tools | Value |
|-------------|-------|-------|
| **Jira** | `create_issue`, `search_issues`, `transition_issue`, `get_sprint` | Project tracking, agile workflows |
| **Linear** | `create_issue`, `search_issues`, `get_cycle`, `assign_team` | Modern issue tracking, velocity tracking |
| **Notion** | `create_page`, `search_pages`, `update_database`, `get_blocks` | Knowledge management, documentation |
| **GitHub** | `create_pr`, `review_pr`, `search_code`, `manage_issues` | Code workflow, release management |

### Home & Environment

| Integration | Tools | Value |
|-------------|-------|-------|
| **HomeKit** | `get_devices`, `control_device`, `get_room_status` | Home automation, energy monitoring |
| **Calendar** (Google/Apple) | `create_event`, `list_events`, `find_free_slots` | Schedule management, meeting prep |
| **Weather** | `get_forecast`, `get_alerts`, `get_current` | Context-aware planning, alert delivery |

### Data & Knowledge

| Integration | Tools | Value |
|-------------|-------|-------|
| **PostgreSQL** | `query`, `list_tables`, `get_schema` | Data analysis, reporting |
| **Redis** | `get`, `set`, `pubsub`, `list_keys` | Caching, pub/sub messaging |
| **Elasticsearch** | `search`, `index`, `get_cluster_health` | Log analysis, full-text search |

---

## 8. Plugin Architecture: How SOUL.md References Integrations

SOUL.md section 8 ("Extension Architecture") outlines how PARAM absorbs new capabilities. When you add an integration, update that section with a brief entry.

### Before (current SOUL.md)

```markdown
### What Integration Means

A new integration could be anything:
- A new agent or reasoning system.
- A new tool, API, or data source.
- A new communication channel (Slack, email, voice).
- A new execution environment.
```

### After (with Slack added)

```markdown
### Active Integrations

| Integration | Prefix | Status | Purpose |
|-------------|--------|--------|---------|
| Hermes | `hermes__*` | Active | Telegram, cron, notifications, state |
| Huly | `mcp__huly__*` | Active | Project tracking, issues, documentation |
| Slack | `mcp__slack__*` | Active | Team messaging, alert delivery |

### What Integration Means

A new integration could be anything:
- A new agent or reasoning system.
- A new tool, API, or data source.
- A new communication channel (Slack, email, voice).
- A new execution environment.
```

This keeps the soul document fresh without needing to rewrite it every time.

---

## 9. Design Constraints

When building a new integration, respect these rules:

1. **No identity drift.** The integration is a tool, not a personality. PARAM remains Jarvis regardless of what MCP servers are plugged in.

2. **Namespace isolation.** Always use a unique prefix (`mcp__<server>__`) to prevent tool name collisions across integrations.

3. **Structured errors.** MCP tools should return JSON with an `error` key on failure, not raw exceptions. OMO handles these gracefully; tracebacks clutter the session.

4. **Stateless tools preferred.** Where possible, tools should be functional (input → output). If state must be maintained, use Hermes `state_set`/`state_get` or the integration's own persistence layer.

5. **No secrets in code.** Tokens, API keys, and credentials live in environment variables (set via `~/.mcp.json` `env` block) or in `~/.hermes/config.yaml`. Never hardcode them in the MCP server script.

6. **Test standalone first.** Run the MCP server directly (`python param_foo_mcp.py`) and send it JSON-RPC messages to verify it works before wiring it into OMO.

---

## 10. Quick Reference

| Task | File |
|------|------|
| Register MCP server | `~/.mcp.json` |
| PARAM identity & tool awareness | `~/.config/opencode/AGENTS.md` |
| PARAM persona & integration philosophy | `SOUL.md` (in this repo) |
| Provider configuration | `~/.config/opencode/opencode.json` |
| Hermes config & tokens | `~/.hermes/config.yaml` |
| Reference MCP server | `param_hermes_mcp.py` (in this repo) |
| Troubleshooting | `specs/TROUBLESHOOTING.md` |
