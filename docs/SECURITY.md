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

The installer creates a dedicated CPTR key named `heidi-mcp`. The `standard` profile contains the scopes required for normal Direct Coding and safe workspace bootstrap, including `workspace:provision`, but it does not grant `command:external` or `workspace:delete`.

The explicit `owner-full` profile adds `command:external` for approved SSH/browser/non-loopback network operations and `workspace:delete` for confirmed deletion of Heidi-managed workspaces. Legacy `full` is accepted only as a compatibility alias and is normalized to `owner-full` during deployment.

`owner-full` is not an authentication or safety bypass. CPTR authentication, workspace ownership, secret redaction, destructive-command classification, explicit network opt-in, managed-root confinement, and purpose-built confirmation boundaries remain enforced. Managed workspace deletion requires a short-lived request/confirm exchange; imported external directories can be archived from CPTR but cannot be recursively deleted through the lifecycle API.

The raw CPTR token exists only in `~/.config/heidi-cli/mcp.env`. CPTR stores only its SHA-256 digest. Re-running deployment rotates this key.

A separate MCP static token is generated for trusted loopback contract verification. Cloudflare Managed OAuth is the ChatGPT-facing production authentication mechanism.

Cloudflare API tokens are read without terminal echo and are not persisted. Tunnel runtime tokens are credentials and remain in an owner-only service environment file.

## Workspace provisioning boundary

Managed create/clone destinations are confined below `CPTR_WORKSPACE_ROOT`, which defaults below the CPTR data directory. Workspace names are validated before path construction, and resolved destinations must remain under that root.

Git clone uses argument-vector subprocess execution rather than shell interpolation. Heidi accepts HTTPS, SSH, and standard SCP-style Git SSH repository locations, but rejects repository URLs containing embedded credentials. ChatGPT-visible lifecycle responses return stable workspace IDs and readiness metadata rather than absolute host paths.

FDX warm-up is an intelligence optimization, not an authorization boundary. A failed FDX warm-up leaves the CPTR workspace usable and returns bounded fallback metadata so normal Direct Coding remains available.

## File permissions

Configuration and secret files are created with umask `077` and explicitly set to mode `0600`. The configuration directory is owner-only.

`heidi doctor` verifies these permissions and performs a tracked-source secret-pattern scan.

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
