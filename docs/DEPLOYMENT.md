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
- standard or full CPTR control profile;
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
```

The CPTR data directory defaults to `~/.cptr` and is deliberately outside the install-managed source directory.

## Verification

A deployment is not considered successful merely because systemd reports `active`. `heidi verify` checks:

1. native FDX binary/version;
2. CPTR `/api/health/live`;
3. CPTR `/api/health/ready`;
4. MCP `/health`;
5. the exact MCP tool/resource contract using the adapter's deployed-contract verifier;
6. the private MCP→CPTR bearer path by listing CPTR workspaces;
7. public Cloudflare DNS/TLS/Access reachability when enabled.

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

`heidi update` fetches the current `main` bootstrap, rebuilds all three components, preserves the CPTR data directory, rotates Heidi MCP's scoped CPTR credential, restarts services, and verifies the stack again.

## Rollback recommendation

Before production use, add signed release tags and keep one previous installed source tree under an immutable release directory. `heidi rollback <version>` can then switch service paths atomically without database deletion. This is recommended as the next lifecycle feature rather than using `git reset --hard` against a live installation.
