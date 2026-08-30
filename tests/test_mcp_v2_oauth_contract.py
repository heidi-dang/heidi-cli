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
    for origin in (
        "https://chatgpt.com/connector/oauth/*",
        "https://claude.ai/*",
        "https://grok.com/*",
        "https://gemini.google.com/*",
    ):
        assert origin in source
    assert "--oauth-redirect-uri" in source
    assert 'request("PUT", f"/accounts/{account_id}/access/apps/{access_app_id}"' in source


def test_oauth_resource_metadata_does_not_confuse_access_jwt_issuer_with_authorization_server():
    source = (MCP / "server" / "index.ts").read_text(encoding="utf-8")
    assert "MCP_OAUTH_AUTHORIZATION_SERVER" in source
    assert "MCP_AUTH_MODE" in source
    assert "oauthAuthorizationServer" in source
    assert "authorizationServer: oauthAuthorizationServer" in source


def test_browser_origin_example_is_not_chatgpt_only():
    env_example = (MCP / ".env.example").read_text(encoding="utf-8")
    for origin in ("https://chatgpt.com", "https://claude.ai", "https://grok.com", "https://gemini.google.com"):
        assert origin in env_example
