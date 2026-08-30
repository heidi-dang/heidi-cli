import { CPTR_APP_VERSION } from "./version.js";

export const MCP_COMPACT_TOOL_NAMES = [
  "cptr_open_live_workbench",
  "cptr_workbench_sessions",
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
  "cptr_direct_workers",
  "cptr_direct_worker_control",
  "cptr_ssh",
  "cptr_chrome_browser",
  "cptr_plugin_update",
  "cptr_delegate_task",
  "cptr_delegate_monitor",
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
    released_at: "2026-08-30",
    summary: "Heidi v2.1.1 switches the ChatGPT-facing MCP contract to tool-only mode by disabling the MCP Apps UI entrypoint while preserving Workbench session state and Direct Coding tools.",
    changes: [
      "Removes the MCP resources capability and ui.resourceUri tool metadata so ChatGPT sees Heidi as a tool-only MCP connector instead of an MCP Apps UI surface.",
      "Keeps cptr_open_live_workbench as a data-only durable Workbench session bootstrap, preserving prompt authorization and session context without mounting a widget.",
      "Adds cptr_workspace_lifecycle so ChatGPT can create, clone, import, refresh, archive, and confirmed-delete workspaces without requiring an existing workspace first.",
      "Automatically warms FDX repository intelligence after Git workspace provisioning and falls back cleanly to normal CPTR Direct Coding when FDX is unavailable.",
      "Adds an owner-full capability profile for authenticated machine owners, including approved external execution and confirmed managed-workspace deletion.",
      "Centralizes the compact MCP tool inventory so runtime tool count and release metadata cannot silently drift apart.",
    ],
    refresh_required: true,
    refresh_reason: "v2.1.1 removes the ChatGPT-facing MCP Apps UI entrypoint, so the host must refresh its cached action contract after deployment.",
    refresh_path: ["Settings", "Apps / Plugins", "Heidi", "Manage / Action control", "Refresh"],
    verification: {
      tool: "cptr_plugin_update",
      arguments: { action: "status" },
    },
  };
}
