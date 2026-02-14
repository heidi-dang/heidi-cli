import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to sys.path so we can import client.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from client import Pipe
import requests

class TestExecuteRun:
    """Test the execute_run method of the Pipe class."""

    @pytest.fixture
    def pipe(self):
        """Fixture to provide a Pipe instance."""
        return Pipe()

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_execute_run_success(self, mock_post, pipe):
        """Test a successful run execution."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "run_id": "run-123",
            "status": "completed",
            "result": "Hello, world!",
            "error": ""
        }
        mock_post.return_value = mock_response

        prompt = "Say hello"
        result = await pipe.execute_run(prompt)

        assert "### ▶️ Run Started" in result
        assert "**Prompt:** Say hello" in result
        assert "**Run ID:** run-123" in result
        assert "**Output:**\n\nHello, world!" in result

        expected_url = f"{pipe.valves.HEIDI_SERVER_URL}/run"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == expected_url
        assert kwargs["json"]["prompt"] == prompt

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_execute_run_connection_error(self, mock_post, pipe):
        """Test connection error handling."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        result = await pipe.execute_run("test prompt")

        assert "**Connection Error**" in result
        assert "Could not connect to Heidi server" in result

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_execute_run_timeout(self, mock_post, pipe):
        """Test timeout handling."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        result = await pipe.execute_run("test prompt")

        assert "**Timeout Error**" in result
        assert "Request timed out after" in result

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_execute_run_auth_error(self, mock_post, pipe):
        """Test authentication error handling (401)."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        error = requests.exceptions.HTTPError("401 Unauthorized", response=mock_response)
        mock_post.side_effect = error

        result = await pipe.execute_run("test prompt")

        assert "**Authentication Error**" in result
        assert "Ensure HEIDI_API_KEY valve is set correctly" in result

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_execute_run_http_error(self, mock_post, pipe):
        """Test other HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        error = requests.exceptions.HTTPError("500 Internal Server Error", response=mock_response)
        mock_post.side_effect = error

        result = await pipe.execute_run("test prompt")

        assert "**HTTP Error**" in result
        assert "500 Internal Server Error" in result

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_execute_run_generic_exception(self, mock_post, pipe):
        """Test generic exception handling."""
        mock_post.side_effect = Exception("Something went wrong")

        result = await pipe.execute_run("test prompt")

        assert "**Heidi Run Error**" in result
        assert "Something went wrong" in result

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_execute_run_with_custom_executor(self, mock_post, pipe):
        """Test execute_run with a custom executor."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "run_id": "run-456",
            "status": "completed",
            "result": "Result from ollama",
            "error": ""
        }
        mock_post.return_value = mock_response

        prompt = "test prompt"
        executor = "ollama"
        model = "llama3"

        await pipe.execute_run(prompt, executor=executor, model=model)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        payload = kwargs["json"]

        assert payload["executor"] == executor
        # model is only sent if executor is copilot
        assert "model" not in payload

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_execute_run_with_copilot_executor(self, mock_post, pipe):
        """Test execute_run with copilot executor (sends model)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {} # mocked response
        mock_post.return_value = mock_response

        prompt = "test prompt"
        executor = "copilot"
        model = "gpt-4o"

        await pipe.execute_run(prompt, executor=executor, model=model)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        payload = kwargs["json"]

        assert payload["executor"] == executor
        assert payload["model"] == model
