# Heidi Upstream Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make canonical `heidi-cli` functionally cover `computer@ae2996a672ad4b595617384b7c5ee8cced3e304d` and `chatgpt-computer-plugin@70c3962e74a75bde2fd3beb1bfaea7ac0a73b517` while retaining Heidi's compact read/control MCP safety architecture.

**Architecture:** Port production-relevant CPTR capabilities into `apps/cptr` by adapting upstream behavior to Heidi's owner-scoped control plane, then expose official-plugin-only terminal and LSP capability families through three compact MCP gateways instead of recreating the 80-action standalone surface. Preserve the existing single Apps resource, bounded Workbench, hybrid benchmark, durable usage accounting, and release provenance. A generated capability matrix is the acceptance artifact proving that every upstream production capability is present verbatim or mapped to an explicit Heidi equivalent.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy/Alembic, Svelte 5/Vite, TypeScript 5.9, React 18, official MCP SDK v2, Zod 4, Node 22, `js-tiktoken`, pytest, Node test runner, Ruff.

**Spec:** `docs/superpowers/specs/2026-09-02-heidi-upstream-convergence-design.md`

## Global Constraints

- Authoritative `computer/main`: `ae2996a672ad4b595617384b7c5ee8cced3e304d`.
- Authoritative `chatgpt-computer-plugin/main`: `70c3962e74a75bde2fd3beb1bfaea7ac0a73b517`.
- Functional parity is required; name-for-name 80-action parity is explicitly not required.
- Production must keep exactly one Apps resource at `ui://cptr/live-workbench.html` and only `cptr_open_live_workbench` may be UI-producing.
- Direct Coding remains the default execution path; delegation still requires explicit `allow:delegate` authorization.
- MCP telemetry delivery failure must never fail an otherwise successful business call.
- Durable MCP usage remains metadata/token-count only and must never store hidden reasoning, unrestricted prompts, source files, tool arguments, or raw tool results.
- All new command/LSP operations remain workspace-owner scoped and bounded by existing CPTR authorization.
- No production environment switch may expose the standalone 80-action contract.
- Repository release/version changes occur only after functional convergence and complete gates are green.

---

### Task 1: Establish executable upstream capability matrix

**Files:**
- Create: `scripts/audit-upstream-parity.py`
- Create: `tests/test_upstream_parity.py`
- Modify: `docs/SOURCE_PROVENANCE.md`

**Interfaces:**
- Consumes: exact upstream SHAs from this plan's Global Constraints.
- Produces: `audit_parity(root: Path) -> dict[str, object]` with `computer`, `plugin`, `unmapped`, and `coverage_percent`; a CLI that exits non-zero when any required capability is unmapped.

- [ ] **Step 1: Write failing parity-verifier unit tests**

Create tests that load the audit module, assert the authoritative SHA constants and required capability IDs are source-controlled, and exercise `audit_capabilities(root, capabilities)` against a temporary fixture containing one present evidence path and one missing path:

```python
REQUIRED = {
    "computer:mcp_traffic",
    "computer:mcp_activity",
    "computer:mcp_diagnostics",
    "computer:system_metrics",
    "computer:mcp_topology_ui",
    "computer:lsp_manager",
    "computer:interactive_pty",
    "computer:direct_coding_runtime_hardening",
    "computer:hybrid_benchmark",
    "plugin:mcp_traffic_delivery",
    "plugin:mcp_activity_delivery",
    "plugin:mcp_diagnostics_delivery",
    "plugin:interactive_pty_controls",
    "plugin:lsp_controls",
    "plugin:iphone_terminal",
    "plugin:hybrid_benchmark",
    "plugin:prompt_sse_status",
}


def test_audit_capabilities_reports_missing_evidence(tmp_path):
    (tmp_path / "present.txt").write_text("ok", encoding="utf-8")
    result = audit_capabilities(tmp_path, [
        capability("present", "computer", COMPUTER_SHA, "source", ["present.txt"], "adapted"),
        capability("missing", "plugin", PLUGIN_SHA, "source", ["missing.txt"], "compact-gateway"),
    ])
    assert result["coverage_percent"] == 50.0
    assert result["unmapped"] == ["missing"]
```

