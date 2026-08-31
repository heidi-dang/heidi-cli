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
  "cptr_direct_workers",
  "cptr_direct_worker_control",
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
    released_at: "2026-09-01",
    summary: "Heidi v2.1.6 hardens Direct Coding test runtimes and Managed Chrome provisioning while preserving the unchanged 26-tool compact MCP Apps contract.",
    changes: [
      "Makes Direct Coding reconstruct the active Heidi Python/Node runtime PATH so fixed test profiles remain usable even when an older service environment file omitted bundled runtime paths.",
      "Adds pytest and pytest-asyncio to the production CPTR dependency set so the fixed python_pytest profile is available after deployment.",
      "Provisions Managed Chrome on host deployments, supports Ubuntu Chromium through /snap/bin, and makes the default container image include Node/npm plus Chromium.",
      "Restores exactly one production MCP Apps resource at ui://cptr/live-workbench.html while preserving the exact 26-tool compact action inventory.",
      "Makes only cptr_open_live_workbench UI-producing; ordinary Direct Coding remains independent of the optional Workbench and the legacy 69-action surface remains regression-test-only.",
      "Ships the Workbench assets in the normal signed production build with hot reload disabled and a CSP limited to the configured Heidi MCP origin.",
      "Adds a bounded CPTR UI overview path for system, workspace, model, MCP-server, and API-family summaries; the widget refreshes it with a short-lived Workbench prompt ticket and never receives the CPTR service bearer.",
      "Syncs audited heidi-dang/computer main commit a4a3a02251312e5f5c04b910d1e11857323b0ab5, including CPTR frontend polish, bulk model controls/search, and the extended API router surface.",
      "Preserves signed release-SHA provenance, owner-full deployment defaults, compact safety annotations, and host-controlled ChatGPT Refresh/review semantics.",
    ],
    refresh_required: true,
    refresh_reason: "The production MCP capability set now includes one Apps resource and cptr_open_live_workbench again publishes ui.resourceUri, so ChatGPT must refresh its cached app/action/resource contract after deployment.",
    refresh_path: ["Settings", "Apps / Plugins", "Heidi", "Manage / Action control", "Refresh"],
    verification: {
      tool: "cptr_plugin_update",
      arguments: { action: "status" },
    },
  };
}
