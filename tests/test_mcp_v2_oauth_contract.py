from __future__ import annotations

import json
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
    assert 'request("PUT", f"/accounts/{account_id}/access/apps/{access_app_id}"' in source
    assert "DEFAULT_MCP_OAUTH_REDIRECT_URIS" not in source
    for forbidden in (
        "chatgpt.com",
        "claude.ai",
        "grok.com",
        "gemini.google.com",
        "mcp.tnaprovider.com.au",
    ):
        assert forbidden not in source


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
    assert "MCP_OAUTH_AUTHORIZATION_SERVER=\n" in env_example
