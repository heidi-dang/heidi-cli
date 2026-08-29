import { CPTR_APP_VERSION } from "./version.js";

export const MCP_CONTRACT_VERSION = CPTR_APP_VERSION;
export const MCP_CONTRACT_TOOL_COUNT = 20;
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
    product: "CPTR Computer",
    version: CPTR_PLUGIN_VERSION,
    schema_revision: CPTR_PLUGIN_SCHEMA_REVISION,
    contract_version: MCP_CONTRACT_VERSION,
    tool_count: MCP_CONTRACT_TOOL_COUNT,
    release_sha: env.GIT_COMMIT_SHA ?? env.RAILWAY_GIT_COMMIT_SHA ?? env.CPTR_WORKBENCH_BUILD_ID ?? null,
    released_at: "2026-08-29",
    summary: "CPTR Computer v2.0.3 fixes Heidi verification on headless and non-login production shells by resolving the bundled Node runtime instead of depending on PATH.",
    changes: [
      "Makes `heidi verify` use Heidi's signed bundled Node runtime for the exact deployed MCP contract check, with system Node only as an explicit fallback.",
      "Prevents a missing login-shell PATH from being misreported as MCP tool/resource contract drift on production hosts.",
      "Adds regression coverage for the bundled-Node verifier path and preserves the exact 20-tool MCP contract and Workbench resource policy.",
      "Keeps the v2.0.2 headless systemd fallback, Cloudflare Managed OAuth compatibility, Direct Coding safety controls, and allow:delegate enforcement unchanged.",
    ],
    refresh_required: false,
    refresh_reason: "This patch does not change the ChatGPT-facing MCP action schema, so an app-action refresh is not required.",
    refresh_path: ["Settings", "Apps / Plugins", "CPTR Computer", "Manage / Action control", "Refresh"],
    verification: {
      tool: "cptr_plugin_update",
      arguments: { action: "status" },
    },
  };
}
