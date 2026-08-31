# Reusable Managed OAuth Client Design

## Goal

Add one reusable confidential OAuth `client_id` + `client_secret` pair for Heidi's public MCP endpoint while preserving Cloudflare Access Managed OAuth, Dynamic Client Registration (DCR), existing ChatGPT behavior, and Heidi's tool-only MCP host classification.

## Invariants

- Do not add MCP resources, Apps SDK UI resources, `ui.resourceUri`, or any equivalent metadata. The existing tool-only ChatGPT connector contract must remain unchanged.
- DCR remains enabled for clients that support it. The reusable confidential client is an additional authentication path, not a replacement.
- The reusable client uses OAuth 2.0 Authorization Code + refresh token grants and a confidential token endpoint method (`client_secret_post` by default).
- The client secret must never be committed to Git, written to MCP tool output, emitted in installer logs, copied into `state.env`, or placed in the MCP runtime environment when the MCP service does not need it.
- Redirect URIs remain an explicit allowlist. The built-in Claude callback remains supported and operators can add more callbacks through configuration.
- Deployment is idempotent. If the stored client registration matches the issuer/resource/auth method/redirect URI contract, it is reused without re-registration.
- A configuration mismatch fails closed rather than silently creating another reusable client.
- Explicit rotation is supported only when the stored DCR registration includes RFC 7592 management credentials (`registration_client_uri` + `registration_access_token`). If Cloudflare does not provide those fields, rotation refuses rather than orphaning a still-valid old client.

## Architecture

### Managed OAuth client helper

Create `scripts/managed-oauth-client.py`. It owns reusable-client lifecycle independently of Access application provisioning.

Inputs:

- public OAuth authorization-server metadata URL;
- protected MCP resource URL;
- owner-only credential file path;
- client name;
- one or more allowed redirect URIs;
- token endpoint auth method;
- optional rotate flag.

On first run the helper discovers the advertised `registration_endpoint`, registers a confidential client using RFC 7591-compatible metadata, validates that `client_id` and `client_secret` are returned, and atomically writes an owner-only JSON credential file with mode `0600`.

On later runs it loads the credential file and compares the normalized registration contract. Matching state returns `reused` without a network registration call. Mismatched state fails with an actionable rotation error.

When rotation is explicitly requested, the helper first requires RFC 7592 management metadata in the stored registration. It deletes the old registration using its registration access token, then creates and persists the replacement. If management metadata is unavailable or deletion fails, the helper preserves the existing credential file and aborts.

The helper's stdout contains only non-secret lifecycle metadata such as action, client ID, file path and redirect URIs. It never prints the client secret or registration access token.

### Installer integration

`install-core.sh` will:

1. Build one normalized OAuth redirect allowlist containing Claude's callback plus any operator-provided `MCP_OAUTH_REDIRECT_URIS` entries.
2. Pass that allowlist to Cloudflare Access Managed OAuth DCR configuration.
3. After Access provisioning returns the auth domain, run `managed-oauth-client.py` for public deployments unless `HEIDI_MCP_OAUTH_GLOBAL_CLIENT=0`.
4. Reuse `$CONFIG_DIR/oauth-client.json` across releases.
5. Support explicit rotation with `HEIDI_MCP_OAUTH_GLOBAL_CLIENT_ROTATE=1`.
6. Store only the non-secret client ID and credential-file path in `state.env`.

The MCP service itself continues validating Cloudflare's signed Access assertion exactly as before. It does not receive or validate the global OAuth client secret.

### Verification

`verify-stack.sh` will verify, without printing secrets, that an enabled reusable-client deployment has:

- an owner-readable credential file;
- mode `0600` (or stricter equivalent owner-only mode);
- non-empty `client_id` and `client_secret` fields;
- state metadata whose client ID matches the credential file;
- the expected MCP resource URL and authorization-server issuer recorded in the credential file.

## Error handling

- Missing redirect URI allowlist: fail before registration.
- Discovery metadata missing `registration_endpoint`: fail closed.
- Non-HTTPS remote registration/management URLs: reject; loopback HTTP is allowed only for tests.
- Registration response missing either client ID or secret: fail without creating a credential file.
- Existing credential file is malformed or has unsafe permissions: fail closed.
- Existing registration contract differs from deployment configuration: require explicit rotation.
- Rotation without management credentials: fail before deleting or overwriting anything.
- Failed old-client deletion: preserve current credentials and abort.
- Failed new registration after successful deletion: do not write partial credentials; deployment fails and requires a fresh registration on the next run.

## Testing

Add Python contract tests with an in-process fake OAuth server to prove:

- first registration sends the intended confidential-client metadata and persists mode `0600`;
- stdout never exposes either secret;
- exact reruns reuse the existing pair without POSTing again;
- mismatched redirect configuration fails closed;
- explicit rotation deletes the managed old registration before creating a replacement;
- rotation refuses when management metadata is absent;
- installer wiring preserves DCR and keeps the OAuth secret out of `state.env` and MCP environment configuration;
- existing MCP v2 OAuth/tool-only contract tests continue to pass.

## Deployment result

After a production deployment, operators can use the same saved `client_id` + `client_secret` in remote MCP clients that support manual confidential OAuth credentials, including Claude's Advanced settings. DCR-capable clients remain free to register independently. The secret remains an operator credential and must be distributed only to clients that can protect confidential credentials.
