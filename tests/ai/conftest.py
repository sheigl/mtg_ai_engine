"""AI test configuration — mock external services before ai_client imports.

Uses a session-scoped autouse fixture so the mocks only activate during AI test
execution, not during pytest collection of other test directories (which need
real httpx for starlette TestClient).
"""
import sys
from unittest.mock import MagicMock
import pytest


@pytest.fixture(autouse=True, scope="session")
def _mock_ai_external_services():
    """Mock openai and httpx to prevent real API calls from ai_client.

    This fixture runs before any AI test but after collection is complete,
    so it doesn't interfere with API tests that need real httpx/starlette.
    """
    if "openai" not in sys.modules:
        _orig_openai = None
    else:
        _orig_openai = sys.modules["openai"]

    if "httpx" not in sys.modules:
        _orig_httpx = None
    else:
        _orig_httpx = sys.modules["httpx"]

    # Only mock if real modules are present (not already mocked)
    needs_mock_openai = _orig_openai is not None and type(_orig_openai).__name__ != "MagicMock"
    needs_mock_httpx = _orig_httpx is not None and type(_orig_httpx).__name__ != "MagicMock"

    if needs_mock_openai:
        sys.modules["openai"] = MagicMock()
    if needs_mock_httpx:
        sys.modules["httpx"] = MagicMock()

    yield

    # Restore originals on teardown (not strictly necessary for tests, but clean)
    if needs_mock_openai and _orig_openai is not None:
        sys.modules["openai"] = _orig_openai
    if needs_mock_httpx and _orig_httpx is not None:
        sys.modules["httpx"] = _orig_httpx
