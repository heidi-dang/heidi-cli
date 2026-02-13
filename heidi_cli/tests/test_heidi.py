from __future__ import annotations

import pytest
from pathlib import Path
from heidi_cli.orchestrator.plan import extract_routing, parse_routing
from heidi_cli.logging import redact_secrets
from heidi_cli.orchestrator.workspace import WorkspaceManager, PatchApplicator, VerificationRunner


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


class TestRedaction:
    def test_redact_github_token(self):
        text = "Token: ghp_abcdefghijklmnopqrstuvwxyz1234567890"
        assert redact_secrets(text) == "Token: ***REDACTED***"

    def test_redact_github_pat(self):
        text = "Token: github_pat_abcdefghijklmnopqrstuvwxyz"
        assert redact_secrets(text) == "Token: ***REDACTED***"

    def test_redact_env_vars(self):
        text = "GH_TOKEN=abc123 COPILOT_GITHUB_TOKEN=xyz789"
        redacted = redact_secrets(text)
        assert "abc123" not in redacted
        assert "xyz789" not in redacted

    def test_redact_copilot_token(self):
        text = "COPILOT_TOKEN=sk-abc123"
        redacted = redact_secrets(text)
        assert "sk-abc123" not in redacted

    def test_redact_github_token_env(self):
        text = "GITHUB_TOKEN=gho_abc123"
        redacted = redact_secrets(text)
        assert "gho_abc123" not in redacted

    def test_redact_openai_key(self):
        text = "OPENAI_API_KEY=sk-abc123"
        redacted = redact_secrets(text)
        assert "sk-abc123" not in redacted

    def test_redact_anthropic_key(self):
        text = "ANTHROPIC_API_KEY=sk-ant-abc123"
        redacted = redact_secrets(text)
        assert "sk-ant-abc123" not in redacted

    def test_redact_json_token(self):
        text = '{"token": "ghp_abcdefghijklmnopqrstuvwxyz1234567890"}'
        redacted = redact_secrets(text)
        assert "ghp_" not in redacted

    def test_no_redaction_needed(self):
        text = "This is normal text without secrets"
        assert redact_secrets(text) == text


class TestWorkspace:
    def test_patch_applier_is_safe_diff(self):
        dangerous = "rm -rf /etc/passwd"
        assert not PatchApplicator.is_safe_diff(dangerous)

    def test_patch_applier_safe_diff(self):
        safe = "def hello():\n    return 'world'"
        assert PatchApplicator.is_safe_diff(safe)
