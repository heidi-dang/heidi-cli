# Source provenance

Initial monorepo import date: 2026-08-28.

## MCP adapter

- Source repository: `heidi-dang/chatgpt-computer-plugin`
- Baseline branch: `main`
- Baseline commit: `7020475e6afc40e0a7c26710bdb20c19d838d9d6`
- Latest audited feature source: `2133a5d3d5d4d0ee7e0915eb2013bd13a7633948` (`main`, 2026-09-03)
- Imported path: `apps/mcp`

Tracked working-tree changes present at consolidation time were intentionally included because they were part of the current CPTR Computer contract work. Generated `.fdx` and audit directories were excluded. The 2026-09-03 audited source through `2133a5d` additionally includes the paired-user-Chrome adapter, one-time evaluate approval routing, browser-frame/human-input gateway support, persistent Live Computer surface behavior, and browser-input telemetry redaction. Heidi deliberately ports those capabilities into the existing `cptr_chrome_read` / `cptr_chrome_control` compact gateways with `target=user`; it does not copy the standalone expanded action surface and therefore preserves the signed 30-tool production contract.

## CPTR backend

- Source repository: `heidi-dang/computer`
- Baseline branch: `main`
- Baseline commit: `db9377e38dc33c5efa47030d41f0cc27eba583d9`
- Latest audited sync commit: `a4a3a02251312e5f5c04b910d1e11857323b0ab5` (`main`, 2026-08-31)
- Latest audited feature source: `70ea95c047a61865ec64b12039d80941741fef80` (`main`, 2026-09-03)
- Imported path: `apps/cptr`

The import intentionally includes the verified direct-coding performance changes that were still in the tracked working tree at consolidation time: bounded single/batch runtime file reads, non-PTY Direct Coding command execution, resident FDX read routing, and their regression/performance tests. The 2026-09-03 convergence source through `70ea95c` adds migration 0019 and the authoritative paired-browser device broker: hashed device credentials and pairing secrets, durable device/session/lease/replay records, control and visual WebSockets, bounded frame storage, epoch-fenced agent/human mutation, fresh-snapshot handback, and short-lived one-time expression-bound evaluate approvals. Heidi imports this backend broker directly and exposes it only through its existing compact Chrome gateways.

## FDX

- Source repository: `heidi-dang/flowdeck`
- Baseline branch: `feat/heidi-fdx-vci-integration`
- Baseline commit: `ea0df02c5c9dc9cc0676ec70e7fc7ded2e7e82d5`
- Imported paths: root Cargo workspace files plus `crates/fdx`

Only the complete native FDX crate and its Rust workspace lock/manifest were imported. FlowDeck agents, orchestration, application runtime, planning database, and other unrelated packages were intentionally excluded.

Tracked FDX working-tree fixes present at consolidation time were included, including structured resident-daemon reads and the associated native tests.

## Import rule

Files were selected from each source repository's tracked file list, then copied from the current working tree. This preserves intentional tracked modifications without importing `node_modules`, build artifacts, caches, local databases, FDX indexes, environment files, nested `.git` directories, or other untracked machine state.
