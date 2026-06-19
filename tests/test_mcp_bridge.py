import sys, os, json
from unittest.mock import MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
import param_hermes_mcp


class TestToMcpSchema:
    def test_normal(self):
        e = MagicMock()
        e.schema = {"parameters": {"type": "object", "properties": {"a": {"type": "str"}}, "required": ["a"]}}
        r = param_hermes_mcp._to_mcp_schema(e)
        assert r["type"] == "object"
        assert r["properties"] == {"a": {"type": "str"}}

    def test_empty(self):
        r = param_hermes_mcp._to_mcp_schema(MagicMock())
        assert r["type"] == "object"

    def test_not_dict(self):
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


class TestBuildToolEntries:
    def _e(self, n, d="desc"):
        e = MagicMock()
        e.name = n
        e.description = d
        e.schema = {"description": d, "parameters": {"type": "object"}}
        return e

    def test_one(self):
        r = param_hermes_mcp._build_tool_entries([self._e("a")])
        assert len(r) == 1
        assert r[0]["name"] == "hermes__a"

    def test_custom_prefix(self):
        r = param_hermes_mcp._build_tool_entries([self._e("t")], prefix="x__")
        assert r[0]["name"] == "x__t"

    def test_many(self):
        r = param_hermes_mcp._build_tool_entries([self._e("a"), self._e("b")])
        assert len(r) == 2

    def test_empty(self):
        assert param_hermes_mcp._build_tool_entries([]) == []

    def test_malformed_skipped(self):
        bad = MagicMock()
        bad.name = "bad"
        bad.schema = None
        assert param_hermes_mcp._build_tool_entries([bad]) == []


class TestBuildCallResponse:
    def test_valid(self):
        r = param_hermes_mcp._build_call_response("hermes__t", {"k": "v"}, lambda n, a: '{"ok":1}')
        assert json.loads(r["text"]) == {"ok": 1}
        assert r["is_error"] is False

    def test_unknown_prefix(self):
        r = param_hermes_mcp._build_call_response("bad", {}, lambda n, a: "")
        assert r["is_error"] is True
        assert "Unknown tool" in json.loads(r["text"])["error"]

    def test_dispatch_error(self):
        r = param_hermes_mcp._build_call_response("hermes__x", {}, lambda n, a: (_ for _ in ()).throw(RuntimeError("fail")))
        assert r["is_error"] is True
        assert "RuntimeError" in json.loads(r["text"])["error"]

    def test_prefix_strip(self):
        c = {}
        param_hermes_mcp._build_call_response("hermes__cron", {"i": 60}, lambda n, a: c.update({"n": n, "a": a}))
        assert c["n"] == "cron"

    def test_empty_args(self):
        r = param_hermes_mcp._build_call_response("hermes__t", {}, lambda n, a: "{}")
        assert r["is_error"] is False

    def test_custom_prefix_ok(self):
        r = param_hermes_mcp._build_call_response("x__t", {}, lambda n, a: "{}", prefix="x__")
        assert r["is_error"] is False

    def test_wrong_prefix_fails(self):
        r = param_hermes_mcp._build_call_response("hermes__t", {}, lambda n, a: "", prefix="x__")
        assert r["is_error"] is True


class TestPrefix:
    def test_value(self):
        assert param_hermes_mcp.PREFIX == "hermes__"

    def test_strip(self):
        assert "hermes__x"[len(param_hermes_mcp.PREFIX):] == "x"

    def test_detection(self):
        assert not "bad".startswith(param_hermes_mcp.PREFIX)
        assert "hermes__y".startswith(param_hermes_mcp.PREFIX)
