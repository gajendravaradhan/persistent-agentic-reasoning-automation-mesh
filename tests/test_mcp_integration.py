import json
import os
import sys
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

_reg = MagicMock()
_reg._snapshot_entries.return_value = []
_reg.dispatch.return_value = '{"ok": true}'
_rt = MagicMock()
_rt.registry = _reg
_rt.discover_builtin_tools = MagicMock()
sys.modules.setdefault("tools.registry", _rt)

import param_hermes_mcp


def _make_entry(name, description="A test tool", params=None):
    e = MagicMock()
    e.name = name
    e.description = description
    e.schema = {
        "description": description,
        "parameters": params or {"type": "object", "properties": {}, "required": []},
    }
    return e


class TestToolDiscovery:
    def test_build_returns_list(self):
        entries = [_make_entry("web_search"), _make_entry("terminal")]
        tools = param_hermes_mcp._build_tool_entries(entries)
        assert isinstance(tools, list)
        assert len(tools) == 2

    def test_each_tool_has_required_mcp_fields(self):
        entries = [_make_entry("memory"), _make_entry("file_read"), _make_entry("web_extract")]
        tools = param_hermes_mcp._build_tool_entries(entries)
        for tool in tools:
            assert "name" in tool, f"Missing 'name' in {tool}"
            assert "description" in tool, f"Missing 'description' in {tool}"
            assert "inputSchema" in tool, f"Missing 'inputSchema' in {tool}"

    def test_tool_names_prefixed_with_hermes(self):
        entries = [_make_entry("web_search"), _make_entry("terminal"), _make_entry("kanban_complete")]
        tools = param_hermes_mcp._build_tool_entries(entries)
        for tool in tools:
            assert tool["name"].startswith("hermes__"), f"Tool not prefixed: {tool['name']}"

    def test_input_schema_is_valid_json_schema(self):
        params = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        entries = [_make_entry("search", params=params)]
        tools = param_hermes_mcp._build_tool_entries(entries)
        schema = tools[0]["inputSchema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "query" in schema["properties"]

    def test_empty_registry_returns_empty_list(self):
        tools = param_hermes_mcp._build_tool_entries([])
        assert tools == []

    def test_tool_count_with_multiple_entries(self):
        entries = [_make_entry(f"tool_{i}") for i in range(10)]
        tools = param_hermes_mcp._build_tool_entries(entries)
        assert len(tools) == 10

    def test_description_propagated_from_schema(self):
        e = _make_entry("my_tool", description="Does something useful")
        tools = param_hermes_mcp._build_tool_entries([e])
        assert "something useful" in tools[0]["description"]

    def test_bad_entry_skipped_gracefully(self):
        good = _make_entry("good_tool")
        bad = MagicMock()
        bad.name = "bad_tool"
        bad.schema = MagicMock(side_effect=Exception("schema error"))
        bad.description = "bad"
        tools = param_hermes_mcp._build_tool_entries([good, bad])
        names = [t["name"] for t in tools]
        assert "hermes__good_tool" in names


class TestToolDispatch:
    def test_successful_dispatch_returns_result(self):
        dispatch = MagicMock(return_value='{"status": "ok", "data": 42}')
        result = param_hermes_mcp._build_call_response("hermes__my_tool", {"arg": "val"}, dispatch)
        assert result["is_error"] is False
        assert "ok" in result["text"]

    def test_tool_name_stripped_of_prefix_before_dispatch(self):
        dispatch = MagicMock(return_value='{"result": true}')
        param_hermes_mcp._build_call_response("hermes__web_search", {"query": "test"}, dispatch)
        dispatch.assert_called_once_with("web_search", {"query": "test"})

    def test_arguments_passed_through_unchanged(self):
        dispatch = MagicMock(return_value='{}')
        args = {"query": "hello", "limit": 5, "deep": True}
        param_hermes_mcp._build_call_response("hermes__search", args, dispatch)
        _, called_args = dispatch.call_args
        assert dispatch.call_args[0][1] == args

    def test_response_has_text_and_is_error_fields(self):
        dispatch = MagicMock(return_value='{"data": "something"}')
        result = param_hermes_mcp._build_call_response("hermes__tool", {}, dispatch)
        assert "text" in result
        assert "is_error" in result

    def test_dispatch_result_serialized_in_text(self):
        dispatch = MagicMock(return_value='{"count": 99}')
        result = param_hermes_mcp._build_call_response("hermes__count", {}, dispatch)
        assert "99" in result["text"]


class TestErrorHandling:
    def test_unknown_tool_no_prefix_returns_error(self):
        dispatch = MagicMock()
        result = param_hermes_mcp._build_call_response("no_prefix_tool", {}, dispatch)
        assert result["is_error"] is True
        assert "Unknown tool" in result["text"] or "error" in result["text"].lower()
        dispatch.assert_not_called()

    def test_wrong_prefix_returns_error(self):
        dispatch = MagicMock()
        result = param_hermes_mcp._build_call_response("openai__tool", {}, dispatch)
        assert result["is_error"] is True
        dispatch.assert_not_called()

    def test_connection_error_returns_graceful_error(self):
        dispatch = MagicMock(side_effect=ConnectionError("Hermes unreachable"))
        result = param_hermes_mcp._build_call_response("hermes__terminal", {"cmd": "ls"}, dispatch)
        assert result["is_error"] is True
        assert "error" in result["text"].lower()

    def test_timeout_error_returns_graceful_error(self):
        dispatch = MagicMock(side_effect=TimeoutError("Request timed out after 30s"))
        result = param_hermes_mcp._build_call_response("hermes__web_search", {}, dispatch)
        assert result["is_error"] is True
        assert "error" in result["text"].lower()

    def test_generic_exception_returns_graceful_error(self):
        dispatch = MagicMock(side_effect=RuntimeError("Something exploded"))
        result = param_hermes_mcp._build_call_response("hermes__tool", {}, dispatch)
        assert result["is_error"] is True
        data = json.loads(result["text"])
        assert "error" in data

    def test_error_response_is_valid_json(self):
        dispatch = MagicMock(side_effect=ValueError("bad input"))
        result = param_hermes_mcp._build_call_response("hermes__tool", {}, dispatch)
        assert result["is_error"] is True
        parsed = json.loads(result["text"])
        assert isinstance(parsed, dict)

    def test_empty_tool_name_returns_error(self):
        dispatch = MagicMock()
        result = param_hermes_mcp._build_call_response("", {}, dispatch)
        assert result["is_error"] is True
        dispatch.assert_not_called()

    def test_none_dispatch_result_handled(self):
        dispatch = MagicMock(return_value=None)
        result = param_hermes_mcp._build_call_response("hermes__tool", {}, dispatch)
        assert "is_error" in result
        assert "text" in result


class TestMcpSchemaConversion:
    def test_complex_schema_preserved(self):
        params = {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target URL"},
                "timeout": {"type": "integer", "default": 30},
            },
            "required": ["url"],
        }
        entry = _make_entry("fetch", params=params)
        tools = param_hermes_mcp._build_tool_entries([entry])
        schema = tools[0]["inputSchema"]
        assert schema["properties"]["url"]["type"] == "string"
        assert schema["properties"]["timeout"]["type"] == "integer"
        assert "url" in schema["required"]

    def test_schema_always_has_type_object(self):
        for params in [None, {}, {"properties": {}}, {"type": "object"}]:
            entry = _make_entry("tool", params=params)
            tools = param_hermes_mcp._build_tool_entries([entry])
            assert tools[0]["inputSchema"]["type"] == "object"

    def test_schema_always_has_properties(self):
        entry = _make_entry("tool")
        tools = param_hermes_mcp._build_tool_entries([entry])
        assert "properties" in tools[0]["inputSchema"]