The repository-wide `audit_parity(ROOT) == 100%` assertion is intentionally deferred to Task 8 after all evidence paths exist.

- [ ] **Step 2: Run the parity test and verify RED**

Run:

```bash
python -m pytest -q tests/test_upstream_parity.py
```

Expected: FAIL because `audit-upstream-parity.py` does not yet exist.

- [ ] **Step 3: Implement a source-controlled capability manifest and verifier**

Use a literal mapping table in `scripts/audit-upstream-parity.py`. Each capability entry contains `upstream`, `source_sha`, `source_evidence`, `heidi_evidence`, and `mapping`. The verifier checks that every `heidi_evidence` path exists and that source SHAs equal the two authoritative revisions. Do not shell out to GitHub at verification time.

- [ ] **Step 4: Record exact provenance**

Update `docs/SOURCE_PROVENANCE.md` so the latest audited source entries are exactly `ae2996a672ad...` and `70c3962e74a...`, and state whether each family is verbatim, adapted, or compact-gateway mapped.

- [ ] **Step 5: Run the parity-verifier unit tests GREEN**

Run:

```bash
python -m pytest -q tests/test_upstream_parity.py
```

Expected: PASS for SHA/capability-manifest structure and temporary-root verifier behavior. Task 8 adds the final repository-wide assertion requiring `audit_parity(ROOT)` to report 100% coverage.

- [ ] **Step 6: Commit the parity framework**

```bash
git add scripts/audit-upstream-parity.py tests/test_upstream_parity.py docs/SOURCE_PROVENANCE.md
git commit -m "test: define upstream parity contract"
```

---

### Task 2: Port CPTR MCP traffic, activity, diagnostics, and system metrics backend

**Files:**
- Create/adapt: `apps/cptr/cptr/services/mcp_traffic.py`
- Create/adapt: `apps/cptr/cptr/services/mcp_activity.py`
- Create/adapt: `apps/cptr/cptr/services/mcp_diagnostics.py`
- Create/adapt: `apps/cptr/cptr/services/mcp_topology_config.py`
- Create/adapt: `apps/cptr/cptr/services/system_metrics.py`
- Modify: `apps/cptr/cptr/app.py`
- Modify: `apps/cptr/cptr/routers/mcp.py`
- Modify: `apps/cptr/cptr/routers/gateway.py`
- Test/create/adapt: `apps/cptr/tests/test_mcp_traffic.py`
- Test/create/adapt: `apps/cptr/tests/test_mcp_traffic_api.py`
- Test/create/adapt: `apps/cptr/tests/test_mcp_activity.py`
- Test/create/adapt: `apps/cptr/tests/test_mcp_activity_api.py`
- Test/create/adapt: `apps/cptr/tests/test_mcp_diagnostics.py`
- Test/create/adapt: `apps/cptr/tests/test_mcp_diagnostics_api.py`
- Test/create/adapt: `apps/cptr/tests/test_mcp_topology_config.py`
- Test/create/adapt: `apps/cptr/tests/test_system_metrics.py`

**Interfaces:**
- Consumes: existing Heidi authentication/user/workspace services and durable `McpUsageStore` from the hybrid benchmark work.
- Produces: bounded in-process stores and authenticated ingestion/snapshot/stream routes compatible with the official plugin telemetry emitters.

- [ ] **Step 1: Port upstream tests first**

Copy/adapt the upstream test behavior for bounded queue sizes, active-request caps, subscriber cleanup, sanitized failures, topology aliases, and system metrics. Keep Heidi's owner-scope fixtures and auth dependencies.

- [ ] **Step 2: Run focused tests RED**

Run:

