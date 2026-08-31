# Heidi CLI

Heidi CLI is the canonical monorepo for the CPTR Computer stack:

- `apps/mcp` — ChatGPT-facing 26-tool MCP adapter plus one bounded MCP Apps Workbench resource at `ui://cptr/live-workbench.html`.
- `apps/cptr` — CPTR backend, control plane, execution runtime, browser/SSH/direct-coding services, persistence, and verification.
- `crates/fdx` — native FDX repository-intelligence CLI and persistent daemon.
- `install.sh` + `bin/heidi` — installation, configuration, deployment, verification, update, status, logs, and URL discovery.

The stack is intentionally deployed as one trust boundary on a single machine: CPTR and MCP bind to loopback by default; only the MCP endpoint is published through Cloudflare Tunnel in production. FDX stays local and is invoked by CPTR.

## One-line install

```bash
curl -fsSL https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.sh | bash
```

The interactive installer opens `/dev/tty`, so prompts still work when the script itself is piped through `curl`.

It will:

1. clone/update this repository under `~/.local/share/heidi-cli`;
2. validate/install required local runtimes;
3. build the CPTR frontend and Python environment;
4. build the production MCP server and signed Workbench UI assets; production exposes exactly one Apps resource and keeps hot reload disabled;
5. compile the native FDX binary;
6. create/rotate a scoped CPTR control token for the current OS user;
7. prompt for **development** or **production** deployment;
8. configure loopback CPTR + MCP services;
9. optionally provision a Cloudflare remotely-managed tunnel, DNS CNAME, and Cloudflare Access MCP application using an API token;
10. verify FDX, CPTR health/readiness, MCP health, the exact 26-tool + one-resource Apps contract, and CPTR↔MCP connectivity;
11. print the final ChatGPT MCP URL.

Secrets are written only under `~/.config/heidi-cli` with owner-only permissions. They are never written into the Git checkout.

## Deployment modes

### Development

Development mode installs all three components and can run the MCP server in development mode with local hot reload. You may keep it local for MCP Inspector testing or configure Cloudflare to make it reachable by ChatGPT.

### Production

Production mode builds immutable artifacts, runs CPTR and MCP as user-level systemd services, enables bounded restart policies, and can create a remotely-managed Cloudflare Tunnel. When Cloudflare Access provisioning is selected, Heidi CLI creates an Access application of type `mcp`, enables Managed OAuth / Dynamic Client Registration (DCR), restricts the application to the email address you provide, and by default creates or reuses one confidential OAuth `client_id` + `client_secret` pair for clients that require manual OAuth credentials.

The reusable pair is additive: DCR remains enabled for ChatGPT and other clients that can register themselves. Its credentials are stored only in `~/.config/heidi-cli/oauth-client.json` with mode `0600`; `state.env` contains only the non-secret client ID and credential-file path, and `mcp.env` does not contain the reusable client secret.

The Cloudflare API token should be least-privilege and include only the permissions needed for the features you choose, typically:

- Account: Cloudflare Tunnel — Edit
- Zone: DNS — Edit
- Account: Access Apps and Policies — Edit
- Account: Access Organizations / Identity Providers / Groups — Read (only if automatic Access issuer discovery is desired)

The installer never stores the Cloudflare API token after provisioning unless you explicitly choose to keep it.

## ChatGPT

After a successful public deployment, Heidi CLI prints:

```text
https://<your-mcp-domain>/mcp
```

Add that endpoint when creating a custom MCP app/connector in ChatGPT. If Cloudflare Managed OAuth is enabled, complete the browser authorization flow and then scan the server tools/resources. ChatGPT can continue using DCR; the reusable confidential client does not alter Heidi's bounded Apps contract: 26 compact tools plus exactly one Workbench resource, with only `cptr_open_live_workbench` publishing `ui.resourceUri`.

OpenAI controls the final app creation, OAuth consent, tool scan, and action-review UI; a server-side installer cannot press those ChatGPT UI controls for you.

### Zero-workspace bootstrap

Heidi v2.1 exposes `cptr_workspace_lifecycle`, so ChatGPT can start from an empty CPTR workspace registry. `create`, `clone`, and `import` do not require an existing workspace ID. Git clones are confined below the managed Heidi workspace root, reject embedded credentials, register the new workspace immediately, and warm FDX repository intelligence when available. FDX warm-up failure is non-fatal and falls back to normal CPTR Direct Coding.

External imported directories are register-only: they can be archived from CPTR, but the lifecycle API will not recursively delete them. Managed workspace deletion is a separate request/confirm operation and requires the `workspace:delete` scope.

## Reusable OAuth client

Public deployments enable the reusable confidential client by default. The installer discovers Cloudflare Managed OAuth's authorization-server metadata, registers the client against the advertised DCR endpoint, and persists the resulting registration in:

```text
~/.config/heidi-cli/oauth-client.json
```

Use the saved `client_id` and `client_secret` only with remote MCP clients that can protect confidential OAuth credentials. Never copy the file into a repository, issue, log, chat transcript, or shared shell history.

The lifecycle is intentionally conservative:

