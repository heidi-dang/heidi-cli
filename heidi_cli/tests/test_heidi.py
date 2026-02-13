from __future__ import annotations

import pytest
from pathlib import Path
from heidi_cli.orchestrator.plan import extract_routing, parse_routing
from heidi_cli.logging import redact_secrets
from heidi_cli.orchestrator.workspace import PatchApplicator


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


class TestArtifacts:
    def test_tasks_dir_is_repo_root(self):
        from heidi_cli.config import ConfigManager
        tasks_dir = ConfigManager.TASKS_DIR
        assert tasks_dir == Path("./tasks")

    def test_heidi_dir_is_project_local(self):
        import os
        from heidi_cli.config import ConfigManager
        original_cwd = os.getcwd()
        try:
            os.chdir("/tmp")
            heidi_dir = ConfigManager.heidi_dir()
            assert str(heidi_dir).startswith("/tmp")
        finally:
            os.chdir(original_cwd)

    def test_artifact_redaction_on_save(self, tmp_path):
        import os
        from heidi_cli.orchestrator.artifacts import TaskArtifact

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            (tmp_path / "tasks").mkdir()

            artifact = TaskArtifact(
                slug="test-task",
                content="Token: ghp_abcdefghijklmnopqrstuvwxyz1234567890\nHello world",
                audit_content="COPILOT_TOKEN=sk-test123\nAudit result: pass"
            )
            artifact.save()

            task_file = tmp_path / "tasks" / "test-task.md"
            audit_file = tmp_path / "tasks" / "test-task.audit.md"

            assert task_file.exists()
            assert audit_file.exists()

            task_content = task_file.read_text()
            audit_content = audit_file.read_text()

            assert "ghp_" not in task_content
            assert "***REDACTED***" in task_content
            assert "sk-test123" not in audit_content
            assert "***REDACTED***" in audit_content
        finally:
            os.chdir(original_cwd)

    def test_artifact_all_secret_patterns_redacted(self, tmp_path):
        import os
        from heidi_cli.orchestrator.artifacts import TaskArtifact

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            (tmp_path / "tasks").mkdir()

            secret_patterns = [
                "ghp_abcdefghijklmnopqrstuvwxyz1234567890",
                "github_pat_abcdefghijklmnopqrstuvwxyz",
                "GH_TOKEN=abc123",
                "COPILOT_TOKEN=xyz789",
                "GITHUB_TOKEN=token123",
                "OPENAI_API_KEY=sk-abc",
                "ANTHROPIC_API_KEY=sk-ant-abc",
            ]

            artifact = TaskArtifact(
                slug="test-all-patterns",
                content="\n".join(secret_patterns),
                audit_content="\n".join(secret_patterns)
            )
            artifact.save()

            task_file = tmp_path / "tasks" / "test-all-patterns.md"
            audit_file = tmp_path / "tasks" / "test-all-patterns.audit.md"

            task_content = task_file.read_text()
            audit_content = audit_file.read_text()

            for pattern in secret_patterns:
                assert pattern not in task_content, f"Pattern {pattern} not redacted in task"
                assert pattern not in audit_content, f"Pattern {pattern} not redacted in audit"

            assert "***REDACTED***" in task_content
            assert "***REDACTED***" in audit_content
        finally:
            os.chdir(original_cwd)

    def test_artifact_files_exist_at_correct_paths(self, tmp_path):
        import os
        from heidi_cli.orchestrator.artifacts import TaskArtifact, sanitize_slug

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            (tmp_path / "tasks").mkdir()

            task_text = "create a hello world python file"
            slug = sanitize_slug(task_text)

            artifact = TaskArtifact(
                slug=slug,
                content="# Task content",
                audit_content="# Audit content"
            )
            artifact.save()

            task_file = tmp_path / "tasks" / f"{slug}.md"
            audit_file = tmp_path / "tasks" / f"{slug}.audit.md"
            meta_file = tmp_path / "tasks" / f"{slug}.meta.json"

            assert task_file.exists(), f"Expected {task_file} to exist"
            assert audit_file.exists(), f"Expected {audit_file} to exist"
            assert meta_file.exists(), f"Expected {meta_file} to exist"
        finally:
            os.chdir(original_cwd)
