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
    released_at: "2026-08-31",
    summary: "Heidi v2.1.3 makes the Workbench bootstrap explicitly optional so normal ChatGPT Direct Coding starts with the task-relevant tool instead of a host-block-prone activation call.",
    changes: [
      "Makes cptr_open_live_workbench explicitly optional and removes the instruction that told ChatGPT to call it first for direct invocations.",
      "Direct Coding now starts with the workspace, FDX, code, Git, test, SSH, or browser tool that directly matches the user's request; Workbench remains available only for explicit open/resume requests and allow:delegate authorization.",
      "Preserves the tool-only MCP connector boundary: no resources capability and no ui.resourceUri metadata are advertised.",
      "Adds cptr_workspace_lifecycle so ChatGPT can create, clone, import, refresh, archive, and confirmed-delete workspaces without requiring an existing workspace first.",
      "Automatically warms FDX repository intelligence after Git workspace provisioning and falls back cleanly to normal CPTR Direct Coding when FDX is unavailable.",
      "Defaults Heidi deployments to a developer capability profile with approved external execution for explicit push/deploy operations while reserving confirmed managed-workspace deletion for owner-full.",
      "Centralizes the compact MCP tool inventory so runtime tool count and release metadata cannot silently drift apart.",
      "Splits Workbench, SSH, managed Chrome, delegated task, and delegated monitor read surfaces from their control surfaces so read/status calls advertise read-only non-open-world semantics.",
      "Preserves destructive/open-world annotations on control surfaces; the change reduces false-positive host classification without weakening CPTR authorization or execution policy.",
    ],
    refresh_required: true,
    refresh_reason: "The cptr_open_live_workbench title and description changed, so the host must refresh its cached action contract after deployment.",
    refresh_path: ["Settings", "Apps / Plugins", "Heidi", "Manage / Action control", "Refresh"],
    verification: {
      tool: "cptr_plugin_update",
      arguments: { action: "status" },
    },
  };
}
