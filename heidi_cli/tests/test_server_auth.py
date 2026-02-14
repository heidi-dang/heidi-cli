
import os
import unittest
from unittest.mock import MagicMock, patch

# In CI/complete environments, dependencies like keyring/github_copilot_sdk are installed.
# We do not mock them here to avoid import side effects.
# If running locally without dependencies, use pip install or a separate conftest.

from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient

# Mocking the environment before importing server
os.environ["HEIDI_API_KEY"] = ""

# Now import server
from heidi_cli.server import app, _require_api_key

class TestSecurityVulnerability(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Ensure clean state for HEIDI_API_KEY
        from heidi_cli import server
        self.original_api_key = server.HEIDI_API_KEY
        server.HEIDI_API_KEY = ""

    def tearDown(self):
        from heidi_cli import server
        server.HEIDI_API_KEY = self.original_api_key

    def test_missing_authentication_enforcement(self):
        # Create a dummy endpoint that uses _require_api_key
        # We need to add it to the app dynamically for testing

        # Note: Adding routes dynamically to FastAPI app is tricky because of router
        # Instead, we can use an existing protected endpoint or mocking request
        # But for this specific vulnerability, calling _require_api_key directly or via endpoint is key

        # Let's add a temporary route
        @app.get("/test-protected-vuln")
        def protected_endpoint(request: Request):
            _require_api_key(request)
            return {"status": "success"}

        # Make a request without any authentication headers or session
        response = self.client.get("/test-protected-vuln")

        # Expect 401 Unauthorized (Fix verification)
        self.assertEqual(response.status_code, 401, "Fix verified: Authentication is enforced even without HEIDI_API_KEY")

    def test_authentication_with_api_key(self):
        # Test that it works WITH an API key set
        @app.get("/test-protected-auth")
        def protected_endpoint_2(request: Request):
            _require_api_key(request)
            return {"status": "success"}

        from heidi_cli import server
        server.HEIDI_API_KEY = "secret-key"

        # Request with correct key
        response = self.client.get("/test-protected-auth", headers={"X-Heidi-Key": "secret-key"})
        self.assertEqual(response.status_code, 200, "Should allow access with valid API key")

        # Request with incorrect key
        response = self.client.get("/test-protected-auth", headers={"X-Heidi-Key": "wrong-key"})
        self.assertEqual(response.status_code, 401, "Should deny access with invalid API key")

            # Request with no key
        response = self.client.get("/test-protected-auth")
        self.assertEqual(response.status_code, 401, "Should deny access with missing API key")
