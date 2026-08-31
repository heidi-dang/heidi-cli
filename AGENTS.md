# Heidi Repository Guardrails

## NON-NEGOTIABLE CHATGPT CONNECTOR INVARIANT

The production ChatGPT-facing Heidi MCP connector uses the **26-tool compact contract plus exactly one bounded MCP Apps Workbench resource**.

The production server must advertise the MCP `resources` capability only for `ui://cptr/live-workbench.html`. Exactly one production tool, `cptr_open_live_workbench`, may publish `_meta.ui.resourceUri` / `ui.resourceUri`, and it must point to that resource. No other tool may become UI-producing without an explicit, versioned user-approved contract migration.

The legacy 63-core-tool / 69-registered-action surface remains regression-test-only and must not be enabled through production environment configuration. Ordinary ChatGPT Direct Coding does not require the Workbench opener; the UI is optional except when the user explicitly requests it or uses the `allow:delegate` authorization path.

The Workbench must remain bounded and least-privilege: production assets are built into the signed release, hot reload is disabled, CSP/connect domains are restricted to the configured Heidi MCP origin, external resource domains are empty, and browser refresh data uses the short-lived Workbench prompt ticket rather than the CPTR service bearer. The CPTR token must never be exposed to the browser widget.

Existing contract tests and `apps/mcp/scripts/check-deployed-contract.mjs` must continue to verify exactly 26 production tools, exactly one Apps resource, exactly one UI-producing tool, production-safe CSP metadata, and release-SHA provenance.

This policy supersedes the earlier v2.1.1-v2.1.4 tool-only compatibility boundary. It was reversed by explicit user instruction for v2.1.5 after the host-block investigation identified CSP configuration—not MCP Apps resource metadata itself—as the relevant integration issue.

Do not weaken, remove, bypass, or broaden this invariant as part of refactoring, MCP SDK upgrades, schema work, UI work, streaming work, or feature expansion. Changing it again requires an **explicit user instruction** that specifically changes the production ChatGPT connector contract.
