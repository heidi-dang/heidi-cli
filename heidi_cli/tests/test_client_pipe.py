import sys
import os
import pytest
from unittest.mock import AsyncMock, patch

# client.py is in root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from client import Pipe

@pytest.mark.anyio
async def test_pipe_routing_chat():
    pipe = Pipe()
    pipe.valves.HEIDI_SERVER_URL = "http://test-server"

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"response": "Chat response"}

        body = {"messages": [{"role": "user", "content": "chat: hello"}]}
        result = await pipe.pipe(body)

        assert result == "Chat response"
        mock_post.assert_called_with(
            "http://test-server/chat",
            json={"message": "hello", "executor": "copilot"},
            headers={"Content-Type": "application/json"},
            timeout=300
        )

@pytest.mark.anyio
async def test_pipe_routing_run():
    pipe = Pipe()
    pipe.valves.HEIDI_SERVER_URL = "http://test-server"

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "status": "completed",
            "result": "Run result",
            "run_id": "123"
        }

        body = {"messages": [{"role": "user", "content": "run: task"}]}
        result = await pipe.pipe(body)

        assert "Run Started" in result
        assert "Run result" in result
        mock_post.assert_called_with(
            "http://test-server/run",
            json={"prompt": "task", "executor": "copilot", "model": "gpt-5"},
            headers={"Content-Type": "application/json"},
            timeout=300
        )

@pytest.mark.anyio
async def test_pipe_routing_loop():
    pipe = Pipe()
    pipe.valves.HEIDI_SERVER_URL = "http://test-server"

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "status": "running",
            "run_id": "456"
        }

        body = {"messages": [{"role": "user", "content": "loop: huge task"}]}
        result = await pipe.pipe(body)

        assert "Agent Loop Started" in result
        assert "huge task" in result
        mock_post.assert_called_with(
            "http://test-server/loop",
            json={"task": "huge task", "executor": "copilot", "max_retries": 2, "model": "gpt-5"},
            headers={"Content-Type": "application/json"},
            timeout=300
        )

@pytest.mark.anyio
async def test_pipe_default_orchestrated():
    pipe = Pipe()
    pipe.valves.HEIDI_SERVER_URL = "http://test-server"

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "status": "completed",
            "result": "Default result",
            "run_id": "789"
        }

        body = {"messages": [{"role": "user", "content": "just talking"}]}
        result = await pipe.pipe(body)

        # Default calls chat_orchestrated -> calls /run
        assert "Default result" in result
        mock_post.assert_called_with(
            "http://test-server/run",
            json={"prompt": "just talking", "executor": "copilot", "model": "gpt-5"},
            headers={"Content-Type": "application/json"},
            timeout=300
        )