```bash
python -m pytest -q \
  apps/cptr/tests/test_mcp_traffic.py \
  apps/cptr/tests/test_mcp_traffic_api.py \
  apps/cptr/tests/test_mcp_activity.py \
  apps/cptr/tests/test_mcp_activity_api.py \
  apps/cptr/tests/test_mcp_diagnostics.py \
  apps/cptr/tests/test_mcp_diagnostics_api.py \
  apps/cptr/tests/test_mcp_topology_config.py \
  apps/cptr/tests/test_system_metrics.py
```

Expected: FAIL on missing services/routes.

- [ ] **Step 3: Port bounded stores without weakening Heidi auth**

Adopt upstream bounded event dataclasses/deques and subscriber fanout. Keep route dependencies on Heidi's current-user/control-key ownership boundary. Traffic/activity/diagnostics ingestion accepts only allowlisted event fields and never trusts client-provided authorization identity.

- [ ] **Step 4: Integrate diagnostics usage with durable accounting**

When a usage diagnostic is accepted, project pricing using the existing server-owned registry and persist through `McpUsageStore` using event-ID dedupe. Preserve the in-memory short-window stream for live charts while database periods remain authoritative for weekly/monthly/all-time totals.

- [ ] **Step 5: Run focused tests GREEN**

Use the command from Step 2. Expected: all pass.

- [ ] **Step 6: Commit backend telemetry parity**

```bash
git add apps/cptr/cptr apps/cptr/tests
git commit -m "feat: converge CPTR MCP telemetry backend"
```

---

### Task 3: Port direct-coding runtime hardening, interactive PTY, and LSP backend

**Files:**
- Create/adapt: `apps/cptr/cptr/services/lsp_manager.py`
- Modify: `apps/cptr/cptr/routers/coding.py`
- Modify: `apps/cptr/cptr/services/fdx_intelligence.py`
- Modify: `apps/cptr/cptr/services/live_events.py`
- Modify: `apps/cptr/cptr/utils/runtime.py`
- Modify: `apps/cptr/cptr/utils/tools.py`
- Test/adapt: `apps/cptr/tests/test_direct_coding.py`
- Test/adapt: `apps/cptr/tests/test_backend_performance.py`
- Test/adapt: `apps/cptr/tests/test_fdx_intelligence.py`
- Test/adapt: `apps/cptr/tests/test_live_events.py`
- Create/adapt: `apps/cptr/tests/test_terminal_parity.py`

**Interfaces:**
- Consumes: existing `CommandSession`/workspace authorization and model-free Direct Worker resolution.
- Produces: `send_input`, `resize`, `signal` command endpoints and workspace/worker-scoped LSP discover/start/request/stop lifecycle.

- [ ] **Step 1: Port terminal/LSP regression tests first**

Tests must cover:

```python
async def test_pty_accepts_stdin_and_reports_incremental_output(...): ...
async def test_resize_rejects_non_pty_command(...): ...
async def test_interrupt_targets_owned_process_tree(...): ...
async def test_lsp_concurrent_start_reuses_or_serializes_server(...): ...
async def test_lsp_worker_scope_cannot_escape_worktree(...): ...
async def test_lsp_stop_is_idempotent_and_cleans_process(...): ...
```

- [ ] **Step 2: Run terminal/LSP tests RED**

```bash
python -m pytest -q apps/cptr/tests/test_terminal_parity.py apps/cptr/tests/test_direct_coding.py apps/cptr/tests/test_live_events.py
```

Expected: missing LSP/interactive command behavior fails.

- [ ] **Step 3: Port upstream runtime behavior**

Adopt the official `computer@ae2996a` LSP manager and terminal parity behavior. Preserve Heidi's worker-path resolution, command policy, owner scoping, output bounds, and process-tree cleanup. LSP server definitions remain administrator-configured; project code must not select arbitrary executables.

- [ ] **Step 4: Port direct-coding/FDX performance hardening**

Apply `57dac6b` behavior for bounded runtime reads, non-PTY execution efficiency, resident FDX routing, and associated fallbacks without regressing Heidi-specific API shape.

- [ ] **Step 5: Run focused backend tests GREEN**

