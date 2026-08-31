# Security

Heidi CLI controls a real workstation. Treat the stack with the same care as SSH access to the machine.

## Default network model

- CPTR binds to loopback only.
- MCP binds to loopback only.
- FDX has no public listener; its daemon is a child process owned by CPTR.
- Production publishes only MCP through Cloudflare Tunnel.
- Cloudflare Access authenticates the user before requests reach the MCP origin.
- The MCP origin independently validates the Access JWT (`Cf-Access-Jwt-Assertion`), including signature, issuer, audience and allowed email.

Do not create a direct public route to CPTR.

## Credentials and control profiles

The installer creates a dedicated CPTR key named `heidi-mcp`. Heidi defaults to the `owner-full` profile: it contains the normal Direct Coding and safe workspace-bootstrap scopes plus `command:external` for explicitly network-opted operations such as Git push and deployment commands, and `workspace:delete` for confirmed deletion of Heidi-managed workspaces.

The `standard` and `developer` profiles remain available as explicit locked-down selections. `standard` omits both `command:external` and `workspace:delete`; `developer` adds `command:external` but still omits `workspace:delete`. Persisted `standard` and `developer` defaults migrate to `owner-full` during deployment unless the operator explicitly sets `HEIDI_CONTROL_PROFILE`.

Legacy `full` is accepted only as a compatibility alias and is normalized to `owner-full` during deployment.

Neither `developer` nor `owner-full` is an authentication or safety bypass. CPTR authentication, workspace ownership, secret redaction, destructive-command classification, explicit `allow_network=true` opt-in, managed-root confinement, and purpose-built confirmation boundaries remain enforced. Managed workspace deletion requires a short-lived request/confirm exchange; imported external directories can be archived from CPTR but cannot be recursively deleted through the lifecycle API.

The raw CPTR token exists only in `~/.config/heidi-cli/mcp.env`. CPTR stores only its SHA-256 digest. Re-running deployment rotates this key.

A separate MCP static token is generated for trusted loopback contract verification. Cloudflare Managed OAuth is the ChatGPT-facing production authentication mechanism.

Public Managed OAuth deployments also create or reuse one confidential OAuth `client_id` + `client_secret` pair by default for remote clients that require manual credentials. This is additive to Dynamic Client Registration (DCR); DCR remains enabled for ChatGPT and other compatible clients. The reusable registration is stored only in `~/.config/heidi-cli/oauth-client.json` with mode `0600`. `state.env` stores only the non-secret client ID and credential-file path, and `mcp.env` does not receive the reusable client secret.

Treat both `client_secret` and any RFC 7592 `registration_access_token` in `oauth-client.json` as owner credentials. Do not print them, commit them, paste them into issue trackers or chat logs, or distribute them to clients that cannot protect confidential OAuth credentials. Heidi's installer and verifier deliberately return only redacted lifecycle metadata.

Dynamic Client Registration remains enabled independently. Cloudflare's DCR callback policy may contain supported wildcard paths for hosts such as Gemini Spark, while the reusable client's redirect list must contain exact absolute URIs only. `scripts/managed-oauth-client.py` rejects wildcard reusable-client callbacks so DCR flexibility does not weaken the static confidential-client contract.

Exact redeployments reuse the saved client pair. Configuration drift fails closed. Rotation requires `HEIDI_MCP_OAUTH_GLOBAL_CLIENT_ROTATE=1` and is allowed only when the existing registration contains management credentials that let Heidi revoke the old client before replacement; otherwise rotation refuses rather than silently orphaning a valid credential. Set `HEIDI_MCP_OAUTH_GLOBAL_CLIENT=0` to disable the reusable client while retaining DCR.

Cloudflare API tokens are read without terminal echo and are not persisted. Tunnel runtime tokens are credentials and remain in an owner-only service environment file.

## Workspace provisioning boundary

Managed create/clone destinations are confined below `CPTR_WORKSPACE_ROOT`, which defaults below the CPTR data directory. Workspace names are validated before path construction, and resolved destinations must remain under that root.

Git clone uses argument-vector subprocess execution rather than shell interpolation. Heidi accepts HTTPS, SSH, and standard SCP-style Git SSH repository locations, but rejects repository URLs containing embedded credentials. ChatGPT-visible lifecycle responses return stable workspace IDs and readiness metadata rather than absolute host paths.

FDX warm-up is an intelligence optimization, not an authorization boundary. A failed FDX warm-up leaves the CPTR workspace usable and returns bounded fallback metadata so normal Direct Coding remains available.

## File permissions

Configuration and secret files are created with umask `077` and explicitly set to mode `0600`. The configuration directory is owner-only. This includes `mcp.env`, `cloudflare.env`, and reusable `oauth-client.json` when present.

`heidi doctor` verifies these permissions and performs a tracked-source secret-pattern scan. `heidi verify` also checks that reusable OAuth credentials are owner-only, structurally valid, and consistent with deployment state without emitting `client_secret`.

## Cloudflare token permissions

Use a dedicated token. Do not use a Global API Key. Grant only the account/zone capabilities required for Tunnel, DNS, Access application/policy management, and Zero Trust organization discovery.

After provisioning, you may revoke the provisioning API token if you do not need automated future Cloudflare changes. The tunnel itself continues using its separate tunnel token.

## Installer and release trust

`curl | bash` is convenient but executes the current `main` installer. For higher-assurance environments, use a Heidi signed release channel or pin a release tag/commit and inspect the installer before execution.

Heidi releases publish a deterministic source archive plus a signed release manifest. The bootstrap verifies the manifest signature against the committed Ed25519 public trust root and validates pinned runtime/source checksums before activation. Release CI also verifies that the signing secret derives the committed public key before publishing channel assets.

## Runtime downloads

Downloaded runtimes are selected from the signed runtime lock and verified against pinned SHA-256 checksums before activation. Runtime archives are extracted using constrained formats/member names appropriate to each artifact.

## CPTR safety boundary

Direct Coding remains workspace-scoped. CPTR rejects traversal, environment-file reads, oversized/binary reads, ambiguous edits and known destructive command patterns. External commands require both an explicit network opt-in and the `command:external` scope.

FDX is repository intelligence, not an execution authority. Exact CPTR reads and write preconditions remain authoritative before source mutation.

## Multi-user warning

The CPTR backend fundamentally exposes the installing user's workstation capabilities. Do not share one instance with untrusted users. If multi-user isolation is required, move execution into per-user containers/VMs and make that sandbox the CPTR execution boundary.
