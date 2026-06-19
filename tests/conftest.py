import sys, os
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
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.Server"] = MagicMock()
sys.modules["mcp.server.stdio"] = MagicMock()
sys.modules["mcp.types"] = MagicMock()
