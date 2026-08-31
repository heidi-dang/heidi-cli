from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP = ROOT / "apps" / "mcp"


def test_mcp_uses_v2_split_sdk_and_zod4():
    package = json.loads((MCP / "package.json").read_text(encoding="utf-8"))
    deps = package["dependencies"]
    dev = package["devDependencies"]
    assert "@modelcontextprotocol/sdk" not in deps
    assert deps["@modelcontextprotocol/server"].startswith("^2.")
    assert deps["@modelcontextprotocol/node"].startswith("^2.")
    assert dev["@modelcontextprotocol/client"].startswith("^2.")
    assert deps["zod"].startswith("^4.")


def test_gateway_routes_modern_and_legacy_protocol_eras_on_one_mcp_url():
    source = (MCP / "server" / "index.ts").read_text(encoding="utf-8")
    assert "createMcpHandler" in source
    assert "isLegacyRequest" in source
    assert "NodeStreamableHTTPServerTransport" in source
    assert "toNodeHandler" in source
    assert "toWebRequest" in source
    assert 'legacy: "reject"' in source
    assert "@modelcontextprotocol/sdk" not in source


def test_managed_oauth_is_host_neutral_and_updates_existing_access_apps():
    source = (ROOT / "scripts" / "cloudflare-provision.py").read_text(encoding="utf-8")
    assert "--oauth-redirect-uri" in source
    assert "MCP_OAUTH_REDIRECT_URIS" in source
    assert re.search(
        r'request\(\s*"PUT"\s*,\s*f"/accounts/\{account_id\}/access/apps/\{access_app_id\}"',
        source,
    )
    assert "DEFAULT_MCP_OAUTH_REDIRECT_URIS" not in source
    for forbidden in (
        "chatgpt.com",
        "claude.ai",
        "grok.com",
        "gemini.google.com",
        "mcp.tnaprovider.com.au",
    ):
        assert forbidden not in source


def test_public_installer_enables_claude_dcr_callback_without_polluting_generic_provisioner():
    installer = (ROOT / "scripts" / "install-core.sh").read_text(encoding="utf-8")
    provisioner = (ROOT / "scripts" / "cloudflare-provision.py").read_text(encoding="utf-8")
    callback = "https://claude.ai/api/mcp/auth_callback"

    assert f'CLAUDE_MCP_OAUTH_REDIRECT_URI="{callback}"' in installer
    assert "OAUTH_DCR_ALLOWED_REDIRECT_URIS" in installer
    assert 'CF_ARGS+=(--oauth-redirect-uri "$oauth_redirect_uri")' in installer
    assert callback not in provisioner


def test_oauth_resource_metadata_does_not_confuse_access_jwt_issuer_with_authorization_server():
    source = (MCP / "server" / "index.ts").read_text(encoding="utf-8")
    assert "MCP_OAUTH_AUTHORIZATION_SERVER" in source
    assert "MCP_AUTH_MODE" in source
    assert "oauthAuthorizationServer" in source
    assert "authorizationServer: oauthAuthorizationServer" in source
    assert "mcp.tnaprovider.com.au" not in source


def test_environment_example_contains_no_environment_or_provider_host_defaults():
    env_example = (MCP / ".env.example").read_text(encoding="utf-8")
    for forbidden in (
        "chatgpt.com",
        "claude.ai",
        "grok.com",
        "gemini.google.com",
        "mcp.tnaprovider.com.au",
        "owner@example.com",
    ):
        assert forbidden not in env_example
    assert "PUBLIC_ORIGIN=\n" in env_example
    assert "MCP_ALLOWED_ORIGINS=\n" in env_example
    assert "# MCP_AUTH_MODE=cloudflare-managed-oauth" in env_example
    assert "# MCP_OAUTH_AUTHORIZATION_SERVER=" in env_example
    assert "# MCP_OAUTH_RESOURCE=" in env_example
    assert "\nHOST=\n" not in env_example
    assert "\nPORT=\n" not in env_example
