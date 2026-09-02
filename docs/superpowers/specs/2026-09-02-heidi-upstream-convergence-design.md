# Heidi upstream convergence design

Date: 2026-09-02
Status: approved architecture — Option A (compact functional parity)

## Goal

Make `heidi-dang/heidi-cli` the canonical production release that contains the complete current functionality of both official upstream repositories while preserving Heidi-specific release, security, and compact-contract invariants.

Authoritative upstream revisions for this convergence:

- `heidi-dang/computer` `main`: `ae2996a672ad4b595617384b7c5ee8cced3e304d`
- `heidi-dang/chatgpt-computer-plugin` `main`: `70c3962e74a75bde2fd3beb1bfaea7ac0a73b517`
- Heidi integration base: `heidi-dang/heidi-cli` `main` at `b8ed3afdcae4d014eac6d53069478e44643f6ab0`, plus the already-verified local hybrid-benchmark release worktree changes.

The convergence target is **functional parity, not tool-name parity**. Heidi keeps a compact ChatGPT-facing contract and groups related official-plugin actions behind bounded read/control gateways where doing so preserves capability and safety.

## Existing findings

`computer/main` is already at the feature-source revision used by the hybrid benchmark work, but Heidi only ported a subset of the changes after its last full audited backend sync (`a4a3a02251312e5f5c04b910d1e11857323b0ab5`). Missing or incompletely ported areas include:

- live MCP console and tool-call UI;
- MCP traffic store, request topology, request outcome charts, session identity and aliases;
- MCP activity stream;
- MCP latency/failure diagnostics and backend system metrics;
- richer MCP token estimation and pricing diagnostics;
- full `/mcp` monitoring frontend and its regression tests;
- terminal runtime parity, interactive PTY controls, and LSP manager/API support;
- direct-coding/FDX runtime hardening and related tests;
- frontend Svelte 5, accessibility, production-build warning, and chunk-splitting improvements.

`chatgpt-computer-plugin/main` contains the complete telemetry/activity/diagnostics adapters, terminal parity controls, LSP actions, iPhone terminal improvements, benchmark actions, and the latest `70c3962` prompt-SSE status fix. Heidi already contains the prompt-SSE state logic and hybrid benchmark semantics, but does not expose all terminal/LSP capabilities through the compact production contract and does not yet include the full upstream telemetry delivery stack.

## Architecture

### 1. Canonical backend parity

Port the complete production-relevant `computer` delta from Heidi's last full audited sync through `ae2996a` into `apps/cptr`, adapting conflicts to Heidi's control-plane architecture rather than replacing Heidi-specific files wholesale.

Required backend capabilities:

- MCP traffic ingestion, bounded storage, streaming and topology state;
- MCP activity ingestion and streaming;
- diagnostics ingestion for latency, failures and usage;
- system metrics streaming;
- topology alias persistence;
- durable usage and hybrid benchmark persistence from migration `0018`;
- interactive command-session stdin, PTY resize and signals;
- LSP discovery/start/request/stop lifecycle;
- direct-coding and FDX runtime hardening;
- terminal parity behavior and tests.

Heidi-specific authorization, owner scoping, immutable release behavior, control-token profiles, direct-worker semantics, and existing control API hardening remain authoritative where upstream code conflicts.

### 2. MCP-v2 compact functional parity

Do **not** expose the official standalone plugin's full 80-action production surface.

Preserve Heidi's compact read/control architecture and add grouped gateways for missing capability families:

- `cptr_terminal_control`: bounded `send_input`, `resize`, and `signal` actions for an owned running command; command start/status/cancel remain in the existing compact code-command surfaces.
- `cptr_lsp_read`: `discover` and bounded `request` operations where read-only semantics are valid.
- `cptr_lsp_control`: `start` and `stop` lifecycle operations.

The benchmark remains a single `cptr_benchmark` gateway with `start|get|submit|leaderboard` actions rather than four public tools.

Telemetry/activity/diagnostics are adapter-internal delivery paths, not extra ChatGPT actions. Every compact action continues to accept bounded `client_model` attribution centrally, and `client_model` must never be forwarded as business authorization.

The exact final compact action count is derived from the canonical inventory in `apps/mcp/server/release.ts`; no duplicated hard-coded count is accepted outside compatibility assertions and release metadata.

### 3. Telemetry parity and privacy

Adopt the official plugin's correlated MCP telemetry architecture:

- request/session/correlation IDs;
- bounded traffic events;
- bounded activity events;
- latency/failure/usage diagnostics;
- session/model/workspace identity enrichment;
- queue limits, batching and failure isolation.

