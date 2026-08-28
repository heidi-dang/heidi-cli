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

## Credentials

The installer creates a dedicated CPTR key named `heidi-mcp`. The standard profile contains only the control scopes needed for normal Direct Coding. The optional full profile adds `command:external`, which is required for explicitly approved external commands such as SSH or non-loopback browser/network actions.

The raw CPTR token exists only in `~/.config/heidi-cli/mcp.env`. CPTR stores only its SHA-256 digest. Re-running deployment rotates this key.

A separate MCP static token is generated for trusted loopback contract verification. Cloudflare Managed OAuth is the ChatGPT-facing production authentication mechanism.

Cloudflare API tokens are read without terminal echo and are not persisted. Tunnel runtime tokens are credentials and remain in an owner-only service environment file.

## File permissions

Configuration and secret files are created with umask `077` and explicitly set to mode `0600`. The configuration directory is owner-only.

`heidi doctor` verifies these permissions and performs a tracked-source secret-pattern scan.

## Cloudflare token permissions

Use a dedicated token. Do not use a Global API Key. Grant only the account/zone capabilities required for Tunnel, DNS, Access application/policy management, and Zero Trust organization discovery.

After provisioning, you may revoke the provisioning API token if you do not need automated future Cloudflare changes. The tunnel itself continues using its separate tunnel token.

## Installer trust

`curl | bash` is convenient but executes the current `main` installer. For higher-assurance environments, pin a release tag or commit, inspect `install.sh`, verify a signed release checksum, and then run the local copy.

A recommended next release feature is a signed manifest so the bootstrap verifies every downloaded source/runtime artifact before execution.

## Runtime downloads

The local Node.js fallback verifies the official SHA-256 published by nodejs.org. Rust is installed through rustup when missing. cloudflared is downloaded from Cloudflare's GitHub release channel and is executed with `--version` before activation.

For maximum supply-chain assurance, the next hardening step should pin and verify a Cloudflare-published checksum/signature for cloudflared rather than following `latest`.

## CPTR safety boundary

Direct Coding remains workspace-scoped. CPTR rejects traversal, environment-file reads, oversized/binary reads, ambiguous edits and known destructive command patterns. External commands require both an explicit network opt-in and the `command:external` scope.

FDX is repository intelligence, not an execution authority. Exact CPTR reads and write preconditions remain authoritative before source mutation.

## Multi-user warning

The CPTR backend fundamentally exposes the installing user's workstation capabilities. Do not share one instance with untrusted users. If multi-user isolation is required, move execution into per-user containers/VMs and make that sandbox the CPTR execution boundary.