- Exact redeployments reuse the same pair instead of generating another client.
- Redirect URI, resource, client-name, or authentication-method drift fails closed and requires an explicit rotation decision.
- `HEIDI_MCP_OAUTH_GLOBAL_CLIENT=0` disables creation/use of the reusable client while leaving DCR available.
- `HEIDI_MCP_OAUTH_GLOBAL_CLIENT_ROTATE=1` explicitly rotates the reusable registration. Rotation is accepted only when the existing DCR response supplied RFC 7592 registration-management credentials so Heidi can revoke the old registration before creating a replacement.
- `MCP_OAUTH_DCR_REDIRECT_URIS` adds comma-separated exact or Cloudflare-supported wildcard callbacks to the DCR policy. Legacy `MCP_OAUTH_REDIRECT_URIS` remains accepted as DCR-list input.
- `MCP_OAUTH_GLOBAL_CLIENT_REDIRECT_URIS` adds comma-separated **exact** callbacks to the reusable client and its DCR allowlist. Wildcard entries are rejected.

The default DCR policy covers Claude's exact callback, Grok's callback, and Gemini Spark's Google OAuth proxy path. Gemini Spark uses `https://oauth-redirect.googleusercontent.com/r/*` only in Cloudflare's DCR allowlist; the reusable RFC 7591 client keeps exact redirect URIs and therefore does not store that wildcard.

`heidi verify` checks that the credential file is owner-only, structurally valid, and consistent with `state.env`, the protected origin resource, and Cloudflare issuer without printing `client_secret` or registration-management credentials.

## Claude remote MCP

Cloudflare Managed OAuth is provisioned for Claude's Dynamic Client Registration callback. Heidi adds Claude's exact remote-MCP OAuth redirect URI to the Access application's DCR allowlist while preserving redirect URIs already configured for other MCP clients.

In Claude, add the same public MCP endpoint:

```text
https://<your-mcp-domain>/mcp
```

You can leave **OAuth Client ID** and **OAuth Client Secret** blank when using DCR, or use the reusable pair from the owner-only `oauth-client.json` when a Claude configuration explicitly requires manual confidential OAuth credentials. In either case, connect and complete the Cloudflare authorization flow. The generic Cloudflare provisioner remains provider-neutral; the Claude callback is applied only by Heidi's deployment/client-profile layer.

Additional remote-MCP callbacks can still be supplied through `MCP_OAUTH_REDIRECT_URIS` or repeated `--oauth-redirect-uri` arguments to `scripts/cloudflare-provision.py`. Existing Access application redirect URIs are retained when Heidi updates the application.

## Heidi command

After installation, ensure `~/.local/bin` is on your `PATH`, then use:

```bash
heidi status
heidi doctor
heidi verify
heidi url
heidi logs cptr
heidi logs mcp
heidi logs tunnel
heidi restart
heidi update
heidi deploy
heidi deploy --mode production
heidi deploy --mode dev
```

`heidi deploy --mode production` runs the compiled MCP server. `heidi deploy --mode dev` runs the MCP development watcher with server restart and Live Workbench hot reload, and persists `development` as the deployment mode. Omitting `--mode` keeps the interactive/current-mode selection flow. `heidi doctor` performs dependency/configuration checks without mutating the deployment. `heidi verify` performs live stack verification.

## Security defaults

- CPTR defaults to `127.0.0.1:8000`.
- MCP defaults to `127.0.0.1:8787`.
- Cloudflare Tunnel publishes MCP only; CPTR is not directly exposed.
- CPTR API credentials are generated locally and stored with mode `0600`.
- Reusable OAuth credentials, when enabled, are stored only in owner-only `oauth-client.json`; the client secret is not copied into `state.env` or `mcp.env`.
- The production MCP origin requires authentication.
- FDX is read-only through the ChatGPT intelligence gateway and remains local to the execution identity.
- The default `owner-full` control profile includes safe workspace provisioning, `command:external` for explicitly network-opted push/deploy operations, and confirmed managed-workspace deletion through `workspace:delete`.
- The `standard` and `developer` profiles remain available only when explicitly selected; `standard` omits external execution and deletion, while `developer` allows external execution without deletion.
- Persisted `standard`, `developer`, and legacy `full` defaults migrate to `owner-full` on deployment unless `HEIDI_CONTROL_PROFILE` is explicitly set.
- Managed filesystem deletion remains a two-step request/confirm operation even under `owner-full`.
- Existing `~/.cptr` state is reused by default so upgrades preserve CPTR workspaces and data.

See `docs/SECURITY.md` before exposing a deployment to anyone other than the machine owner.

## Development from the monorepo

```bash
npm --prefix apps/mcp ci
npm --prefix apps/mcp run build
npm --prefix apps/mcp test
npm --prefix apps/mcp run typecheck

python -m pytest apps/cptr/tests

cargo fmt --all -- --check
cargo test -p fdx
```

FDX can be built directly with:

```bash
cargo build --release -p fdx
./target/release/fdx --version
```

## Repository policy

This repository intentionally avoids Git submodules and nested Git repositories. The three runtime components are versioned together so a release can guarantee a compatible MCP schema, CPTR control API, and FDX protocol.

Generated output, local databases, `.env` files, node modules, Python environments, Rust `target`, CPTR data, FDX indexes, and deployment secrets are excluded from Git.

Repository ownership and split-upstream synchronization rules are defined in `docs/REPOSITORY_GOVERNANCE.md`.

## Licensing

This monorepo contains mixed-license components. Read `NOTICE.md` and the files in `LICENSES/`. In particular, `apps/cptr` remains governed by the Open Use License and its attribution requirements; `crates/fdx` remains MIT licensed.
