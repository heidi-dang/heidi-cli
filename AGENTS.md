# Heidi Repository Guardrails

## NON-NEGOTIABLE CHATGPT CONNECTOR INVARIANT

The production ChatGPT-facing Heidi MCP connector must remain **tool-only**.

Do not add, restore, advertise, or register the MCP `resources` capability for the production ChatGPT connector. Do not add or restore `_meta.ui.resourceUri`, `ui.resourceUri`, an MCP Apps UI entrypoint, or equivalent resource metadata to any production ChatGPT-facing tool or tool result.

The dormant Workbench UI implementation may remain in the repository for local QA, compatibility experiments, or a separately scoped future surface, but it must not be mounted or advertised by the production ChatGPT connector.

This constraint exists because advertising MCP Resources / Apps UI metadata caused ChatGPT host-classification and availability problems. The current tool-only contract is an intentional compatibility boundary, not unfinished work.

Existing contract tests and `apps/mcp/scripts/check-deployed-contract.mjs` must continue to verify that the server advertises no MCP resources capability and that no tool exposes UI resource metadata.

Do not weaken, remove, bypass, or reinterpret this invariant as part of refactoring, MCP SDK upgrades, schema work, UI work, streaming work, or feature expansion. Changing this policy requires an **explicit user instruction** that specifically reverses the tool-only ChatGPT connector decision.
