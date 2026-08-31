# Reusable Managed OAuth Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one reusable confidential OAuth client for Heidi's Cloudflare Access Managed OAuth MCP deployment while keeping DCR and the tool-only MCP contract unchanged.

**Architecture:** Add a standalone Python lifecycle helper that registers/reuses/rotates a confidential client through the authorization server's advertised DCR endpoint and persists credentials in an owner-only JSON file. Wire it into the installer after Cloudflare Access provisioning, expose only non-secret state, and verify credential-file integrity without leaking secrets.

**Tech Stack:** Python 3.12 stdlib, Bash installer/verification scripts, Cloudflare Access Managed OAuth/DCR, pytest.

**Spec:** `docs/superpowers/specs/2026-08-31-global-managed-oauth-client-design.md`

## Global Constraints

- Preserve Cloudflare Managed OAuth DCR for ChatGPT and other DCR-capable clients.
- Preserve Heidi's tool-only MCP contract; do not add MCP resources or `ui.resourceUri` metadata.
- Never emit or commit the OAuth client secret or registration access token.
- Store reusable credentials only in an owner-only `0600` JSON file under Heidi's config directory.
- Reuse matching credentials idempotently; fail closed on configuration drift.
- Rotate only when the old registration can be deleted through stored RFC 7592 management credentials.

---

### Task 1: Reusable OAuth client lifecycle helper

**Files:**
- Create: `scripts/managed-oauth-client.py`
- Create: `tests/test_managed_oauth_client.py`

**Interfaces:**
- Consumes: OAuth authorization-server metadata URL, resource URL, credential file path, client name, redirect URIs, token endpoint auth method, rotate flag.
- Produces: owner-only JSON registration file and redacted stdout JSON containing `action`, `client_id`, `credentials_file`, `redirect_uris`.

- [ ] **Step 1: Write failing lifecycle tests**

Cover creation, mode `0600`, secret-redacted output, idempotent reuse, mismatch failure, managed rotation, and rotation refusal without management credentials using a local `ThreadingHTTPServer`.

- [ ] **Step 2: Run the helper tests and verify RED**

Run: `python3 -m pytest -q tests/test_managed_oauth_client.py`

Expected: FAIL because `scripts/managed-oauth-client.py` does not exist.

- [ ] **Step 3: Implement the minimal helper**

Implement argument parsing, metadata discovery, URL validation, registration POST, optional RFC 7592 deletion, normalized contract comparison, atomic `0600` persistence, and redacted result output using Python stdlib only.

- [ ] **Step 4: Run the helper tests and verify GREEN**

Run: `python3 -m pytest -q tests/test_managed_oauth_client.py`

Expected: all helper tests PASS.

### Task 2: Installer integration and state separation

**Files:**
- Modify: `scripts/install-core.sh`
- Modify: `tests/test_installer_contract.py`

**Interfaces:**
- Consumes: `MCP_OAUTH_REDIRECT_URIS`, `HEIDI_MCP_OAUTH_GLOBAL_CLIENT`, `HEIDI_MCP_OAUTH_GLOBAL_CLIENT_ROTATE`.
- Produces: `$CONFIG_DIR/oauth-client.json`, `HEIDI_MCP_OAUTH_CLIENT_ID`, and `HEIDI_MCP_OAUTH_CLIENT_FILE` in `state.env`; no secret in `state.env` or `mcp.env`.

- [ ] **Step 1: Add failing installer contract assertions**

Assert the installer invokes `managed-oauth-client.py`, keeps the built-in Claude callback in the shared redirect allowlist, supports opt-out/rotation flags, records only client ID/file path in state, and never writes `MCP_OAUTH_CLIENT_SECRET` or equivalent into runtime/state env files.

- [ ] **Step 2: Run installer contract tests and verify RED**

Run: `python3 -m pytest -q tests/test_installer_contract.py`

Expected: new assertions FAIL against the current installer.

- [ ] **Step 3: Implement installer wiring**

Build a normalized redirect array, pass every redirect to `cloudflare-provision.py`, invoke the helper after auth-domain discovery, parse only its non-secret result, and persist only client ID/path in state.

- [ ] **Step 4: Run installer tests and verify GREEN**

Run: `python3 -m pytest -q tests/test_installer_contract.py tests/test_cloudflare_provision.py`

Expected: PASS.

### Task 3: Verification, docs, and CI registration

**Files:**
- Modify: `scripts/verify-stack.sh`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `docs/SECURITY.md`
- Modify: `docs/DEPLOYMENT.md`
- Modify: `tests/test_installer_contract.py`

**Interfaces:**
- Consumes: state metadata and owner-only credential file.
- Produces: non-secret verification result and operator documentation for manual OAuth credentials.

- [ ] **Step 1: Add failing verification/build contract assertions**

Assert CI syntax-checks the new helper, executable contracts include it, verifier checks credential file permissions/content without printing secrets, and documentation identifies the owner-only credential location plus opt-out/rotation behavior.

- [ ] **Step 2: Run contract tests and verify RED**

Run: `python3 -m pytest -q tests/test_installer_contract.py`

Expected: new verification/documentation assertions FAIL.

- [ ] **Step 3: Implement verification and documentation**

Add non-secret credential-file verification, include the helper in Python syntax/executable CI checks, and document how reusable credentials coexist with DCR and which clients may safely use the secret.

- [ ] **Step 4: Run full installer suite and compatibility checks**

Run: `python3 -m pytest -q tests`

Run: `python3 scripts/verify-compatibility.py`

Run: `bash -n install.sh scripts/install-core.sh scripts/install-lib.sh scripts/install-split-backend.sh scripts/install-split-mcp.sh scripts/verify-stack.sh bin/heidi`

Expected: all PASS.

### Task 4: Regression gate and integration

**Files:**
- Review only: MCP contract and all changed files.

- [ ] **Step 1: Run full CI through the pull request**

Expected jobs: installer, mcp, cptr, fdx all PASS.

- [ ] **Step 2: Review the PR diff for secret leakage and host-classification regressions**

Confirm no client secret literals, no MCP resources, no `ui.resourceUri`, no changes to `apps/mcp/server/mcp.ts` or compact tool metadata unless strictly test-only and required.

- [ ] **Step 3: Merge only after green CI**

Use the repository's normal merge policy. Deployment is a separate operational step because creation of the live reusable client requires the production Cloudflare/VM path and must be verified against the live Managed OAuth issuer.
