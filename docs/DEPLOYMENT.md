# Deployment

## Supported managed host

The initial Heidi installer targets Linux with a user-level systemd manager. CPTR and MCP run as the installing user so direct coding operates under the expected workstation identity. Production deployments enable systemd user lingering when possible.

## Quick install

```bash
curl -fsSL https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.sh | bash
```

The bootstrap installs the source checkout beneath `~/.local/share/heidi-cli/repo` and executes the interactive deployment wizard.

## Wizard choices

The wizard asks for:

- development or production mode;
- CPTR and MCP loopback ports;
- CPTR control profile (`owner-full` by default; `developer` or `standard` only when explicitly selected);
- whether a development deployment should be made remote;
- public MCP hostname;
- Cloudflare Account ID;
- Cloudflare Zone ID;
- email identity allowed by Access;
- a hidden Cloudflare API token.

Production always configures a remote Cloudflare deployment because ChatGPT cannot directly connect to a localhost MCP endpoint.

## Cloudflare API token

Use a dedicated least-privilege token. The automatic production path needs the permissions required to:

- create/read/configure a remotely-managed Cloudflare Tunnel;
- create/update the CNAME DNS record;
- create/read the Cloudflare Access MCP application and application policy;
- read the Zero Trust organization `auth_domain`.

The API token is used only by the provisioning process and is then unset. It is not stored in Heidi configuration. The resulting tunnel runtime token is stored in `~/.config/heidi-cli/cloudflare.env` with mode `0600` because cloudflared requires it to reconnect.

## Managed OAuth client modes

Cloudflare Access Managed OAuth remains the public authentication layer. Heidi preserves Dynamic Client Registration (DCR) and, by default, also creates or reuses one confidential OAuth `client_id` + `client_secret` registration for MCP clients that require manually configured credentials.

The reusable registration is stored in:

```text
~/.config/heidi-cli/oauth-client.json
```

The file is owner-only (`0600`). `state.env` records only `HEIDI_MCP_OAUTH_CLIENT_ID` and `HEIDI_MCP_OAUTH_CLIENT_FILE`; the `client_secret` and RFC 7592 registration-management token stay only in `oauth-client.json`. They are not written to `mcp.env`.

Deployment behavior is controlled by:

```text
HEIDI_MCP_OAUTH_GLOBAL_CLIENT=1          # default; create or reuse
HEIDI_MCP_OAUTH_GLOBAL_CLIENT=0          # disable reusable pair; DCR remains enabled
HEIDI_MCP_OAUTH_GLOBAL_CLIENT_ROTATE=1   # explicitly replace the saved registration
MCP_OAUTH_DCR_REDIRECT_URIS=https://client.example/callback,https://oauth.example/r/*
MCP_OAUTH_GLOBAL_CLIENT_REDIRECT_URIS=https://client.example/callback
```

The default Cloudflare DCR allowlist includes Claude's exact callback, Grok's callback, and Gemini Spark's Google OAuth proxy path. `MCP_OAUTH_DCR_REDIRECT_URIS` adds exact or Cloudflare-supported wildcard callbacks; legacy `MCP_OAUTH_REDIRECT_URIS` remains accepted for DCR. The reusable confidential client has a separate exact-only redirect list: `MCP_OAUTH_GLOBAL_CLIENT_REDIRECT_URIS` adds exact callbacks to that registration and to the DCR allowlist, while wildcard reusable-client callbacks are rejected.

A normal redeploy reuses a matching saved pair. If the resource, redirect URIs, client name, or token-endpoint authentication method no longer matches, deployment fails closed and requires an explicit rotation decision. Rotation succeeds only if the stored registration contains `registration_client_uri` and `registration_access_token`, allowing Heidi to revoke the old client first. If those management values are absent, Heidi refuses rotation rather than leaving an unknown live credential behind.

Remote clients that support DCR can continue leaving OAuth Client ID/Secret blank. Clients that require manual confidential credentials may use the saved `client_id` and `client_secret` only if they can protect secrets appropriately.

## Services

The installer writes:

