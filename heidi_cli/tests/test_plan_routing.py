from __future__ import annotations

import pytest
import yaml
from heidi_cli.orchestrator.plan import parse_routing

class TestParseRouting:
    def test_parse_routing_valid(self):
        """Test with valid YAML containing execution_handoffs as a list."""
        yaml_text = """
execution_handoffs:
  - label: "Batch 1"
    agent: "high-autonomy"
    includes_steps: [1, 2]
"""
        result = parse_routing(yaml_text)
        assert "execution_handoffs" in result
        assert isinstance(result["execution_handoffs"], list)
        assert len(result["execution_handoffs"]) == 1
        assert result["execution_handoffs"][0]["label"] == "Batch 1"

    def test_parse_routing_missing_key(self):
        """Test with valid YAML missing the execution_handoffs key."""
        yaml_text = """
some_other_key: "value"
"""
        with pytest.raises(ValueError, match=r"routing YAML must contain execution_handoffs: \[ ... \]"):
            parse_routing(yaml_text)

    def test_parse_routing_invalid_type(self):
        """Test with valid YAML where execution_handoffs is not a list."""
        yaml_text = """
execution_handoffs: "not a list"
"""
        with pytest.raises(ValueError, match=r"routing YAML must contain execution_handoffs: \[ ... \]"):
            parse_routing(yaml_text)

    def test_parse_routing_empty(self):
        """Test with empty string, which results in {}."""
        yaml_text = ""
        with pytest.raises(ValueError, match=r"routing YAML must contain execution_handoffs: \[ ... \]"):
            parse_routing(yaml_text)

    def test_parse_routing_invalid_syntax(self):
        """Test with invalid YAML syntax."""
        yaml_text = """
execution_handoffs:
  - label: "Batch 1"
    agent: "high-autonomy"
    includes_steps: [1, 2
"""  # Missing closing bracket
        with pytest.raises(yaml.YAMLError):
            parse_routing(yaml_text)

    def test_parse_routing_none_input(self):
        """Test that passing None raises TypeError or ValueError."""
        # Depending on yaml implementation, safe_load(None) might return None (-> ValueError)
        # or raise TypeError/AttributeError.
        with pytest.raises((ValueError, AttributeError, TypeError)):
            parse_routing(None)
