#!/usr/bin/env python3
"""One-shot PR95 migration helper for MCP SDK v2 + universal Managed OAuth.

This is intentionally fail-closed: exact source blocks must match before any
architectural routing replacement is applied. It is removed after the branch
has been migrated and verified.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP = ROOT / "apps" / "mcp"


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"{label} changed; refusing blind migration")
    return text.replace(old, new, 1)


def migrate_package() -> None:
    path = MCP / "package.json"
    package = json.loads(path.read_text(encoding="utf-8"))
    deps = package["dependencies"]
    deps.pop("@modelcontextprotocol/sdk", None)
    deps["@modelcontextprotocol/server"] = "^2.0.0"
    deps["@modelcontextprotocol/node"] = "^2.0.0"
    deps["zod"] = "^4.2.0"
    package["devDependencies"]["@modelcontextprotocol/client"] = "^2.0.0"
    path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")


def migrate_imports() -> None:
    replacements = {
        "@modelcontextprotocol/sdk/server/mcp.js": "@modelcontextprotocol/server",
        "@modelcontextprotocol/sdk/client/index.js": "@modelcontextprotocol/client",
        "@modelcontextprotocol/sdk/inMemory.js": "@modelcontextprotocol/server",
        "@modelcontextprotocol/sdk/server/streamableHttp.js": "@modelcontextprotocol/node",
        "@modelcontextprotocol/sdk/types.js": "@modelcontextprotocol/server",
    }
    for path in MCP.rglob("*.ts"):
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def migrate_gateway() -> None:
    path = MCP / "server" / "index.ts"
    text = path.read_text(encoding="utf-8")
    text = replace_required(
        text,
        'import { StreamableHTTPServerTransport } from "@modelcontextprotocol/node";\n'
        'import { isInitializeRequest } from "@modelcontextprotocol/server";',
        'import { NodeStreamableHTTPServerTransport, toNodeHandler, toWebRequest } from "@modelcontextprotocol/node";\n'
        'import { createMcpHandler, isInitializeRequest, isLegacyRequest } from "@modelcontextprotocol/server";',
        "MCP v2 server imports",
    )
    text = text.replace("StreamableHTTPServerTransport", "NodeStreamableHTTPServerTransport")
    text = text.replace("NodeNodeStreamableHTTPServerTransport", "NodeStreamableHTTPServerTransport")

    issuer_anchor = 'const oauthIssuer = process.env.CLOUDFLARE_ACCESS_ISSUER;\n'
    if "MCP_OAUTH_AUTHORIZATION_SERVER" not in text:
        text = replace_required(
            text,
            issuer_anchor,
            issuer_anchor
            + 'const authMode = process.env.MCP_AUTH_MODE ??\n'
            + '  (oauthIssuer ? "cloudflare-managed-oauth" : mcpAccessToken ? "static-token" : "unconfigured");\n'
            + 'const oauthAuthorizationServer = process.env.MCP_OAUTH_AUTHORIZATION_SERVER ??\n'
            + '  (authMode === "cloudflare-managed-oauth" ? publicOrigin : oauthIssuer);\n',
            "OAuth issuer anchor",
        )

    modern_anchor = "async function handleStatefulInitialize(\n"
    if "const modernMcpHandler =" not in text:
        text = replace_required(
            text,
            modern_anchor,
            'const modernMcpHandler = createMcpHandler(() => createSessionServer(), { legacy: "reject" });\n'
            'const modernNodeHandler = toNodeHandler(modernMcpHandler);\n\n'
            + modern_anchor,
            "legacy initialize handler anchor",
        )

    text = text.replace(
        '"Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Mcp-Session-Id, MCP-Protocol-Version",',
        '"Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Mcp-Session-Id, MCP-Protocol-Version, Mcp-Method, Mcp-Name, Last-Event-Id",',
    )
    text = replace_required(
        text,
        'res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept, Mcp-Session-Id, MCP-Protocol-Version");\n'
        '  res.setHeader("Access-Control-Expose-Headers", "Mcp-Session-Id");',
        'res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept, Mcp-Session-Id, MCP-Protocol-Version, Mcp-Method, Mcp-Name, Last-Event-Id");\n'
        '  res.setHeader("Access-Control-Expose-Headers", "Mcp-Session-Id, MCP-Protocol-Version, WWW-Authenticate, Last-Event-Id");',
        "MCP CORS response headers",
    )

    old_metadata = '''  if (url.pathname === "/.well-known/oauth-protected-resource" && req.method === "GET") {
    if (!oauthIssuer) {
      writeJson(res, 404, { error: "OAuth is not configured" });
      return;
    }
    writeJson(res, 200, createProtectedResourceMetadata({
      resource: oauthResource,
      authorizationServer: oauthIssuer,
      scopes: oauthScopes,
    }));
    return;
  }'''
    new_metadata = '''  if (url.pathname === "/.well-known/oauth-protected-resource" && req.method === "GET") {
    if (!oauthAuthorizationServer) {
      writeJson(res, 404, { error: "OAuth is not configured" });
      return;
    }
    writeJson(res, 200, createProtectedResourceMetadata({
      resource: oauthResource,
      authorizationServer: oauthAuthorizationServer,
      scopes: oauthScopes,
    }));
    return;
  }'''
    text = replace_required(text, old_metadata, new_metadata, "protected-resource metadata")

    old_post = '''    if (req.method === "POST") {
      const body = await readJsonBody(req);
      if (isInitializeRequest(body)) {
        await handleStatefulInitialize(req, res, body, identity);
        return;
      }
      // Migration compatibility for a ChatGPT connection created before the
      // current contract. After connector metadata Refresh, initialize-capable
      // clients receive an Mcp-Session-Id and all prompt activity stays scoped.
      res.setHeader("X-CPTR-Contract-Refresh", `required-v${CPTR_APP_VERSION}`);
      await handleStatelessCompatibilityRequest(req, res, body);
      return;
    }'''
    new_post = '''    if (req.method === "POST") {
      const body = await readJsonBody(req);
      const probe = await toWebRequest(req, body);
      if (!(await isLegacyRequest(probe))) {
        await modernNodeHandler(req, res, body);
        return;
      }
      if (isInitializeRequest(body)) {
        await handleStatefulInitialize(req, res, body, identity);
        return;
      }
      // Migration compatibility for clients connected before the 2026-07-28
      // protocol. Legacy sessionful traffic stays isolated while modern clients
      // use request-scoped Streamable HTTP on this same /mcp endpoint.
      res.setHeader("X-CPTR-Contract-Refresh", `required-v${CPTR_APP_VERSION}`);
      await handleStatelessCompatibilityRequest(req, res, body);
      return;
    }'''
    text = replace_required(text, old_post, new_post, "legacy/modern POST router")

    text = text.replace(
        'session_mode: "stateful-with-stateless-migration-fallback",\n        active_sessions: mcpSessions.size,',
        'protocol_revision: "2026-07-28",\n        modern_transport: "request-scoped-streamable-http",\n        legacy_session_mode: "stateful-with-stateless-migration-fallback",\n        active_legacy_sessions: mcpSessions.size,',
    )
    text = replace_required(
        text,
        '  await Promise.all([...mcpSessions.keys()].map((sessionId) => closeMcpSession(sessionId)));\n  httpServer.close();',
        '  await Promise.all([...mcpSessions.keys()].map((sessionId) => closeMcpSession(sessionId)));\n'
        '  await modernMcpHandler.close().catch(() => undefined);\n'
        '  httpServer.close();',
        "MCP shutdown",
    )
    if "@modelcontextprotocol/sdk" in text:
        raise RuntimeError("legacy @modelcontextprotocol/sdk import remains in index.ts")
    path.write_text(text, encoding="utf-8")


def migrate_v2_schema_shapes() -> None:
    path = MCP / "server" / "mcp.ts"
    text = path.read_text(encoding="utf-8")
    old = '''      outputSchema: {
        target_type: z.enum(["task", "monitor", "command"]),
        target_id: z.string(),
        status: z.string(),
        workspace_id: z.string().optional(),
        review_status: z.string().optional(),
        title: z.string(),
        initial_summary: z.string(),
        recent_events: z.array(z.record(z.string(), z.unknown())),
      },'''
    new = '''      outputSchema: z.object({
        target_type: z.enum(["task", "monitor", "command"]),
        target_id: z.string(),
        status: z.string(),
        workspace_id: z.string().optional(),
        review_status: z.string().optional(),
        title: z.string(),
        initial_summary: z.string(),
        recent_events: z.array(z.record(z.string(), z.unknown())),
      }),'''
    text = replace_required(text, old, new, "SDK v2 render-live-terminal output schema")
    path.write_text(text, encoding="utf-8")


def migrate_cloudflare() -> None:
    path = ROOT / "scripts" / "cloudflare-provision.py"
    text = path.read_text(encoding="utf-8")
    api_anchor = 'API = os.environ.get("HEIDI_CLOUDFLARE_API_BASE", "https://api.cloudflare.com/client/v4").rstrip("/")\n'
    if "DEFAULT_MCP_OAUTH_REDIRECT_URIS" not in text:
        text = replace_required(
            text,
            api_anchor,
            api_anchor
            + '''\nDEFAULT_MCP_OAUTH_REDIRECT_URIS = (
    "https://chatgpt.com/connector/oauth/*",
    "https://claude.ai/*",
    "https://grok.com/*",
    "https://gemini.google.com/*",
)\n''',
            "Cloudflare API anchor",
        )

    arg_anchor = '    parser.add_argument("--access-app-id")\n'
    if "--oauth-redirect-uri" not in text:
        text = replace_required(
            text,
            arg_anchor,
            arg_anchor
            + '    parser.add_argument(\n'
            + '        "--oauth-redirect-uri", action="append", default=[],\n'
            + '        help="Additional exact or /* Cloudflare Managed OAuth DCR redirect URI; repeat as needed",\n'
            + '    )\n',
            "Cloudflare argument anchor",
        )

    function_anchor = "def provision_access(args: argparse.Namespace, account_id: str) -> tuple[str, str, str]:\n"
    if "def managed_oauth_configuration" not in text:
        helpers = '''def oauth_redirect_uris(args: argparse.Namespace) -> list[str]:
    configured = [str(value).strip() for value in (args.oauth_redirect_uri or []) if str(value).strip()]
    return list(dict.fromkeys([*DEFAULT_MCP_OAUTH_REDIRECT_URIS, *configured]))


def managed_oauth_configuration(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "enabled": True,
        "dynamic_client_registration": {
            "enabled": True,
            "allow_any_on_localhost": False,
            "allow_any_on_loopback": False,
            "allowed_uris": oauth_redirect_uris(args),
        },
        "grant": {"access_token_lifetime": "15m", "session_duration": "168h"},
    }


def access_application_body(args: argparse.Namespace, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    current = existing or {}
    return {
        "name": str(current.get("name") or "Heidi CLI MCP"),
        "domain": args.domain,
        "type": "mcp",
        "session_duration": str(current.get("session_duration") or "24h"),
        "app_launcher_visible": bool(current.get("app_launcher_visible", False)),
        "oauth_configuration": managed_oauth_configuration(args),
    }


'''
        text = replace_required(text, function_anchor, helpers + function_anchor, "Cloudflare access function anchor")

    old = '''    if access_app_id:
        access_app = request("GET", f"/accounts/{account_id}/access/apps/{access_app_id}")
        if str(access_app.get("domain") or "").rstrip("/") != args.domain.rstrip("/"):
            raise RuntimeError("configured Cloudflare Access application protects a different domain")
        if (access_app.get("oauth_configuration") or {}).get("enabled") is not True:
            raise RuntimeError("configured Cloudflare Access application does not have Managed OAuth enabled")
        audience = str(access_app.get("aud") or "")
    else:
        access_app = request(
            "POST", f"/accounts/{account_id}/access/apps",
            body={
                "name": "Heidi CLI MCP",
                "domain": args.domain,
                "type": "mcp",
                "session_duration": "24h",
                "app_launcher_visible": False,
                "oauth_configuration": {
                    "enabled": True,
                    "dynamic_client_registration": {
                        "enabled": True,
                        "allow_any_on_localhost": False,
                        "allow_any_on_loopback": False,
                        "allowed_uris": ["https://chatgpt.com/connector/oauth/*"],
                    },
                    "grant": {"access_token_lifetime": "15m", "session_duration": "168h"},
                },
            },
        )'''
    new = '''    if access_app_id:
        access_app = request("GET", f"/accounts/{account_id}/access/apps/{access_app_id}")
        if str(access_app.get("domain") or "").rstrip("/") != args.domain.rstrip("/"):
            raise RuntimeError("configured Cloudflare Access application protects a different domain")
        access_app = request(
            "PUT", f"/accounts/{account_id}/access/apps/{access_app_id}",
            body=access_application_body(args, access_app),
        )
        audience = str(access_app.get("aud") or "")
    else:
        access_app = request(
            "POST", f"/accounts/{account_id}/access/apps",
            body=access_application_body(args),
        )'''
    text = replace_required(text, old, new, "Cloudflare Access application provisioning")
    path.write_text(text, encoding="utf-8")


def migrate_env_and_docs() -> None:
    env_path = MCP / ".env.example"
    env = env_path.read_text(encoding="utf-8")
    env = env.replace(
        "MCP_ALLOWED_ORIGINS=https://chatgpt.com",
        "MCP_ALLOWED_ORIGINS=https://chatgpt.com,https://claude.ai,https://grok.com,https://gemini.google.com",
    )
    if "MCP_AUTH_MODE=" not in env:
        env = env.replace(
            "NODE_ENV=production\n",
            "NODE_ENV=production\n"
            "MCP_AUTH_MODE=cloudflare-managed-oauth\n"
            "MCP_OAUTH_AUTHORIZATION_SERVER=https://mcp.tnaprovider.com.au\n",
        )
    env_path.write_text(env, encoding="utf-8")

    readme_path = MCP / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if "## Universal MCP clients" not in readme:
        readme += '''

## Universal MCP clients

The public `/mcp` endpoint is host-neutral. MCP SDK v2 serves the 2026-07-28 request-scoped HTTP protocol and retains the existing sessionful 2025-era path for legacy clients on the same URL. Cloudflare Managed OAuth owns RFC 8414/9728 discovery, PKCE, token issuance, and Dynamic Client Registration at the edge; the Heidi origin validates only the resulting `Cf-Access-Jwt-Assertion`.

The Cloudflare provisioner enables first-party redirect families for ChatGPT, Claude, Grok, and Gemini and accepts repeatable `--oauth-redirect-uri` values for additional clients. Existing Access applications are updated in place so enabling a new client does not require recreating the MCP application. Keep redirect allowlists restricted to trusted first-party client domains.
'''
        readme_path.write_text(readme, encoding="utf-8")


def main() -> None:
    migrate_package()
    migrate_imports()
    migrate_gateway()
    migrate_v2_schema_shapes()
    migrate_cloudflare()
    migrate_env_and_docs()


if __name__ == "__main__":
    main()
