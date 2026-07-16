import sys
import os
from unittest.mock import MagicMock

# Mock external services that are not installed in test environment
# and would block test collection for API tests importing ai modules
if "openai" not in sys.modules:
    sys.modules["openai"] = MagicMock()
if "httpx" not in sys.modules:
    sys.modules["httpx"] = MagicMock()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