```text
~/.config/systemd/user/heidi-cptr.service
~/.config/systemd/user/heidi-mcp.service
~/.config/systemd/user/heidi-cloudflared.service   # public deployments only
```

and secret/configuration files:

```text
~/.config/heidi-cli/state.env
~/.config/heidi-cli/cptr.env
~/.config/heidi-cli/mcp.env
~/.config/heidi-cli/cloudflare.env                 # public deployments only
~/.config/heidi-cli/oauth-client.json              # reusable Managed OAuth client, when enabled
```

`oauth-client.json` is mode `0600` and is the only Heidi configuration file that stores the reusable OAuth `client_secret`. `state.env` stores only `HEIDI_MCP_OAUTH_CLIENT_ID` and `HEIDI_MCP_OAUTH_CLIENT_FILE`; `mcp.env` does not need the reusable client secret.

The reusable client is additive to Dynamic Client Registration (DCR). Set `HEIDI_MCP_OAUTH_GLOBAL_CLIENT=0` to disable it or `HEIDI_MCP_OAUTH_GLOBAL_CLIENT_ROTATE=1` for an explicit managed rotation. Additional DCR callback patterns can be supplied with `MCP_OAUTH_DCR_REDIRECT_URIS` (legacy `MCP_OAUTH_REDIRECT_URIS` remains accepted). Additional reusable-client callbacks must be exact URIs supplied through `MCP_OAUTH_GLOBAL_CLIENT_REDIRECT_URIS`.

The default DCR policy covers Claude, the Grok callback, and Gemini Spark's Google OAuth proxy path. The Spark proxy uses a wildcard path only in Cloudflare's DCR allowlist; the reusable client itself rejects wildcard redirect URIs.

The CPTR data directory defaults to `~/.cptr` and is deliberately outside the install-managed source directory.

## Verification

A deployment is not considered successful merely because systemd reports `active`. `heidi verify` checks:

1. native FDX binary/version;
2. CPTR `/api/health/live`;
3. CPTR `/api/health/ready`;
4. MCP `/health`;
5. reusable OAuth credential-file ownership, schema, non-empty client ID/secret, resource, client ID and Cloudflare issuer consistency when enabled, without printing the secret;
6. the exact 26-tool MCP contract, absence of MCP resources/UI metadata, and disabled compatibility Workbench using the adapter's deployed-contract verifier;
7. the private MCP→CPTR bearer path by listing CPTR workspaces;
8. public Cloudflare DNS/TLS/Access reachability when enabled.

The final OAuth authorization and ChatGPT `Scan Tools` step must occur inside ChatGPT because that UI and authorization session are owned by OpenAI, not by the MCP server.

## Operations

```bash
heidi status
heidi doctor
heidi verify
heidi url
heidi restart
heidi logs all
heidi update
```

`heidi update` fetches the current `main` bootstrap, rebuilds all three components, preserves the CPTR data directory, rotates Heidi MCP's scoped CPTR credential, restarts services, and verifies the stack again. A normal update does **not** rotate the reusable OAuth client; it reuses the existing matching pair.

To intentionally rotate the reusable OAuth client during deployment, set `HEIDI_MCP_OAUTH_GLOBAL_CLIENT_ROTATE=1` for that deployment. Treat rotation as a credential change: update every manual client that used the old pair after the new registration is created.

## Rollback recommendation

Prefer signed release tags and keep one previous installed source tree under an immutable release directory. A future `heidi rollback <version>` command should switch service unit paths atomically without touching `~/.cptr`.

Until that lands, operators can mitigate risk by:

1. Recording the current `HEIDI_REPO_DIR` and `release/compatibility.json` `heidi_version` before `heidi update`.
2. Keeping the previous checkout path read-only (do not `git reset --hard` a live tree).
3. Pointing systemd unit `WorkingDirectory` / binary paths back to the prior tree and running `heidi verify`.
4. Confirming CPTR data under `~/.cptr` was not migrated destructively (Heidi preserves it by default).

Never use `git reset --hard` against an active production checkout as the primary rollback path.
