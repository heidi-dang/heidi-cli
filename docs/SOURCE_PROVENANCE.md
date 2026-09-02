# Source provenance

Initial monorepo import date: 2026-08-28.

## MCP adapter

- Source repository: `heidi-dang/chatgpt-computer-plugin`
- Baseline branch: `main`
- Baseline commit: `7020475e6afc40e0a7c26710bdb20c19d838d9d6`
- Latest audited feature source: `70c3962e74a75bde2fd3beb1bfaea7ac0a73b517` (`main`, 2026-09-02)
- Imported path: `apps/mcp`

Tracked working-tree changes present at consolidation time were intentionally included because they were part of the current CPTR Computer contract work. Generated `.fdx` and audit directories were excluded. The 2026-09-02 audited source through `70c3962` includes correlated MCP traffic/activity/diagnostics delivery, MCP-visible token estimation, ChatGPT session identity, interactive PTY controls, LSP controls, iPhone terminal hardening, the standardized benchmark lifecycle, and the latest prompt-SSE status fix. Heidi ports shared transport/runtime behavior and maps benchmark, terminal, and LSP action families into the canonical MCP v2 compact gateways rather than copying the standalone 80-action contract.

## CPTR backend

- Source repository: `heidi-dang/computer`
- Baseline branch: `main`
- Baseline commit: `db9377e38dc33c5efa47030d41f0cc27eba583d9`
- Latest audited sync commit: `a4a3a02251312e5f5c04b910d1e11857323b0ab5` (`main`, 2026-08-31)
- Latest audited feature source: `ae2996a672ad4b595617384b7c5ee8cced3e304d` (`main`, 2026-09-02)
- Imported path: `apps/cptr`

The import intentionally includes the verified direct-coding performance changes that were still in the tracked working tree at consolidation time: bounded single/batch runtime file reads, non-PTY Direct Coding command execution, resident FDX read routing, and their regression/performance tests. The 2026-08-31 audited sync imports the upstream CPTR UI polish, bulk model controls/search, and the 55-endpoint extended API surface while preserving Heidi-specific lifecycle, execution-policy, FDX, and control-plane additions. The 2026-09-02 convergence source through `ae2996a` additionally covers the complete MCP console/traffic/activity/topology/diagnostics/system-metrics stack, Svelte/accessibility/build/chunk hardening, terminal/LSP runtime parity, direct-coding/FDX hardening, migration 0018 durable usage/accounting, and the owner-scoped anti-tamper hybrid benchmark. Heidi adapts those families to its existing authorization, control/UI overview, immutable-release, and compact MCP boundaries.

## FDX

- Source repository: `heidi-dang/flowdeck`
- Baseline branch: `feat/heidi-fdx-vci-integration`
- Baseline commit: `ea0df02c5c9dc9cc0676ec70e7fc7ded2e7e82d5`
- Imported paths: root Cargo workspace files plus `crates/fdx`

Only the complete native FDX crate and its Rust workspace lock/manifest were imported. FlowDeck agents, orchestration, application runtime, planning database, and other unrelated packages were intentionally excluded.

Tracked FDX working-tree fixes present at consolidation time were included, including structured resident-daemon reads and the associated native tests.

## Import rule

Files were selected from each source repository's tracked file list, then copied from the current working tree. This preserves intentional tracked modifications without importing `node_modules`, build artifacts, caches, local databases, FDX indexes, environment files, nested `.git` directories, or other untracked machine state.
