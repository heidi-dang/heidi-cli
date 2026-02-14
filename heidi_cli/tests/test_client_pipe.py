import sys
import os
import pytest

# Add the root directory to sys.path to import client.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from client import Pipe

class TestPipe:
    @pytest.fixture
    def pipe(self):
        """Fixture to initialize Pipe with default valves."""
        pipe = Pipe()
        # Ensure consistent defaults for testing
        pipe.valves.DEFAULT_EXECUTOR = "copilot"
        pipe.valves.DEFAULT_MODEL = "gpt-5"
        return pipe

    def test_get_executor_and_model_none(self, pipe):
        """Test with None input."""
        executor, model = pipe._get_executor_and_model(None)
        assert executor == "copilot"
        assert model == "gpt-5"

    def test_get_executor_and_model_copilot(self, pipe):
        """Test with 'copilot/gpt-5'."""
        executor, model = pipe._get_executor_and_model("copilot/gpt-5")
        assert executor == "copilot"
        assert model == "gpt-5"

    def test_get_executor_and_model_opencode(self, pipe):
        """Test with 'opencode/gpt-4o'."""
        executor, model = pipe._get_executor_and_model("opencode/gpt-4o")
        assert executor == "opencode"
        assert model == "gpt-4o"

    def test_get_executor_and_model_ollama(self, pipe):
        """Test with 'ollama/llama3'."""
        executor, model = pipe._get_executor_and_model("ollama/llama3")
        assert executor == "ollama"
        assert model == "llama3"

    def test_get_executor_and_model_jules(self, pipe):
        """Test with 'jules/default'."""
        executor, model = pipe._get_executor_and_model("jules/default")
        assert executor == "jules"
        assert model == "default"

    def test_get_executor_and_model_no_prefix(self, pipe):
        """Test with 'gpt-5' (no prefix)."""
        executor, model = pipe._get_executor_and_model("gpt-5")
        assert executor == "copilot"
        assert model == "gpt-5"

    def test_get_executor_and_model_multiple_slashes(self, pipe):
        """Test with 'copilot/gpt-5/v2'."""
        executor, model = pipe._get_executor_and_model("copilot/gpt-5/v2")
        assert executor == "copilot"
        assert model == "gpt-5/v2"

    def test_get_executor_and_model_unknown_prefix(self, pipe):
        """Test with 'unknown/model'."""
        # Current implementation: falls back to default executor, and model is the full string
        executor, model = pipe._get_executor_and_model("unknown/model")
        assert executor == "copilot"
        assert model == "unknown/model"

    def test_get_executor_and_model_empty_string(self, pipe):
        """Test with empty string."""
        executor, model = pipe._get_executor_and_model("")
        assert executor == "copilot"
        assert model == "gpt-5"