```bash
python -m pytest -q \
  apps/cptr/tests/test_terminal_parity.py \
  apps/cptr/tests/test_direct_coding.py \
  apps/cptr/tests/test_backend_performance.py \
  apps/cptr/tests/test_fdx_intelligence.py \
  apps/cptr/tests/test_live_events.py
```

Expected: all pass.

- [ ] **Step 6: Commit runtime parity**

```bash
git add apps/cptr/cptr apps/cptr/tests
git commit -m "feat: converge terminal and LSP runtime"
```

---

### Task 4: Port the complete CPTR `/mcp` monitoring frontend and upstream frontend hardening

**Files:**
- Modify: `apps/cptr/cptr/frontend/package.json`
- Modify: `apps/cptr/cptr/frontend/package-lock.json`
- Create/adapt: `apps/cptr/cptr/frontend/scripts/check-production-build.mjs`
- Create/adapt: `apps/cptr/cptr/frontend/src/lib/apis/mcp.ts`
- Create/adapt: `apps/cptr/cptr/frontend/src/lib/stores/mcp-traffic.ts`
- Create/adapt: `apps/cptr/cptr/frontend/src/lib/stores/mcp-activity.ts`
- Create/adapt: `apps/cptr/cptr/frontend/src/lib/stores/mcp-diagnostics.ts`
- Create/adapt: `apps/cptr/cptr/frontend/src/lib/stores/mcp-topology.ts`
- Create/adapt: `apps/cptr/cptr/frontend/src/lib/utils/mcp-console.ts`
- Create/adapt: `apps/cptr/cptr/frontend/src/lib/components/mcp/*.svelte`
- Create/adapt: `apps/cptr/cptr/frontend/src/routes/mcp/+page.svelte`
- Modify/adapt: Svelte/accessibility/chunk-splitting files changed by `c5f9ff4`, `3624cae`, `eb0b366`, and `e28dec1`
- Create/adapt tests: `apps/cptr/cptr/frontend/tests/mcp-console-functions.test.mjs`
- Create/adapt tests: `apps/cptr/cptr/frontend/tests/mcp-traffic-topology.test.mjs`

**Interfaces:**
- Consumes: Task 2 telemetry APIs and existing durable weekly/monthly usage/benchmark APIs.
- Produces: operational `/mcp` console with traffic, activity, topology, diagnostics, system metrics, token/cost and benchmark views.

- [ ] **Step 1: Port frontend regression tests first**

Keep official expectations for bounded reducers, request lifecycle, topology aliases, chart bucketing, mobile behavior, and warning-free production build. Add Heidi assertions that weekly/monthly cards source durable aggregate fields and benchmark results remain separated from observed real-work metrics.

- [ ] **Step 2: Run MCP frontend tests RED**

```bash
node --test \
  apps/cptr/cptr/frontend/tests/mcp-console-functions.test.mjs \
  apps/cptr/cptr/frontend/tests/mcp-traffic-topology.test.mjs
```

Expected: missing modules/components fail.

- [ ] **Step 3: Port MCP UI modules and reducers**

Bring the upstream `/mcp` route and component family into Heidi. Preserve Svelte 5 conventions and use the existing server endpoints rather than duplicating analytics logic in the browser.

- [ ] **Step 4: Port frontend quality/performance fixes**

Adapt upstream Svelte 5 migration, form/interaction accessibility fixes, production warning checker, and Vite heavy-runtime chunk splitting. Do not mass-format unrelated files beyond the specific upstream-changed set.

- [ ] **Step 5: Run frontend tests/check/build GREEN**

```bash
node --test apps/cptr/cptr/frontend/tests/*.test.mjs
npm --prefix apps/cptr/cptr/frontend run check
npm --prefix apps/cptr/cptr/frontend run format:check:frontend
npm --prefix apps/cptr/cptr/frontend run build
```

Expected: all pass and production warning checker reports no forbidden warnings.

- [ ] **Step 6: Commit CPTR frontend parity**

```bash
git add apps/cptr/cptr/frontend
git commit -m "feat: converge CPTR MCP monitoring UI"
```

