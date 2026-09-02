# Heidi CLI architecture

## Goal

Heidi CLI versions and deploys the ChatGPT MCP adapter, CPTR execution backend, and FDX repository-intelligence engine as one compatibility-tested product while preserving clear internal boundaries.

```text
ChatGPT
   |
   | HTTPS / MCP + OAuth
   v
Cloudflare Access + Tunnel
   |
   v
apps/mcp (loopback :8787)
   |
   | scoped CPTR bearer
   v
apps/cptr (loopback :8000)
   |
   +---- filesystem / git / commands / browser / SSH
   |
   +---- crates/fdx resident daemon + CLI
```

## Component boundaries

### `apps/mcp`

Transport and presentation only. It owns:

- MCP Streamable HTTP and the exact 26-tool production schema;
- optional compatibility/development Workbench assets and endpoints, disabled in the production contract;
- OAuth / Cloudflare Access assertion validation;
- CPTR HTTP client;
- public health and deployed-contract verification.

It does **not** own host execution, workspace authorization, command policy, or FDX execution.

### `apps/cptr`

The authoritative local control plane. It owns:

- users, workspaces, scopes and API keys;
- filesystem and Git boundaries;
- direct coding and model-free worktree workers;
- managed commands, browser and SSH execution;
- durable tasks, monitors, evidence and verification;
- FDX process lifecycle and bounded gateway responses.

The default direct-coding path keeps ChatGPT as the reasoner. Delegated model/agent execution remains a separate opt-in capability.

### `crates/fdx`

Native read-only repository intelligence. It owns:

- token-efficient reads and outlines;
- search/grep and batch inspection;
- impact / why / evidence graph reasoning;
- semantic and build intelligence;
- verification planning;
- the persistent `fdx serve` JSON-lines daemon.

CPTR is the authorization boundary. FDX does not widen workspace access.

## Why a monorepo

The prior split repositories could drift independently: MCP tool schemas, CPTR routes, and FDX daemon contracts could each be valid alone while incompatible together. A monorepo enables one CI matrix and one release gate for the whole path.

The code is still separated by runtime responsibility. This is a monorepo, not a monolith.

## Deployment boundary

The installer binds CPTR and MCP to loopback. In production, Cloudflare Tunnel exposes only MCP. CPTR is never given a public DNS route by the Heidi installer.

Secrets live in `~/.config/heidi-cli/*.env` with mode `0600`. Runtime data remains in `~/.cptr` by default so reinstalling/updating Heidi CLI does not erase existing CPTR state.

## Compatibility authority

The single compatibility authority is `release/compatibility.json` (schema `heidi.compatibility.v1`). It records:

- Heidi release version;
- MCP contract version and registered action count;
- CPTR package version and control API revision;
- FDX package and protocol/capability versions;
- deployment topologies and sandbox defaults;
- ordered migration notes for operators.

`scripts/verify-compatibility.py` cross-checks that file against `package.json`, `apps/mcp/package.json`, `apps/cptr/pyproject.toml`, `crates/fdx/Cargo.toml`, and the canonical MCP tool inventory in `apps/mcp/server/release.ts`. `heidi verify` (via `scripts/verify-stack.sh`) runs the same check on deployed installations.

A root alias `heidi-release.json` mirrors the same document for discoverability; treat `release/compatibility.json` as the path CI and installers open by default.
