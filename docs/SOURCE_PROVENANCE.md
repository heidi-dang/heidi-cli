# Source provenance

Initial monorepo import date: 2026-08-28.

## MCP adapter

- Source repository: `heidi-dang/chatgpt-computer-plugin`
- Baseline branch: `main`
- Baseline commit: `7020475e6afc40e0a7c26710bdb20c19d838d9d6`
- Imported path: `apps/mcp`

Tracked working-tree changes present at consolidation time were intentionally included because they were part of the current CPTR Computer contract work. Generated `.fdx` and audit directories were excluded.

## CPTR backend

- Source repository: `heidi-dang/computer`
- Baseline branch: `main`
- Baseline commit: `db9377e38dc33c5efa47030d41f0cc27eba583d9`
- Imported path: `apps/cptr`

The import intentionally includes the verified direct-coding performance changes that were still in the tracked working tree at consolidation time: bounded single/batch runtime file reads, non-PTY Direct Coding command execution, resident FDX read routing, and their regression/performance tests.

## FDX

- Source repository: `heidi-dang/flowdeck`
- Baseline branch: `feat/heidi-fdx-vci-integration`
- Baseline commit: `ea0df02c5c9dc9cc0676ec70e7fc7ded2e7e82d5`
- Imported paths: root Cargo workspace files plus `crates/fdx`

Only the complete native FDX crate and its Rust workspace lock/manifest were imported. FlowDeck agents, orchestration, application runtime, planning database, and other unrelated packages were intentionally excluded.

Tracked FDX working-tree fixes present at consolidation time were included, including structured resident-daemon reads and the associated native tests.

## Import rule

Files were selected from each source repository's tracked file list, then copied from the current working tree. This preserves intentional tracked modifications without importing `node_modules`, build artifacts, caches, local databases, FDX indexes, environment files, nested `.git` directories, or other untracked machine state.
