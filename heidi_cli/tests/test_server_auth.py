
import os
import sys
import unittest
from unittest.mock import MagicMock

# Defer imports to avoid collection-time errors if dependencies are missing/conflicted
# This is crucial for CI environments where package loading order might be sensitive

class TestSecurityVulnerability(unittest.TestCase):
    def setUp(self):
        # Import inside method to avoid top-level failures
        try:
            from fastapi.testclient import TestClient
            from heidi_cli import server

            self.app = server.app
            self.client = TestClient(self.app)
            self.server_module = server

            # Ensure clean state for HEIDI_API_KEY
            self.original_api_key = self.server_module.HEIDI_API_KEY
            self.server_module.HEIDI_API_KEY = ""
        except ImportError as e:
            self.skipTest(f"Skipping test due to missing dependencies: {e}")
        except Exception as e:
            # If pydantic error happens here, print debug info
            print(f"DEBUG: Error in setUp: {e}")
            if 'pydantic' in sys.modules:
                print(f"DEBUG: pydantic module: {sys.modules['pydantic']}")
                if hasattr(sys.modules['pydantic'], '__file__'):
                    print(f"DEBUG: pydantic file: {sys.modules['pydantic'].__file__}")
                else:
                    print(f"DEBUG: pydantic has no __file__")
            raise e

    def tearDown(self):
        if hasattr(self, 'server_module'):
            self.server_module.HEIDI_API_KEY = self.original_api_key

    def test_missing_authentication_enforcement(self):
        # We need to test the _require_api_key function or an endpoint using it
        # Since adding routes dynamically is complex, we'll assume there's a protected route
        # OR better: unit test the function directly if possible, but testing behavior via client is more robust integration test

        # Let's create a temporary router to test this specific behavior if we can
        # But we can't easily modify the app router in a thread-safe way for tests

        # However, the vulnerability was in _require_api_key logic
        # We can call it directly!

        try:
            from fastapi import Request, HTTPException
            from heidi_cli.server import _require_api_key

            # Mock a request
            mock_request = MagicMock(spec=Request)
            mock_request.headers = {}
            mock_request.query_params = {}
            mock_request.state.user = None

            # Case 1: No API Key set on server (HEIDI_API_KEY = "")
            # With the FIX, this should raise HTTPException(401)
            # Before the fix, it would return None (pass)

            with self.assertRaises(HTTPException) as cm:
                _require_api_key(mock_request)

            self.assertEqual(cm.exception.status_code, 401)

        except ImportError:
            pass # Handled in setUp

    def test_authentication_with_api_key(self):
        try:
            from fastapi import Request, HTTPException
            from heidi_cli.server import _require_api_key

            # Case 2: API Key set on server
            self.server_module.HEIDI_API_KEY = "secret-key"

            # Sub-case: Valid key provided
            mock_request_valid = MagicMock(spec=Request)
            mock_request_valid.headers = {"x-heidi-key": "secret-key"}
            mock_request_valid.state.user = None

            # Should not raise
            try:
                _require_api_key(mock_request_valid)
            except HTTPException:
                self.fail("_require_api_key raised HTTPException with valid key")

            # Sub-case: Invalid key provided
            mock_request_invalid = MagicMock(spec=Request)
            mock_request_invalid.headers = {"x-heidi-key": "wrong-key"}
            mock_request_invalid.state.user = None

            with self.assertRaises(HTTPException) as cm:
                _require_api_key(mock_request_invalid)
            self.assertEqual(cm.exception.status_code, 401)

             # Sub-case: No key provided
            mock_request_empty = MagicMock(spec=Request)
            mock_request_empty.headers = {}
            mock_request_empty.state.user = None

            with self.assertRaises(HTTPException) as cm:
                _require_api_key(mock_request_empty)
            self.assertEqual(cm.exception.status_code, 401)

        except ImportError:
            pass
