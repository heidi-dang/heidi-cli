# Heidi repository governance

## Canonical product repository

`heidi-dang/heidi-cli` is the canonical repository for the production Heidi product. Its compatibility manifest, installer, MCP adapter, CPTR runtime integration, FDX protocol, CI, and signed release workflow are the authoritative release boundary.

Production Heidi fixes must land in `heidi-cli` first. A split repository must never become an independent production release authority for Heidi.

## Split repository roles

### `heidi-dang/computer`

`computer` remains an active generic CPTR/Open WebUI Computer upstream. Changes may be imported into `apps/cptr` only through an explicit audited sync that records the upstream commit in `docs/SOURCE_PROVENANCE.md`, reviews the source diff, updates compatibility metadata when required, and runs the Heidi cross-component gates.

Heidi-specific hardening may remain downstream in `apps/cptr`; do not automatically push those changes back upstream unless they are appropriate for the generic product.

### `heidi-dang/chatgpt-computer-plugin`

The standalone plugin is a historical/reference upstream for `apps/mcp`, not a production Heidi release authority. New production MCP work belongs in `apps/mcp`. If a useful standalone change is imported, record its exact source commit and re-run the compact-contract and host-classification gates.

## Sync invariant

Every split-repository import must satisfy all of the following:

1. record repository, branch, and exact source commit;
2. import only tracked source required by Heidi;
3. exclude nested `.git`, generated output, caches, credentials, and machine state;
4. review the source delta against the current Heidi component before integration;
5. preserve the 26-tool production MCP contract unless a deliberate versioned contract migration is approved;
6. update `release/compatibility.json` for component/protocol changes;
7. run installer, MCP, CPTR, and FDX gates before merge.

## Workflow policy

Persistent workflow files on `main` are restricted to:

- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`

Temporary migration, repair, surgical-patch, or one-shot workflows must be removed from the default branch and disabled in GitHub Actions immediately after their purpose is complete. They must not become an alternate deployment or mutation path.

Platform-managed dynamic workflows such as GitHub/Copilot integrations are outside the tracked workflow-file allowlist but should remain enabled only when intentionally used.

## Release authority

A production Heidi release is accepted only when:

- the signed release manifest identifies the exact Git commit and source archive checksum;
- `release/compatibility.json` matches the MCP/CPTR/FDX runtime contract;
- the production MCP reports the same source commit in `/health` and update metadata;
- the production MCP contract advertises exactly 26 compact tools plus exactly one Apps resource at `ui://cptr/live-workbench.html`, with `cptr_open_live_workbench` as the only UI-producing tool and the legacy 69-action surface remaining test-only;
- the canonical CI gates pass on the release commit.

This policy prevents the split-repository drift that the Heidi monorepo was created to eliminate.
