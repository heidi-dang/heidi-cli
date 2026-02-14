import os
import sys
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Set env before import
os.environ["HEIDI_API_KEY"] = "test-secret"
os.environ["HEIDI_AUTH_MODE"] = "optional"

# Now import app
from heidi_cli.server import app, HEIDI_API_KEY

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_options_cors():
    response = client.options(
        "/run",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200

def test_run_auth_failure():
    # Patch HEIDI_API_KEY if it wasn't picked up correctly
    with patch("heidi_cli.server.HEIDI_API_KEY", "test-secret"):
        response = client.post("/run", json={"prompt": "hello"})
        assert response.status_code == 401

def test_run_dry_run():
    with patch("heidi_cli.server.HEIDI_API_KEY", "test-secret"):
        response = client.post(
            "/run",
            json={"prompt": "hello", "dry_run": True},
            headers={"X-Heidi-Key": "test-secret"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        # Since dry_run for /run returns simulated response immediately
        assert "Dry run" in data["result"]

def test_loop_dry_run():
    with patch("heidi_cli.server.HEIDI_API_KEY", "test-secret"):
        # We mock run_loop where it is imported in server.py (local import inside function)
        # Patching local import inside function is tricky. We must patch the module where it comes from.
        with patch("heidi_cli.orchestrator.loop.run_loop", new_callable=AsyncMock) as mock_loop:
            mock_loop.return_value = "Plan generated"

            response = client.post(
                "/loop",
                json={"task": "do something", "dry_run": True},
                headers={"X-Heidi-Key": "test-secret"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "running"

def test_chat_auth_failure():
    with patch("heidi_cli.server.HEIDI_API_KEY", "test-secret"):
        response = client.post("/chat", json={"message": "hello"})
        assert response.status_code == 401

def test_chat_success():
    with patch("heidi_cli.server.HEIDI_API_KEY", "test-secret"):
        # Mock pick_executor to return a mock executor
        with patch("heidi_cli.orchestrator.loop.pick_executor") as mock_pick:
            mock_executor = AsyncMock()
            mock_executor.run.return_value.output = "Chat response"
            mock_executor.run.return_value.ok = True
            mock_pick.return_value = mock_executor

            response = client.post(
                "/chat",
                json={"message": "hello"},
                headers={"X-Heidi-Key": "test-secret"}
            )
            assert response.status_code == 200
            assert response.json()["response"] == "Chat response"
