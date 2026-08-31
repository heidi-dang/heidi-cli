from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_public_installer_wires_reusable_managed_oauth_client_as_additive_to_dcr():
    source = read("scripts/install-core.sh")

    assert "managed-oauth-client.py" in source
    assert "HEIDI_MCP_OAUTH_GLOBAL_CLIENT" in source
    assert "HEIDI_MCP_OAUTH_GLOBAL_CLIENT_ROTATE" in source
    assert 'MCP_OAUTH_CLIENT_FILE="$CONFIG_DIR/oauth-client.json"' in source
    assert 'HEIDI_MCP_OAUTH_CLIENT_ID' in source
    assert 'HEIDI_MCP_OAUTH_CLIENT_FILE' in source

    # DCR remains configured through the existing Cloudflare Access path.
    assert "--oauth-redirect-uri" in source
    assert 'CLAUDE_MCP_OAUTH_REDIRECT_URI="https://claude.ai/api/mcp/auth_callback"' in source
    assert "MCP_OAUTH_REDIRECT_URIS" in source


def test_global_client_and_cloudflare_dcr_use_the_same_normalized_redirect_allowlist():
    source = read("scripts/install-core.sh")

    assert "OAUTH_ALLOWED_REDIRECT_URIS" in source
    assert 'for oauth_redirect_uri in "${OAUTH_ALLOWED_REDIRECT_URIS[@]}"' in source
    assert 'CF_ARGS+=(--oauth-redirect-uri "$oauth_redirect_uri")' in source
    assert 'GLOBAL_OAUTH_ARGS+=(--redirect-uri "$oauth_redirect_uri")' in source


def test_oauth_client_secret_is_not_written_to_state_or_mcp_runtime_environment():
    source = read("scripts/install-core.sh")

    mcp_env_block = source.split('>"$MCP_ENV_FILE"', 1)[0].rsplit(
        'if [[ "$INCLUDES_MCP" == 1 ]]', 1
    )[-1]
    state_block = source.split('>"$STATE_FILE"', 1)[0].rsplit("{", 1)[-1]

    assert "CLIENT_SECRET" not in mcp_env_block
    assert "CLIENT_SECRET" not in state_block
    assert 'env_line HEIDI_MCP_OAUTH_CLIENT_ID "$MCP_OAUTH_CLIENT_ID"' in state_block
    assert 'env_line HEIDI_MCP_OAUTH_CLIENT_FILE "$MCP_OAUTH_CLIENT_STATE_FILE"' in state_block


def test_reusable_global_client_uses_cloudflare_authorization_server_and_origin_resource():
    source = read("scripts/install-core.sh")

    assert 'GLOBAL_OAUTH_METADATA_URL="${CF_ACCESS_AUTH_DOMAIN%/}/.well-known/oauth-authorization-server"' in source
    assert '--metadata-url "$GLOBAL_OAUTH_METADATA_URL"' in source
    assert '--resource "$PUBLIC_ORIGIN"' in source
    assert '--resource "$MCP_URL"' not in source
    assert '--token-endpoint-auth-method client_secret_post' in source
