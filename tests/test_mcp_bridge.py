"""Tests for param_hermes_mcp.py — patching mcp.server.Server to avoid Pydantic."""
import sys, os
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

_reg = MagicMock()
_reg._snapshot_entries.return_value = []
_reg.dispatch.return_value = '{"ok": true}'
_rt = MagicMock()
_rt.registry = _reg
_rt.discover_builtin_tools = MagicMock()
sys.modules["tools.registry"] = _rt

# Patch Server class directly — prevents Pydantic from seeing MagicMock types
_mock_server_cls = MagicMock()
_mock_server_cls.return_value = MagicMock()

with patch("mcp.server.Server", _mock_server_cls):
    import param_hermes_mcp


class TestToMcpSchema:
    def test_normal(self):
        e = MagicMock()
        e.schema = {"parameters": {"type": "object", "properties": {"a": {"type": "str"}}, "required": ["a"]}}
        r = param_hermes_mcp._to_mcp_schema(e)
        assert r["type"] == "object"
        assert r["properties"] == {"a": {"type": "str"}}
        assert r["required"] == ["a"]

    def test_empty_params(self):
        e = MagicMock()
        e.schema = {}
        r = param_hermes_mcp._to_mcp_schema(e)
        assert r["type"] == "object"
        assert r["properties"] == {}

    def test_bad_type(self):
        e = MagicMock()
        e.schema = {"parameters": 42}
        r = param_hermes_mcp._to_mcp_schema(e)
        assert r["type"] == "object"

    def test_missing_type(self):
        e = MagicMock()
        e.schema = {"parameters": {"properties": {"x": {}}}}
        r = param_hermes_mcp._to_mcp_schema(e)
        assert r["type"] == "object"

    def test_missing_props(self):
        e = MagicMock()
        e.schema = {"parameters": {"type": "object"}}
        r = param_hermes_mcp._to_mcp_schema(e)
        assert r["properties"] == {}


class TestPrefix:
    def test_value(self):
        assert param_hermes_mcp.PREFIX == "hermes__"

    def test_strip(self):
        assert "hermes__cronjob"[len(param_hermes_mcp.PREFIX):] == "cronjob"


class TestServerExists:
    def test_has_server(self):
        assert hasattr(param_hermes_mcp, "server")
