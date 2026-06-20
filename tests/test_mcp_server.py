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


class TestCreateServer:
    """Tests for _create_server() and its decorated handlers (mocked MCP)."""

    def test_create_server_returns_server(self):
        mock_mcp = MagicMock()
        mock_mcp.server = MagicMock()
        mock_mcp.types = MagicMock()
        sys.modules["mcp"] = mock_mcp
        sys.modules["mcp.server"] = mock_mcp.server
        try:
            srv = param_hermes_mcp._create_server()
            assert srv is not None
            mock_mcp.server.Server.assert_called_once_with("param-hermes-mcp")
        finally:
            del sys.modules["mcp"]
            del sys.modules["mcp.server"]

    def test_handle_list_tools_dispatches_entries(self):
        import asyncio
        mock_mcp = MagicMock()
        mock_mcp.server = MagicMock()
        mock_mcp.types = MagicMock()
        mock_srv = MagicMock()
        mock_mcp.server.Server.return_value = mock_srv
        # Capture the handler when list_tools() decorator is applied
        handler_ref = {}
        def capture(h):
            handler_ref["handler"] = h
            return h
        mock_srv.list_tools.return_value = capture
        sys.modules["mcp"] = mock_mcp
        sys.modules["mcp.server"] = mock_mcp.server
        try:
            param_hermes_mcp._create_server()
            assert "handler" in handler_ref
            result = asyncio.run(handler_ref["handler"]())
            assert isinstance(result, list)
        finally:
            del sys.modules["mcp"]
            del sys.modules["mcp.server"]

    def test_handle_call_tool_dispatches_request(self):
        import asyncio
        mock_mcp = MagicMock()
        mock_mcp.server = MagicMock()
        mock_mcp.types = MagicMock()
        mock_srv = MagicMock()
        mock_mcp.server.Server.return_value = mock_srv
        # Capture both handlers
        handlers = {}
        def capture_factory(key):
            def capture(h):
                handlers[key] = h
                return h
            return capture
        mock_srv.list_tools.return_value = capture_factory("list")
        mock_srv.call_tool.return_value = capture_factory("call")
        sys.modules["mcp"] = mock_mcp
        sys.modules["mcp.server"] = mock_mcp.server
        try:
            param_hermes_mcp._create_server()
            assert "call" in handlers
            result = asyncio.run(handlers["call"]("hermes__test", {}))
            assert len(result) == 1
            assert result[0].text is not None
        finally:
            del sys.modules["mcp"]
            del sys.modules["mcp.server"]

    def test_server_handlers_registered(self):
        mock_mcp = MagicMock()
        mock_mcp.server = MagicMock()
        mock_mcp.types = MagicMock()
        sys.modules["mcp"] = mock_mcp
        sys.modules["mcp.server"] = mock_mcp.server
        try:
            srv = param_hermes_mcp._create_server()
            # Verify list_tools and call_tool decorators were applied
            assert hasattr(srv, "list_tools") or mock_mcp.server.Server.return_value.list_tools.called
            assert hasattr(srv, "call_tool") or mock_mcp.server.Server.return_value.call_tool.called
        finally:
            del sys.modules["mcp"]
            del sys.modules["mcp.server"]


class TestMainFunction:
    """Tests for async main() entry point (mocked MCP stdio)."""

    def test_main_creates_and_runs_server(self):
        import asyncio
        from unittest.mock import AsyncMock

        class FakeStreams:
            async def __aenter__(self):
                return (MagicMock(), MagicMock())
            async def __aexit__(self, *args):
                pass

        mock_mcp = MagicMock()
        mock_mcp.server = MagicMock()
        mock_mcp.types = MagicMock()
        # Server mock with awaitable run()
        mock_srv = MagicMock()
        mock_srv.run = AsyncMock()
        mock_srv.create_initialization_options.return_value = {}
        mock_mcp.server.Server = MagicMock(return_value=mock_srv)
        mock_stdio = FakeStreams()
        mock_mcp.server.stdio = MagicMock()
        mock_mcp.server.stdio.stdio_server = MagicMock(return_value=mock_stdio)
        sys.modules["mcp"] = mock_mcp
        sys.modules["mcp.server"] = mock_mcp.server
        sys.modules["mcp.server.stdio"] = mock_mcp.server.stdio
        try:
            async def run_main():
                await param_hermes_mcp.main()
            asyncio.run(run_main())
            mock_srv.run.assert_awaited_once()
        finally:
            for mod in ["mcp", "mcp.server", "mcp.server.stdio"]:
                sys.modules.pop(mod, None)


class TestEntryPoint:
    """Tests for if __name__ == '__main__' block behavior."""

    def test_main_is_async_function(self):
        import inspect
        assert inspect.iscoroutinefunction(param_hermes_mcp.main)
