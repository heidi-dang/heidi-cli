import sys
import os
import time
from unittest.mock import MagicMock, patch
import pytest

# Ensure root directory is in sys.path if not already
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from client import Pipe, COPILOT_MODELS
except ImportError:
    # If not found via sys.path hack, assume PYTHONPATH is set correctly
    from client import Pipe, COPILOT_MODELS

class TestClientPipe:

    @pytest.fixture
    def pipe(self):
        return Pipe()

    def test_fetch_models_cache_hit(self, pipe):
        """Test that cached models are returned if valid."""
        # Setup cache
        pipe._models_cache = ["cached-model"]
        pipe._models_cache_time = time.time()

        # Verify cache hit without network request
        with patch('client.requests.get') as mock_get:
            models = pipe._fetch_models()
            assert models == ["cached-model"]
            mock_get.assert_not_called()

    def test_fetch_models_server_success(self, pipe):
        """Test fetching models from server successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "server-model"}, {"name": "another-model"}]

        with patch('client.requests.get', return_value=mock_response) as mock_get:
            pipe._models_cache = None
            models = pipe._fetch_models()

            assert "server-model" in models
            assert "another-model" in models
            mock_get.assert_called_once()
            # Verify cache update
            assert pipe._models_cache == models

    def test_fetch_models_server_failure_returns_fallback(self, pipe):
        """Test that server failure returns default models."""
        with patch('client.requests.get', side_effect=Exception("Connection error")):
            models = pipe._fetch_models()
            assert models == COPILOT_MODELS

    def test_fetch_models_cache_expiration(self, pipe):
        """Test that expired cache triggers a new request."""
        pipe._models_cache = ["old-model"]
        # Set cache time to be older than 300 seconds
        pipe._models_cache_time = time.time() - 301

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "new-model"}]

        with patch('client.requests.get', return_value=mock_response) as mock_get:
            models = pipe._fetch_models()
            assert models == ["new-model"]
            mock_get.assert_called_once()

    def test_fetch_models_handles_malformed_response(self, pipe):
        """Test that malformed JSON response returns default models."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Return dict instead of list
        mock_response.json.return_value = {"not": "a list"}

        with patch('client.requests.get', return_value=mock_response):
            models = pipe._fetch_models()
            assert models == COPILOT_MODELS

    def test_fetch_models_handles_empty_model_names(self, pipe):
        """Test that empty model names are filtered out."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": ""}, {"name": None}, {"id": "valid-model"}]

        with patch('client.requests.get', return_value=mock_response):
            models = pipe._fetch_models()
            assert models == ["valid-model"]

    def test_fetch_models_http_error(self, pipe):
        """Test that HTTP error returns default models."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('client.requests.get', return_value=mock_response):
            models = pipe._fetch_models()
            # If status code is not 200, it falls through to return COPILOT_MODELS
            assert models == COPILOT_MODELS
