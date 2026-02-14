import sys
import os
from unittest.mock import patch
import pytest

# Ensure client.py can be imported
sys.path.append(os.getcwd())

from client import Pipe

class TestClient:
    @patch('client.Pipe._fetch_agents')
    def test_list_agents(self, mock_fetch_agents):
        # Arrange
        mock_agents = [
            ("Agent1", "Description of Agent1"),
            ("Agent2", "Description of Agent2")
        ]
        mock_fetch_agents.return_value = mock_agents

        pipe = Pipe()

        # Act
        output = pipe.list_agents()

        # Assert
        assert "### 🤖 Available Agents" in output
        assert "| Agent | Description |" in output
        assert "|-------|-------------|" in output
        assert "| **Agent1** | Description of Agent1 |" in output
        assert "| **Agent2** | Description of Agent2 |" in output

    @patch('client.Pipe._fetch_agents')
    def test_list_agents_empty(self, mock_fetch_agents):
        # Arrange
        mock_fetch_agents.return_value = []

        pipe = Pipe()

        # Act
        output = pipe.list_agents()

        # Assert
        assert "### 🤖 Available Agents" in output
        assert "| Agent | Description |" in output
        assert "|-------|-------------|" in output
        assert "| **" not in output

    @patch('client.Pipe._fetch_agents')
    def test_list_agents_error(self, mock_fetch_agents):
        # Arrange
        mock_fetch_agents.side_effect = Exception("Fetch error")

        pipe = Pipe()

        # Act & Assert
        with pytest.raises(Exception, match="Fetch error"):
            pipe.list_agents()
