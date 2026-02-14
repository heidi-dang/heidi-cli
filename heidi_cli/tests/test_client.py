import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import requests

# Ensure we can import client.py from the root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from client import Pipe

class TestClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.pipe = Pipe()
        # Set default valve values for testing
        self.pipe.valves.HEIDI_SERVER_URL = "http://testserver"
        self.pipe.valves.DEFAULT_EXECUTOR = "test_executor"
        self.pipe.valves.DEFAULT_MODEL = "test_model"
        self.pipe.valves.REQUEST_TIMEOUT = 10

    @patch('client.requests.post')
    async def test_execute_loop_success(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "run_id": "run_123",
            "status": "completed",
            "result": "Success Result",
            "error": ""
        }
        mock_post.return_value = mock_response

        task = "Test Task"
        executor = "custom_executor"
        model = "custom_model"

        # Act
        result = await self.pipe.execute_loop(task, executor, model)

        # Assert
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://testserver/loop")
        expected_payload = {
            "task": task,
            "executor": executor,
            "max_retries": self.pipe.valves.MAX_RETRIES,
            # "model": None # model is None if executor != copilot, and filtered out
        }
        self.assertEqual(kwargs['json'], expected_payload)

        self.assertIn("Agent Loop Started", result)
        self.assertIn("**Run ID:** run_123", result)
        self.assertIn("**Result:** Success Result", result)

    @patch('client.requests.post')
    async def test_execute_loop_success_copilot(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "run_id": "run_123",
            "status": "completed",
            "result": "Success Result",
            "error": ""
        }
        mock_post.return_value = mock_response

        task = "Test Task"
        executor = "copilot"
        model = "custom_model"

        # Act
        result = await self.pipe.execute_loop(task, executor, model)

        # Assert
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['model'], model)


    @patch('client.requests.post')
    async def test_execute_loop_failed_status(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "run_id": "run_456",
            "status": "failed",
            "result": "",
            "error": "Some error occurred"
        }
        mock_post.return_value = mock_response

        task = "Test Task"

        # Act
        result = await self.pipe.execute_loop(task)

        # Assert
        self.assertIn("Agent Loop Started", result)
        self.assertIn("**Status:** failed", result)
        self.assertIn("**Error:** Some error occurred", result)

    @patch('client.requests.post')
    async def test_execute_loop_connection_error(self, mock_post):
        # Arrange
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        # Act
        result = await self.pipe.execute_loop("Test Task")

        # Assert
        self.assertIn("Connection Error", result)
        self.assertIn("Could not connect to Heidi server", result)

    @patch('client.requests.post')
    async def test_execute_loop_timeout(self, mock_post):
        # Arrange
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        # Act
        result = await self.pipe.execute_loop("Test Task")

        # Assert
        self.assertIn("Timeout Error", result)
        self.assertIn("Request timed out", result)

    @patch('client.requests.post')
    async def test_execute_loop_auth_error(self, mock_post):
        # Arrange
        error = requests.exceptions.HTTPError("401 Unauthorized")
        error.response = MagicMock()
        error.response.status_code = 401
        mock_post.side_effect = error

        # Act
        result = await self.pipe.execute_loop("Test Task")

        # Assert
        self.assertIn("Authentication Error", result)
        self.assertIn("401 Unauthorized", result)

    @patch('client.requests.post')
    async def test_execute_loop_http_error(self, mock_post):
        # Arrange
        error = requests.exceptions.HTTPError("500 Internal Server Error")
        error.response = MagicMock()
        error.response.status_code = 500
        mock_post.side_effect = error

        # Act
        result = await self.pipe.execute_loop("Test Task")

        # Assert
        self.assertIn("HTTP Error", result)
        self.assertIn("500 Internal Server Error", result)

    @patch('client.requests.post')
    async def test_execute_loop_generic_exception(self, mock_post):
        # Arrange
        mock_post.side_effect = Exception("Generic failure")

        # Act
        result = await self.pipe.execute_loop("Test Task")

        # Assert
        self.assertIn("Heidi Loop Error", result)
        self.assertIn("Generic failure", result)

if __name__ == '__main__':
    unittest.main()
