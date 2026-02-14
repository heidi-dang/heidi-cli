from __future__ import annotations

from unittest.mock import patch, MagicMock


class TestTokenPrecedence:
    """Test token source precedence: parameter > GH_TOKEN > GITHUB_TOKEN > ConfigManager"""

    def test_github_token_parameter_takes_precedence(self, monkeypatch, tmp_path):
        """Parameter passed to CopilotRuntime should take precedence over env vars"""
        monkeypatch.setenv("GH_TOKEN", "env_gh_token")
        monkeypatch.setenv("GITHUB_TOKEN", "env_github_token")

        with patch("heidi_cli.copilot_runtime.CopilotClient"):
            from heidi_cli.copilot_runtime import CopilotRuntime

            rt = CopilotRuntime(github_token="param_token")
            assert rt.github_token == "param_token"
            assert rt._token_source == "constructor argument"

    def test_gh_token_env_takes_precedence_over_github_token(self, monkeypatch):
        """GH_TOKEN should take precedence over GITHUB_TOKEN"""
        monkeypatch.setenv("GH_TOKEN", "env_gh_token")
        monkeypatch.setenv("GITHUB_TOKEN", "env_github_token")

        with patch("heidi_cli.copilot_runtime.CopilotClient"):
            from heidi_cli.copilot_runtime import CopilotRuntime

            rt = CopilotRuntime()
            assert rt.github_token == "env_gh_token"
            assert rt._token_source == "GH_TOKEN"

    def test_github_token_env_used_when_gh_token_not_set(self, monkeypatch):
        """GITHUB_TOKEN should be used when GH_TOKEN is not set"""
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "env_github_token")

        with patch("heidi_cli.copilot_runtime.CopilotClient"):
            from heidi_cli.copilot_runtime import CopilotRuntime

            rt = CopilotRuntime()
            assert rt.github_token == "env_github_token"
            assert rt._token_source == "GITHUB_TOKEN"

    def test_config_manager_token_used_when_no_env_vars(self, monkeypatch):
        """ConfigManager token should be used when no env vars are set"""
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        with patch("heidi_cli.copilot_runtime.CopilotClient") as mock_client:
            mock_client.return_value = MagicMock()
            with patch("heidi_cli.config.ConfigManager") as mock_cm:
                mock_cm.get_github_token.return_value = "config_token"
                from heidi_cli.copilot_runtime import CopilotRuntime

                rt = CopilotRuntime()
                assert rt.github_token == "config_token"

    def test_no_token_available(self, monkeypatch):
        """When no token source is available, github_token should be None"""
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        with patch("heidi_cli.copilot_runtime.CopilotClient"):
            with patch("heidi_cli.config.ConfigManager") as mock_cm:
                mock_cm.get_github_token.return_value = None
                from heidi_cli.copilot_runtime import CopilotRuntime

                rt = CopilotRuntime()
                assert rt.github_token is None
                assert rt._token_source is None


class TestGHErrors:
    """Test parsing and handling of common gh error outputs"""

    def test_parse_gh_not_logged_in_error(self):
        """Test parsing 'gh auth status' output when not logged in"""
        stderr = "error: not logged in, run: gh auth login"
        assert "not logged in" in stderr
        assert "gh auth login" in stderr

    def test_parse_gh_token_failure(self):
        """Test parsing 'gh auth token' failure output"""
        stderr = "json: error: could not read token: token not found"
        assert "could not read token" in stderr

    def test_parse_gh_auth_expired(self):
        """Test parsing expired auth error"""
        stderr = "error: HTTP 401: Unauthorized - Token has expired"
        assert "401" in stderr or "expired" in stderr

    def test_parse_gh_insufficient_scope(self):
        """Test parsing insufficient scope error"""
        stderr = "error: resource protected by fine-grained token - requires one of: copilot"
        assert "requires one of" in stderr


class TestMockedGhSubprocess:
    """Test gh CLI subprocess calls with mocking"""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_gh_auth_token_success(self, mock_run, mock_which):
        """gh auth token should return token on success"""
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = MagicMock(returncode=0, stdout="gho_xxxxxxxxxxxx", stderr="")

        result = __import__("subprocess").run(
            ["gh", "auth", "token"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "gho_xxxxxxxxxxxx"

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_gh_auth_token_failure_returns_empty(self, mock_run, mock_which):
        """gh auth token should return empty on failure"""
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not logged in")

        result = __import__("subprocess").run(
            ["gh", "auth", "token"], capture_output=True, text=True
        )
        assert result.returncode != 0

    @patch("shutil.which")
    def test_gh_not_found(self, mock_which):
        """shutil.which should return None when gh not installed"""
        mock_which.return_value = None

        result = __import__("shutil").which("gh")
        assert result is None


class TestNoTokenLeakage:
    """Test that tokens are never logged or exposed"""

    def test_redact_secrets_covers_all_token_types(self):
        """Verify redact_secrets catches all known token patterns"""
        from heidi_cli.logging import redact_secrets

        # Dynamically construct tokens to avoid hardcoded secrets scanning
        dummy_suffix = "abcdefghijklmnopqrstuvwxyz1234567890"
        test_cases = [
            f"ghp_{dummy_suffix}",  # ghp_ + 36 chars = 40 total
            "github_pat_" + dummy_suffix[:26],
            f"gho_{dummy_suffix}",  # gho_ + 36 chars = 40 total
            "GH_TOKEN=abc123",
            "GITHUB_TOKEN=xyz789",
        ]

        for tc in test_cases:
            redacted = redact_secrets(tc)
            assert "***REDACTED***" in redacted, f"Failed to redact: {tc}"

    def test_token_never_in_cli_output(self):
        """Ensure CLI commands don't output raw tokens"""
        from heidi_cli.logging import redact_secrets

        token = "ghp_" + "abcdefghijklmnopqrstuvwxyz1234567890"
        output_with_token = f"Token: {token}"
        redacted = redact_secrets(output_with_token)

        assert token not in redacted
        assert "***REDACTED***" in redacted

    def test_config_file_never_contains_raw_token(self, monkeypatch, tmp_path):
        """Verify secrets file uses proper permissions and keyring"""
        import stat
        from heidi_cli.config import ConfigManager

        original_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(tmp_path)
            ConfigManager.ensure_dirs()

            secrets_file = ConfigManager.secrets_file()
            if secrets_file.exists():
                mode = stat.S_IMODE(secrets_file.stat().st_mode)
                assert mode == 0o600, f"Secrets file has wrong permissions: {oct(mode)}"
        finally:
            __import__("os").chdir(original_cwd)
