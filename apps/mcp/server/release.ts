import { CPTR_APP_VERSION } from "./version.js";

export const MCP_COMPACT_TOOL_NAMES = [
  "cptr_open_live_workbench",
  "cptr_workbench_sessions_read",
  "cptr_workbench_sessions_control",
  "cptr_workspaces",
  "cptr_workspace_lifecycle",
  "cptr_workspace_inspect",
  "cptr_fdx_intelligence",
  "cptr_code_read",
  "cptr_code_mutate",
  "cptr_code_files",
  "cptr_git",
  "cptr_workspace_run_test_target",
  "cptr_code_run_command",
  "cptr_code_get_command",
  "cptr_code_cancel_command",
  "cptr_terminal_control",
  "cptr_lsp_read",
  "cptr_lsp_control",
  "cptr_direct_workers",
  "cptr_direct_worker_control",
  "cptr_benchmark",
  "cptr_ssh_read",
  "cptr_ssh_control",
  "cptr_chrome_read",
  "cptr_chrome_control",
  "cptr_plugin_update",
  "cptr_delegate_task_read",
  "cptr_delegate_task_control",
  "cptr_delegate_monitor_read",
  "cptr_delegate_monitor_control",
] as const;

export const MCP_CONTRACT_VERSION = CPTR_APP_VERSION;
export const MCP_CONTRACT_TOOL_COUNT = MCP_COMPACT_TOOL_NAMES.length;
export const CPTR_PLUGIN_VERSION = CPTR_APP_VERSION;
export const CPTR_PLUGIN_SCHEMA_REVISION = CPTR_APP_VERSION;

export type PluginUpdateManifest = {
  product: string;
  version: string;
  schema_revision: string;
  contract_version: string;
  tool_count: number;
  release_sha: string | null;
  control_profile: string;
  released_at: string;
  summary: string;
  changes: string[];
  refresh_required: boolean;
  refresh_reason: string;
  refresh_path: string[];
  verification: {
    tool: string;
    arguments: Record<string, unknown>;
  };
};

export function currentPluginUpdateManifest(env: NodeJS.ProcessEnv = process.env): PluginUpdateManifest {
  return {
    product: "Heidi",
    version: CPTR_PLUGIN_VERSION,
    schema_revision: CPTR_PLUGIN_SCHEMA_REVISION,
    contract_version: MCP_CONTRACT_VERSION,
    tool_count: MCP_CONTRACT_TOOL_COUNT,
    release_sha: env.GIT_COMMIT_SHA ?? env.RAILWAY_GIT_COMMIT_SHA ?? env.CPTR_WORKBENCH_BUILD_ID ?? null,
    control_profile: env.HEIDI_CONTROL_PROFILE?.trim() || "unknown",
    released_at: "2026-09-02",
    summary: "Heidi v2.1.11 carries the converged 30-tool release and preserves externally managed Cloudflare Tunnel ownership during signed upgrades.",
    changes: [
      "Preserves an existing active system-managed heidi-cloudflared.service during legacy upgrades, records external-system ownership, and skips tunnel-token/user-unit takeover while retaining strict public-edge verification.",
      "Recovers a missing legacy allowed-email value only from the existing owner-only non-symlink MCP environment before public-config validation, preserving secretless upgrades from older Heidi state layouts.",
      "Allows non-interactive upgrades to reuse unchanged public MCP configuration only from secure owner-only state, Access metadata, and reusable OAuth credentials, while preserving strict final deployment verification and never storing the Cloudflare API token.",
      "Pins Rustup 1.29.1 to immutable architecture-specific archive URLs and verified SHA-256 values so signed Heidi installs cannot break when Rust's mutable current/dist bootstrap changes.",
      "Converges the audited official sources heidi-dang/computer@ae2996a672ad4b595617384b7c5ee8cced3e304d and heidi-dang/chatgpt-computer-plugin@70c3962e74a75bde2fd3beb1bfaea7ac0a73b517 into Heidi's compact authorization and release boundaries.",
      "Adds migration 0018 with immutable, owner-scoped MCP usage events keyed by unique event ID plus durable engineering-session and standardized benchmark records.",
      "Persists current-week, current-month, rolling 7/30-day, and all-time MCP-visible token estimates and API-equivalent simulated cost so analytics survive backend restarts.",
      "Adds bounded client_model attribution to every compact MCP action, consumes it at the adapter boundary, and never forwards that model metadata into CPTR business handlers or treats it as authorization.",
      "Stores only bounded usage metadata and token counts for operational analytics; prompts, source code, tool arguments, tool results, hidden reasoning, cache usage, and final-answer tokens are not persisted as usage telemetry.",
      "Adds cptr_benchmark with owner-scoped disposable workspaces and a versioned server-owned randomized grader; model code cannot provide or override its score.",
      "Adds compact cptr_terminal_control, cptr_lsp_read, and cptr_lsp_control gateways over the existing workspace-scoped interactive PTY and administrator-configured LSP backend without exposing the seven legacy standalone action names in production.",
      "Hardens benchmark integrity by running untrusted student code outside the trusted scoring coordinator, closing the demonstrated __main__ grader-tampering path that could otherwise forge a perfect score.",
      "Keeps standardized benchmark results comparable by suite/version while marking observed real-work reliability and verification metrics as explicitly non-comparable across different tasks.",
      "Extends the bounded Workbench overview with responsive This week / This month token and simulated-cost cards plus comparable benchmark and observed real-work evidence, while retaining the explicit not-your-ChatGPT-bill disclaimer.",
      "Preserves exactly one Apps resource at ui://cptr/live-workbench.html, cptr_open_live_workbench as the only UI-producing action, Direct Coding as the default execution path, and allow:delegate as the explicit delegation gate.",
    ],
    refresh_required: true,
    refresh_reason: "Heidi v2.1.11 includes the v2.1.7 MCP action migration with bounded client_model attribution, cptr_benchmark, and three compact terminal/LSP parity gateways; hosts upgrading from the deployed v2.1.6 contract must refresh their cached app/action contract after deployment.",
    refresh_path: ["Settings", "Apps / Plugins", "Heidi", "Manage / Action control", "Refresh"],
    verification: {
      tool: "cptr_plugin_update",
      arguments: { action: "status" },
    },
  };
}
