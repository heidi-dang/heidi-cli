# Heidi CLI

Heidi CLI is the canonical monorepo for the CPTR Computer stack:

- `apps/mcp` — ChatGPT-facing MCP / Apps SDK adapter and Live Workbench.
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
4. build the MCP server and Workbench;
5. compile the native FDX binary;
6. create/rotate a scoped CPTR control token for the current OS user;
7. prompt for **development** or **production** deployment;
8. configure loopback CPTR + MCP services;
9. optionally provision a Cloudflare remotely-managed tunnel, DNS CNAME, and Cloudflare Access MCP application using an API token;
10. verify FDX, CPTR health/readiness, MCP health, MCP tool/resource contract, and CPTR↔MCP connectivity;
11. print the final ChatGPT MCP URL.

Secrets are written only under `~/.config/heidi-cli` with owner-only permissions. They are never written into the Git checkout.

## Deployment modes

### Development

Development mode installs all three components and can run the MCP server in development mode with local hot reload. You may keep it local for MCP Inspector testing or configure Cloudflare to make it reachable by ChatGPT.

### Production

Production mode builds immutable artifacts, runs CPTR and MCP as user-level systemd services, enables bounded restart policies, and can create a remotely-managed Cloudflare Tunnel. When Cloudflare Access provisioning is selected, Heidi CLI creates an Access application of type `mcp`, enables Managed OAuth / dynamic client registration, and restricts the application to the email address you provide.

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

Add that endpoint when creating a custom MCP app/connector in ChatGPT. If Cloudflare Managed OAuth is enabled, complete the browser authorization flow and then scan the server tools.

OpenAI controls the final app creation, OAuth consent, tool scan, and action-review UI; a server-side installer cannot press those ChatGPT UI controls for you.

### Zero-workspace bootstrap

Heidi v2.1 exposes `cptr_workspace_lifecycle`, so ChatGPT can start from an empty CPTR workspace registry. `create`, `clone`, and `import` do not require an existing workspace ID. Git clones are confined below the managed Heidi workspace root, reject embedded credentials, register the new workspace immediately, and warm FDX repository intelligence when available. FDX warm-up failure is non-fatal and falls back to normal CPTR Direct Coding.

External imported directories are register-only: they can be archived from CPTR, but the lifecycle API will not recursively delete them. Managed workspace deletion is a separate request/confirm operation and requires the `workspace:delete` scope.

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
- The production MCP origin requires authentication.
- FDX is read-only through the ChatGPT intelligence gateway and remains local to the execution identity.
- The `standard` control profile includes safe workspace provisioning but not external execution or filesystem deletion.
- The explicit `owner-full` profile adds `command:external` and `workspace:delete`; legacy persisted `full` is accepted only as an alias and is migrated to `owner-full`.
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

## Licensing

This monorepo contains mixed-license components. Read `NOTICE.md` and the files in `LICENSES/`. In particular, `apps/cptr` remains governed by the Open Use License and its attribution requirements; `crates/fdx` remains MIT licensed.