---

### Task 5: Port official plugin telemetry emitters and richer token estimation into Heidi MCP-v2

**Files:**
- Create/adapt: `apps/mcp/server/mcp-traffic.ts`
- Create/adapt: `apps/mcp/server/mcp-activity.ts`
- Create/adapt: `apps/mcp/server/mcp-diagnostics.ts`
- Modify: `apps/mcp/server/mcp-usage.ts`
- Modify: `apps/mcp/server/client/computer-client.ts`
- Modify: `apps/mcp/server/mcp.ts`
- Modify: `apps/mcp/server/index.ts`
- Modify: `apps/mcp/package.json`
- Modify: `apps/mcp/package-lock.json`
- Test/create/adapt: `apps/mcp/tests/mcp-traffic.test.ts`
- Test/create/adapt: `apps/mcp/tests/mcp-activity.test.ts`
- Test/create/adapt: `apps/mcp/tests/mcp-diagnostics.test.ts`
- Test/create/adapt: `apps/mcp/tests/mcp-usage.test.ts`

**Interfaces:**
- Consumes: Task 2 CPTR ingestion routes.
- Produces: correlated bounded request/session/tool telemetry and richer `estimateModelTokens(modelId, text)` using `js-tiktoken` with byte fallback.

- [ ] **Step 1: Port emitter/estimator tests RED**

Tests must assert queue limits, batch flushing, correlation IDs, session enrichment, redaction, exact-model tokenization when available, fallback for unknown model IDs, fallback for oversized payloads, and that emitter failure does not alter tool success.

- [ ] **Step 2: Run focused Node tests RED**

```bash
node --test \
  apps/mcp/tests/mcp-traffic.test.ts \
  apps/mcp/tests/mcp-activity.test.ts \
  apps/mcp/tests/mcp-diagnostics.test.ts \
  apps/mcp/tests/mcp-usage.test.ts
```

Expected: missing emitters / richer estimator fail.

- [ ] **Step 3: Add `js-tiktoken` and port bounded estimator**

Use the official plugin implementation: exact encoding when the library maps the model, `o200k_base` fallback for unknown model IDs, and UTF-8 byte fallback when payload size exceeds `CPTR_MCP_USAGE_MAX_EXACT_BYTES` or encoding is unavailable. Keep `client_model` sanitization centralized.

- [ ] **Step 4: Port traffic/activity/diagnostics emitters and request context**

Use `AsyncLocalStorage` for request/correlation/session metadata. Batch delivery to CPTR through `ComputerClient`. Emit only bounded allowlisted traffic/diagnostic fields; activity projections follow upstream redaction/bounds. Delivery exceptions are logged/bounded and never replace the business result.

- [ ] **Step 5: Run focused tests GREEN**

Use the command from Step 2. Expected: all pass.

- [ ] **Step 6: Commit MCP telemetry parity**

```bash
git add apps/mcp
git commit -m "feat: converge MCP telemetry delivery"
```

---

### Task 6: Add compact terminal-control and LSP gateways

**Files:**
- Modify: `apps/mcp/server/schemas/gateways.ts`
- Modify: `apps/mcp/server/schemas/outputs.ts`
- Modify: `apps/mcp/server/compact-gateways.ts`
- Modify: `apps/mcp/server/client/computer-client.ts`
- Modify: `apps/mcp/server/release.ts`
- Modify: `apps/mcp/scripts/check-deployed-contract.mjs`
- Modify: `apps/mcp/tests/compact-contract.test.ts`
- Create: `apps/mcp/tests/terminal-lsp-gateways.test.ts`

**Interfaces:**
- Consumes: Task 3 CPTR endpoints.
- Produces:
  - `cptr_terminal_control` with actions `send_input | resize | signal`.
  - `cptr_lsp_read` with actions `discover | request`.
  - `cptr_lsp_control` with actions `start | stop`.

- [ ] **Step 1: Write compact contract tests RED**

Tests assert the three new names appear exactly once in `MCP_COMPACT_TOOL_NAMES`, the legacy standalone action names are not production-registered, and safety annotations are:

