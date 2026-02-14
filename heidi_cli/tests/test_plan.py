from __future__ import annotations

import pytest
from heidi_cli.orchestrator.plan import extract_routing, parse_routing

class TestPlan:
    def test_extract_routing_success(self):
        text = """
        Here is my plan:
        BEGIN_EXECUTION_HANDOFFS_YAML
        execution_handoffs:
          - label: "Batch 1"
            agent: "high-autonomy"
            includes_steps: [1, 2]
        END_EXECUTION_HANDOFFS_YAML
        """
        result = extract_routing(text)
        assert "execution_handoffs" in result
        assert "Batch 1" in result

    def test_extract_routing_missing_markers(self):
        with pytest.raises(ValueError, match="Missing routing block"):
            extract_routing("no markers here")

    def test_extract_routing_whitespace_variations(self):
        """Test with various whitespace combinations around markers"""
        # Leading/trailing spaces inside markers
        text = "BEGIN_EXECUTION_HANDOFFS_YAML   \n  content  \n   END_EXECUTION_HANDOFFS_YAML"
        assert extract_routing(text) == "content"

        # Newlines around markers
        text = "\n\nBEGIN_EXECUTION_HANDOFFS_YAML\ncontent\nEND_EXECUTION_HANDOFFS_YAML\n\n"
        assert extract_routing(text) == "content"

        # Tabs
        text = "\tBEGIN_EXECUTION_HANDOFFS_YAML\t\ncontent\n\tEND_EXECUTION_HANDOFFS_YAML"
        assert extract_routing(text) == "content"

    def test_extract_routing_empty_content(self):
        """Test with markers present but no content between them"""
        text = "BEGIN_EXECUTION_HANDOFFS_YAMLEND_EXECUTION_HANDOFFS_YAML"
        assert extract_routing(text) == ""

        text = "BEGIN_EXECUTION_HANDOFFS_YAML   END_EXECUTION_HANDOFFS_YAML"
        assert extract_routing(text) == ""

        text = "BEGIN_EXECUTION_HANDOFFS_YAML\n\nEND_EXECUTION_HANDOFFS_YAML"
        assert extract_routing(text) == ""

    def test_extract_routing_multiline_content(self):
        """Test with content spanning multiple lines"""
        content = "line1\nline2\n  line3"
        text = f"BEGIN_EXECUTION_HANDOFFS_YAML\n{content}\nEND_EXECUTION_HANDOFFS_YAML"
        assert extract_routing(text) == content

    def test_extract_routing_markers_in_wrong_order(self):
        """Test that it fails if END comes before BEGIN"""
        text = "END_EXECUTION_HANDOFFS_YAML content BEGIN_EXECUTION_HANDOFFS_YAML"
        with pytest.raises(ValueError, match="Missing routing block"):
            extract_routing(text)

    def test_extract_routing_partial_markers(self):
        """Test that it fails if markers are incomplete"""
        text = "BEGIN_EXECUTION_HANDOFFS content END_EXECUTION_HANDOFFS_YAML"
        with pytest.raises(ValueError, match="Missing routing block"):
            extract_routing(text)

        text = "BEGIN_EXECUTION_HANDOFFS_YAML content END_EXECUTION_HANDOFFS"
        with pytest.raises(ValueError, match="Missing routing block"):
            extract_routing(text)

    def test_extract_routing_multiple_blocks(self):
        """Test behavior when multiple blocks are present (should find the first)"""
        text = """
        BEGIN_EXECUTION_HANDOFFS_YAML
        block1
        END_EXECUTION_HANDOFFS_YAML

        BEGIN_EXECUTION_HANDOFFS_YAML
        block2
        END_EXECUTION_HANDOFFS_YAML
        """
        assert extract_routing(text) == "block1"

    def test_parse_routing_valid(self):
        yaml_text = """
execution_handoffs:
  - label: "Batch 1"
    agent: "high-autonomy"
    includes_steps: [1, 2]
    verification:
      - "git status"
"""
        result = parse_routing(yaml_text)
        assert "execution_handoffs" in result
        assert len(result["execution_handoffs"]) == 1

    def test_parse_routing_invalid(self):
        with pytest.raises(ValueError, match="routing YAML must contain"):
            parse_routing("invalid: yaml")

    def test_parse_routing_not_list(self):
        yaml_text = """
execution_handoffs: "not a list"
"""
        with pytest.raises(ValueError, match="routing YAML must contain"):
            parse_routing(yaml_text)

    def test_parse_routing_empty_yaml(self):
        with pytest.raises(ValueError, match="routing YAML must contain"):
            parse_routing("")
