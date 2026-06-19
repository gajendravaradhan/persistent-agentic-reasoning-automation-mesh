import sys, os, json
from unittest.mock import MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

_reg = MagicMock()
_reg._snapshot_entries.return_value = []
_reg.dispatch.return_value = '{"ok": true}'
_rt = MagicMock()
_rt.registry = _reg
_rt.discover_builtin_tools = MagicMock()
sys.modules["tools.registry"] = _rt

import param_hermes_mcp


class TestServerCreation:
    def test_build_tool_entries_integration(self):
        e = MagicMock()
        e.name = "test_tool"
        e.description = "test"
        e.schema = {"description": "Test", "parameters": {"type": "object"}}
        _reg._snapshot_entries.return_value = [e]
        entries = param_hermes_mcp._build_tool_entries([e])
        assert len(entries) == 1
        assert entries[0]["name"] == "hermes__test_tool"
        assert "inputSchema" in entries[0]


class TestCallResponseIntegration:
    def test_valid_dispatch(self):
        _reg.dispatch.return_value = '{"status": "healthy"}'
        _reg.dispatch.side_effect = None
        r = param_hermes_mcp._build_call_response("hermes__status", {}, _reg.dispatch)
        assert r["is_error"] is False
        assert "healthy" in r["text"]

    def test_dispatch_error(self):
        _reg.dispatch.side_effect = ConnectionError("TokenEye unreachable")
        _reg.dispatch.return_value = None
        r = param_hermes_mcp._build_call_response("hermes__check", {}, _reg.dispatch)
        assert r["is_error"] is True
        assert "ConnectionError" in json.loads(r["text"])["error"]

    def test_unknown_tool(self):
        r = param_hermes_mcp._build_call_response("bad", {}, _reg.dispatch)
        assert r["is_error"] is True
        assert "Unknown tool" in json.loads(r["text"])["error"]


class TestPrefixFunctional:
    def test_prefix_constant(self):
        assert param_hermes_mcp.PREFIX == "hermes__"

    def test_prefix_stripping(self):
        name = "hermes__cronjob"
        assert name[len(param_hermes_mcp.PREFIX):] == "cronjob"