```text
cptr_terminal_control  readOnly=false destructive=true  openWorld=false
cptr_lsp_read          readOnly=true  destructive=false openWorld=false
cptr_lsp_control       readOnly=false destructive=true  openWorld=false
```

Also assert every action schema accepts centrally injected `client_model` but `ComputerClient` business payloads never receive it.

- [ ] **Step 2: Run compact tests RED**

```bash
node --test apps/mcp/tests/compact-contract.test.ts apps/mcp/tests/terminal-lsp-gateways.test.ts
```

Expected: missing gateway/schema/client methods fail.

- [ ] **Step 3: Add bounded schemas and client methods**

`terminal_control` requires `workspace_id`, `command_id`, and action-specific fields. `lsp_read.request` requires `lsp_id`, `method`, optional bounded `params`, and `timeout_seconds`; `lsp_control.start` requires administrator-configured `server_id` plus optional relative root; `stop` requires `lsp_id`.

- [ ] **Step 4: Register the three compact gateways**

Keep all registration in `compact-gateways.ts`; derive contract count from `MCP_COMPACT_TOOL_NAMES.length`. Do not add a legacy profile or environment switch.

- [ ] **Step 5: Run compact tests GREEN**

Use Step 2 command. Expected: all pass.

- [ ] **Step 6: Commit compact parity gateways**

```bash
git add apps/mcp
git commit -m "feat: expose compact terminal and LSP parity"
```

---

### Task 7: Port latest official Workbench prompt-SSE behavior and verify iPhone terminal parity

**Files:**
- Modify only if delta remains: `apps/mcp/web/src/workbench.tsx`
- Modify only if delta remains: `apps/mcp/tests/terminal-view.test.ts`
- Verify: `apps/mcp/web/src/terminal-view.tsx`
- Verify: `apps/mcp/web/src/workbench.css`

**Interfaces:**
- Consumes: official plugin behavior at `70c3962`.
- Produces: prompt-level SSE connection status that shows `CPTR Computer` only after prompt SSE is live, while retaining Heidi direct-worker/overview additions.

- [ ] **Step 1: Write/port the `70c3962` regression assertions**

Assert:

```ts
assert.match(source, /const promptConnection = usePromptActivity\(/);
assert.match(source, /promptConnection === "prompt live"/);
assert.doesNotMatch(source, /meta\?\.targetId \? targetConnection : "connecting terminal session"/);
```

Adapt the expected connection expression to Heidi's worker-aware branch.

- [ ] **Step 2: Run terminal-view test RED or confirm already GREEN**

```bash
node --test apps/mcp/tests/terminal-view.test.ts
```

If already GREEN, record the capability as already converged and make no product-code edit.

- [ ] **Step 3: Verify iPhone terminal constraints**

Tests must retain 600 desktop rows, 320 mobile rows, requestAnimationFrame follow scrolling, bounded 220–280px mobile shell, 210px narrow minimum, contained overscroll, and host intrinsic-height reporting.

- [ ] **Step 4: Commit only if a code/test delta was required**

```bash
git add apps/mcp/web/src/workbench.tsx apps/mcp/tests/terminal-view.test.ts
git commit -m "fix: converge latest prompt SSE status"
```

---

### Task 8: Close parity matrix and run complete monorepo gates

**Files:**
- Modify: `scripts/audit-upstream-parity.py`
- Modify: `tests/test_upstream_parity.py`
- Modify as required: root governance/release docs only after all product tests are green.

**Interfaces:**
- Consumes: Tasks 2–7.
- Produces: machine-verifiable `100.0%` capability coverage and complete repository gates.

- [ ] **Step 1: Finalize every parity evidence path**

Run:

```bash
python scripts/audit-upstream-parity.py
```

Expected output includes both exact SHAs, zero unmapped capabilities, and `coverage_percent=100.0`.

- [ ] **Step 2: Run complete CPTR backend gate**

```bash
python -m pytest apps/cptr/tests
ruff check apps/cptr/cptr apps/cptr/tests
```

