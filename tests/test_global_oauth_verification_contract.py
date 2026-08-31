from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_ci_syntax_and_executable_contracts_include_managed_oauth_helper():
    ci = read(".github/workflows/ci.yml")
    assert "scripts/managed-oauth-client.py" in ci
    assert "py_compile" in ci
    assert "Executable contracts" in ci


def test_stack_verifier_validates_reusable_oauth_credentials_without_exposing_secret():
    verifier = read("scripts/verify-stack.sh")

    assert "check_reusable_oauth_client" in verifier
    assert "HEIDI_MCP_OAUTH_CLIENT_FILE" in verifier
    assert "HEIDI_MCP_OAUTH_CLIENT_ID" in verifier
    assert "client_secret" in verifier
    assert "owner-only" in verifier
    assert "MCP_OAUTH_ALLOWED_EMAIL" in verifier
    assert "CLOUDFLARE_ACCESS_ISSUER" in verifier

    # The verifier may assert that client_secret exists, but it must never print it.
    assert 'print(data["client_secret"])' not in verifier
    assert "printf 'Reusable OAuth client secret" not in verifier


def test_operator_docs_cover_reuse_rotation_dcr_and_secret_storage():
    docs = "\n".join(
        [
            read("README.md"),
            read("docs/SECURITY.md"),
            read("docs/DEPLOYMENT.md"),
        ]
    )

    assert "oauth-client.json" in docs
    assert "HEIDI_MCP_OAUTH_GLOBAL_CLIENT" in docs
    assert "HEIDI_MCP_OAUTH_GLOBAL_CLIENT_ROTATE" in docs
    assert "Dynamic Client Registration" in docs or "DCR" in docs
    assert "client_id" in docs
    assert "client_secret" in docs
    assert "0600" in docs
    assert "state.env" in docs
    assert "mcp.env" in docs
