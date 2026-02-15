import pytest
from unittest.mock import patch, MagicMock
import requests
import sys
import os

# Add project root to sys.path to allow importing client.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from client import Pipe


@pytest.fixture
def pipe():
    return Pipe()


@pytest.mark.asyncio
async def test_execute_loop_connection_error(pipe):
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError):
        result = await pipe.execute_loop("task")
        assert "**Connection Error**" in result
        assert "Could not connect to Heidi server" in result


@pytest.mark.asyncio
async def test_execute_loop_timeout_error(pipe):
    with patch("requests.post", side_effect=requests.exceptions.Timeout):
        result = await pipe.execute_loop("task")
        assert "**Timeout Error**" in result
        assert "Try increasing REQUEST_TIMEOUT valve" in result


@pytest.mark.asyncio
async def test_execute_loop_auth_error(pipe):
    mock_response = MagicMock()
    mock_response.status_code = 401
    error = requests.exceptions.HTTPError(response=mock_response)
    with patch("requests.post", side_effect=error):
        result = await pipe.execute_loop("task")
        assert "**Authentication Error**" in result
        assert "Ensure HEIDI_API_KEY valve is set correctly" in result


@pytest.mark.asyncio
async def test_execute_loop_generic_error(pipe):
    with patch("requests.post", side_effect=Exception("Generic error")):
        result = await pipe.execute_loop("task")
        assert "**Heidi Loop Error**" in result
        assert "Generic error" in result


@pytest.mark.asyncio
async def test_execute_run_timeout_error(pipe):
    with patch("requests.post", side_effect=requests.exceptions.Timeout):
        result = await pipe.execute_run("prompt")
        assert "**Timeout Error**" in result
        # Refactored: now includes the tip
        assert "Try increasing REQUEST_TIMEOUT valve" in result


@pytest.mark.asyncio
async def test_execute_run_generic_error(pipe):
    with patch("requests.post", side_effect=Exception("Generic error")):
        result = await pipe.execute_run("prompt")
        assert "**Heidi Run Error**" in result


@pytest.mark.asyncio
async def test_list_runs_generic_error(pipe):
    with patch("requests.get", side_effect=Exception("Generic error")):
        result = await pipe.list_runs()
        assert "**Error listing runs**" in result


@pytest.mark.asyncio
@pytest.mark.skip(reason="chat_with_heidi method not yet implemented in main")
async def test_chat_timeout_error(pipe):
    with patch("requests.post", side_effect=requests.exceptions.Timeout):
        result = await pipe.chat_with_heidi([{"content": "hi"}])
        assert "**Timeout Error**" in result
        # Refactored: now includes the tip
        assert "Try increasing REQUEST_TIMEOUT valve" in result