Expected: all tests and lint pass.

- [ ] **Step 3: Run complete CPTR frontend gate**

```bash
npm --prefix apps/cptr/cptr/frontend run check
npm --prefix apps/cptr/cptr/frontend run format:check:frontend
npm --prefix apps/cptr/cptr/frontend run build
node --test apps/cptr/cptr/frontend/tests/*.test.mjs
```

Expected: all pass.

- [ ] **Step 4: Run complete MCP/Workbench gate**

```bash
npm --prefix apps/mcp test
npm --prefix apps/mcp run typecheck
npm --prefix apps/mcp run build
```

Expected: all pass.

- [ ] **Step 5: Verify migration round trip**

Create a temporary SQLite database, run Alembic upgrade to head, downgrade to `0017`, and upgrade to head again. Expected: all three operations succeed and `0018` creates the usage/benchmark tables exactly once.

- [ ] **Step 6: Run root release/governance/compatibility gate**

```bash
python -m pytest -q tests
python scripts/verify-compatibility.py
bash -n install.sh scripts/install-core.sh scripts/install-lib.sh scripts/verify-stack.sh bin/heidi
```

Expected: all pass; compatibility tool count matches the canonical inventory automatically.

- [ ] **Step 7: Audit repository hygiene**

Verify Git status contains no `node_modules`, `dist` artifacts unless explicitly tracked by release design, `.env`, local DBs, caches, nested `.git`, credentials, or machine state.

- [ ] **Step 8: Commit convergence closure**

```bash
git add scripts tests docs apps release package.json
git commit -m "feat: converge Heidi with official CPTR upstreams"
```

---

### Task 9: Version the converged Heidi contract after all gates are green

**Files:**
- Modify: `package.json`
- Modify: `apps/mcp/package.json`
- Modify: `apps/mcp/package-lock.json`
- Modify: `apps/mcp/server/release.ts`
- Modify: `release/compatibility.json`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `apps/mcp/README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/DEPLOYMENT.md`
- Modify: `docs/REPOSITORY_GOVERNANCE.md`
- Modify: `scripts/verify-stack.sh`
- Modify: release/governance tests that assert the exact compact count.

**Interfaces:**
- Consumes: derived final compact tool count from Task 6 and complete green gates from Task 8.
- Produces: one coherent Heidi release identity describing the convergence.

- [ ] **Step 1: Determine the next unused semantic version**

Inspect local/remote tags and GitHub release metadata. Do not overwrite an immutable existing release. Use the next patch version after the highest published stable release.

- [ ] **Step 2: Update canonical version fields and release notes**

All package/compatibility versions must match. The release note must identify the two exact upstream SHAs and state that functional parity is delivered through the compact contract.

- [ ] **Step 3: Update count/invariant assertions from the derived inventory**

Update only deliberate compatibility assertions; runtime count continues to derive from `MCP_COMPACT_TOOL_NAMES.length`.

- [ ] **Step 4: Re-run root + MCP release gates**

```bash
python scripts/verify-compatibility.py
python -m pytest -q tests
npm --prefix apps/mcp test
npm --prefix apps/mcp run typecheck
npm --prefix apps/mcp run build
```

Expected: all pass with one resource and one UI-producing tool.

- [ ] **Step 5: Commit release metadata**

```bash
git add package.json apps/mcp release AGENTS.md README.md docs scripts tests
git commit -m "chore: version converged Heidi release"
```

## Final Acceptance

The implementation is complete only when:

```text
computer upstream coverage: 100%
plugin upstream coverage:   100%
unmapped capabilities:      0
CPTR backend tests:          PASS
CPTR frontend check/build:   PASS
MCP tests/typecheck/build:   PASS
migration round-trip:        PASS
root compatibility/release: PASS
Apps resources:              1
UI-producing tools:          1
legacy 80-action profile:    unavailable in production
```

Publishing/tagging/deploying the resulting signed release remains a separate release action unless the user explicitly requests it after convergence verification.
