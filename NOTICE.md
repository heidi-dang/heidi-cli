# Licensing and attribution

`heidi-cli` is a monorepo containing components with different licenses. The repository does **not** relicense third-party or upstream code under a single blanket license.

## CPTR backend

`apps/cptr` is based on Open WebUI Computer and remains governed by the Open Use License included at `apps/cptr/LICENSE` and mirrored at `LICENSES/CPTR-OPEN-USE.txt`.

The Open Use License requires preservation of attribution elements. The consolidation intentionally preserves the CPTR/Open WebUI product attribution, copyright notices, license text, and upstream-facing documentation inside the component.

## FDX

`crates/fdx` is taken from FlowDeck's native FDX CLI and is governed by the MIT License at `LICENSES/FDX-MIT.txt`.

## MCP adapter and Heidi deployment layer

The ChatGPT-facing MCP adapter is preserved under `apps/mcp`. Root-level Heidi installer, deployment, verification, and orchestration files are maintained in this repository. Where a file contains upstream copyright or licensing notices, those notices remain authoritative.

If you redistribute this repository, preserve all component license and attribution files.
