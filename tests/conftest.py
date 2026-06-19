# conftest.py — shared pytest fixtures for PARAM tests
import os
import sys
from unittest.mock import MagicMock, patch
import pytest

# Ensure the project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def mock_registry_entry():
    """Create a mock Hermes registry entry."""
    entry = MagicMock()
    entry.name = "test_tool"
    entry.description = "A test tool"
    entry.schema = {
        "description": "A test tool for unit testing",
        "parameters": {
            "type": "object",
            "properties": {"param1": {"type": "string"}},
            "required": ["param1"],
        },
    }
    return entry


@pytest.fixture
def mock_registry_entry_no_params():
    """Mock entry with no parameters schema."""
    entry = MagicMock()
    entry.name = "simple_tool"
    entry.description = "Simple tool"
    entry.schema = {"description": "Simple tool"}
    return entry


@pytest.fixture
def mock_registry_entry_empty_params():
    """Mock entry with empty parameters."""
    entry = MagicMock()
    entry.name = "empty_tool"
    entry.description = None
    entry.schema = {
        "description": "Empty tool",
        "parameters": {},
    }
    return entry


@pytest.fixture
def mock_registry_entry_malformed():
    """Mock entry with malformed parameters (not a dict)."""
    entry = MagicMock()
    entry.name = "bad_tool"
    entry.description = "Bad tool"
    entry.schema = {
        "description": "Bad tool",
        "parameters": "not_a_dict",
    }
    return entry


@pytest.fixture
def mock_registry_with_entries(mock_registry_entry):
    """Mock registry with test entries."""
    registry = MagicMock()
    registry._snapshot_entries.return_value = [mock_registry_entry]
    registry.dispatch.return_value = '{"result": "ok"}'
    return registry


@pytest.fixture(autouse=True)
def isolate_hermes_home(tmp_path):
    """Ensure HERMES_HOME doesn't leak between tests."""
    old_home = os.environ.get("HERMES_HOME")
    os.environ["HERMES_HOME"] = str(tmp_path)
    yield
    if old_home:
        os.environ["HERMES_HOME"] = old_home
    else:
        os.environ.pop("HERMES_HOME", None)
