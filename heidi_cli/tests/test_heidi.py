from __future__ import annotations

import pytest
from heidi_cli.logging import redact_secrets
from heidi_cli.orchestrator.workspace import PatchApplicator


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
    def test_tasks_dir_is_in_project_root(self):
        from heidi_cli.config import ConfigManager

        tasks_dir = ConfigManager.tasks_dir()
        assert tasks_dir.name == "tasks"
        assert tasks_dir.parent == ConfigManager.project_root()

    def test_heidi_dir_is_global_config(self):
        import os
        from heidi_cli.config import ConfigManager, heidi_config_dir

        original_cwd = os.getcwd()
        try:
            os.chdir("/tmp")
            heidi_dir = ConfigManager.heidi_dir()
            expected = heidi_config_dir()
            assert heidi_dir == expected
        finally:
            os.chdir(original_cwd)

    def test_config_dir_is_global_not_cwd(self, tmp_path):
        import os
        from heidi_cli.config import ConfigManager, heidi_config_dir

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            config_dir = ConfigManager.config_dir()
            expected = heidi_config_dir()
            assert config_dir == expected
            assert not str(config_dir).startswith(str(tmp_path))
        finally:
            os.chdir(original_cwd)

    def test_secrets_file_permissions_0600(self, tmp_path):
        import os
        import stat
        from heidi_cli.config import ConfigManager

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            ConfigManager.ensure_dirs()
            secrets_file = ConfigManager.secrets_file()
            if secrets_file.exists():
                mode = stat.S_IMODE(secrets_file.stat().st_mode)
                assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"
        finally:
            os.chdir(original_cwd)

    def test_legacy_heidi_detection(self, tmp_path):
        import os
        from heidi_cli.config import check_legacy_heidi_dir

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            legacy = check_legacy_heidi_dir()
            assert legacy is None
            (tmp_path / ".heidi").mkdir()
            legacy = check_legacy_heidi_dir()
            assert legacy is not None
            assert legacy.name == ".heidi"
        finally:
            os.chdir(original_cwd)

    def test_project_root_detection_git(self, tmp_path):
        import os
        from heidi_cli.config import find_project_root

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = find_project_root()
            assert result == tmp_path
            (tmp_path / ".git").mkdir()
            result = find_project_root()
            assert result == tmp_path
        finally:
            os.chdir(original_cwd)

    def test_project_root_detection_cwd_fallback(self, tmp_path):
        import os
        from heidi_cli.config import find_project_root

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = find_project_root()
            assert result == tmp_path
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
                audit_content="COPILOT_TOKEN=sk-test123\nAudit result: pass",
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
                audit_content="\n".join(secret_patterns),
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
                slug=slug, content="# Task content", audit_content="# Audit content"
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