Durable Heidi usage persistence remains the accounting source for weekly/monthly/rolling/all-time totals.

Usage and traffic telemetry must not persist hidden reasoning. Durable usage records remain metadata/token-count only. Activity/diagnostic payloads must use the upstream bounded/redacted serializers and preserve credential/path redaction. Any UI-visible arguments/results remain bounded diagnostic projections, not an unrestricted transcript store.

Use the richer official `js-tiktoken` estimator when dependency and bundle gates pass; retain bounded byte fallback for unknown/current model IDs and oversized payloads. Pricing remains server-owned and historical rows retain the pricing snapshot used when recorded.

### 4. UI parity

Import/adapt the current `computer` MCP monitoring UI into Heidi's CPTR frontend so the bundled backend contains the same operational `/mcp` capabilities:

- live console;
- topology and server/request views;
- activity feed;
- backend/system diagnostics;
- latency/failure detail;
- request charts;
- token/simulated-cost charts;
- weekly/monthly durable usage summaries;
- standardized benchmark panel.

Preserve upstream mobile/iPhone behavior, Svelte 5/accessibility fixes, production build-warning gate, and runtime chunk splitting.

Heidi's separate ChatGPT Apps Workbench remains bounded. It keeps the current compact overview cards and live terminal/direct-worker UI rather than embedding the full administrative `/mcp` console into the ChatGPT widget.

Port `chatgpt-computer-plugin@70c3962` prompt-SSE status behavior and its regression test into the Heidi Workbench if any byte/logic delta remains after comparison.

### 5. Release and provenance

Update `docs/SOURCE_PROVENANCE.md` to record the exact two authoritative upstream SHAs above and describe adapted-vs-verbatim imports.

Bump the next Heidi version only after the convergence gates pass. `release/compatibility.json`, package versions, deployed-contract verifier, governance docs and update manifest must agree with the derived compact action inventory and one-resource/one-UI-producing-tool invariant.

Do not alter the single Apps resource invariant:

- exactly one Apps resource: `ui://cptr/live-workbench.html`;
- only `cptr_open_live_workbench` is UI-producing;
- Direct Coding remains the default execution mode;
- delegation still requires explicit `allow:delegate` authorization.

## Error handling and compatibility

- Telemetry delivery failure must never fail an otherwise successful MCP business call.
- Persistent analytics writes are idempotent by event ID.
- Unknown or unavailable model IDs remain valid telemetry with canonical model unset and fallback token estimation.
- LSP processes are workspace/worker scoped, owned, bounded, and shut down cleanly.
- PTY control operations require an existing owned command and reject non-PTY resize operations.
- Existing compact tool behavior must remain backward compatible except for the deliberate versioned addition of new grouped gateways.
- No production environment switch may expose the legacy standalone 80-action surface.

## Verification

Acceptance requires all of the following on the final integrated Heidi commit:

1. Upstream inventory audit proves every production capability introduced in `computer` from `a4a3a022` through `ae2996a` is either present verbatim or mapped to an explicitly documented Heidi equivalent.
2. Official plugin inventory audit proves every production capability through `70c3962` is present or mapped to a compact Heidi gateway; no unmatched action remains without a documented reason.
3. Full bundled CPTR Python suite passes.
4. CPTR frontend typecheck, format gate, production build, and MCP-specific frontend tests pass.
5. Full MCP/Workbench Node test suite, TypeScript typecheck and production build pass.
6. LSP lifecycle tests pass, including concurrent starts and cleanup.
7. Interactive PTY tests pass for stdin, resize and signal behavior.
8. Telemetry traffic/activity/diagnostics acceptance tests pass with bounded queues, redaction and correlated session identity.
9. Durable usage migration upgrade/downgrade and restart deduplication pass.
10. Hybrid standardized benchmark anti-tamper regression passes.
11. Root Heidi release/governance/compatibility tests pass.
12. Compatibility verifier derives the exact compact action count and confirms one Apps resource / one UI-producing tool.
13. Final Git diff contains no generated caches, dependency directories, credentials, nested repositories, or unrelated machine state.

## Definition of done

The convergence is complete only when a capability matrix shows **100% functional coverage** for both upstream SHAs, the complete Heidi monorepo gate is green, provenance is updated, and the final integration is committed on a clean branch based on current `heidi-cli/main`.

Publishing/tagging/deploying the resulting Heidi release is a separate release step unless explicitly included by the user after convergence verification.
