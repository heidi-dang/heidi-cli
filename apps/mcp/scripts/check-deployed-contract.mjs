import { readFileSync } from "node:fs";

const endpoint = process.env.CPTR_DEPLOYED_MCP_URL?.trim();
const token = process.env.CPTR_DEPLOYED_MCP_TOKEN?.trim();
const packageMetadata = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
const expectedContractVersion = packageMetadata.version;
if (typeof expectedContractVersion !== "string" || !expectedContractVersion.trim()) {
  throw new Error("package.json is missing the canonical CPTR Computer version");
}

const expectedTools = [
  "cptr_chrome_control",
  "cptr_chrome_read",
  "cptr_code_cancel_command",
  "cptr_code_files",
  "cptr_code_get_command",
  "cptr_code_mutate",
  "cptr_code_read",
  "cptr_code_run_command",
  "cptr_delegate_monitor_control",
  "cptr_delegate_monitor_read",
  "cptr_delegate_task_control",
  "cptr_delegate_task_read",
  "cptr_direct_worker_control",
  "cptr_direct_workers",
  "cptr_fdx_intelligence",
  "cptr_git",
  "cptr_open_live_workbench",
  "cptr_plugin_update",
  "cptr_ssh_control",
  "cptr_ssh_read",
  "cptr_workbench_sessions_control",
  "cptr_workbench_sessions_read",
  "cptr_workspace_lifecycle",
  "cptr_workspace_inspect",
  "cptr_workspace_run_test_target",
  "cptr_workspaces",
];
const expectedRegisteredToolCount = expectedTools.length;

if (!endpoint || !token) {
  throw new Error("Set CPTR_DEPLOYED_MCP_URL and CPTR_DEPLOYED_MCP_TOKEN before running the deployed contract check.");
}

let nextId = 1;
async function rpc(method, params) {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
    },
    body: JSON.stringify({ jsonrpc: "2.0", id: nextId++, method, params }),
  });
  if (!response.ok) throw new Error(`${method} failed with HTTP ${response.status}`);
  const payload = await response.json();
  if (payload.error) throw new Error(`${method} returned ${payload.error.message ?? "an RPC error"}`);
  return payload.result ?? payload;
}

function exactSet(actual, expected, label) {
  const actualSorted = [...actual].sort();
  const expectedSorted = [...expected].sort();
  if (JSON.stringify(actualSorted) !== JSON.stringify(expectedSorted)) {
    const missing = expectedSorted.filter((name) => !actualSorted.includes(name));
    const unexpected = actualSorted.filter((name) => !expectedSorted.includes(name));
    throw new Error(`${label} drift: missing [${missing.join(", ") || "none"}], unexpected [${unexpected.join(", ") || "none"}]`);
  }
}

const healthUrl = new URL("/health", endpoint);
const healthResponse = await fetch(healthUrl);
if (!healthResponse.ok) throw new Error(`health check failed with HTTP ${healthResponse.status}`);
const health = await healthResponse.json();
if (health?.app_version !== expectedContractVersion) {
  throw new Error(`app version drift: expected ${expectedContractVersion}, got ${health?.app_version ?? "missing"}`);
}
if (health?.workbench?.ready !== true) throw new Error("deployed workbench is not ready");
if (typeof health?.workbench?.build_id !== "string" || health.workbench.build_id.length < 12) {
  throw new Error("deployed workbench build fingerprint is missing");
}
// hot_reload is optional: enabled in dev/hot-reload deployments, disabled in standard production.
if (health?.workbench?.hot_reload === true) {
  console.log("  workbench: hot_reload enabled (dev mode)");
} else {
  console.log("  workbench: hot_reload disabled (standard production)");
}
if (health?.mcp_contract?.version !== expectedContractVersion) {
  throw new Error(`MCP contract version drift: expected ${expectedContractVersion}, got ${health?.mcp_contract?.version ?? "missing"}`);
}
if (health?.mcp_contract?.tool_count !== expectedRegisteredToolCount) {
  throw new Error(`MCP health tool-count drift: expected ${expectedRegisteredToolCount}, got ${health?.mcp_contract?.tool_count ?? "missing"}`);
}

const initialize = await rpc("initialize", {
  protocolVersion: "2026-01-26",
  capabilities: {},
  clientInfo: { name: "cptr-deployed-contract-check", version: expectedContractVersion },
});
if (initialize.capabilities?.resources !== undefined) {
  throw new Error("MCP resource capability drift: expected a tool-only MCP contract with no resources capability");
}
const tools = await rpc("tools/list", {});
exactSet((tools.tools ?? []).map((tool) => tool.name), expectedTools, "tool contract");
if ((tools.tools ?? []).length !== expectedRegisteredToolCount) {
  throw new Error(`MCP registered-tool-count drift: expected ${expectedRegisteredToolCount}, got ${(tools.tools ?? []).length}`);
}
const uiTools = (tools.tools ?? [])
  .filter((tool) => tool?._meta?.ui?.resourceUri)
  .map((tool) => tool.name);
if (uiTools.length !== 0) {
  throw new Error(`MCP UI metadata drift: expected no UI-producing tools, got [${uiTools.join(", ")}]`);
}
console.log(`CPTR deployed tool-only MCP contract verified: ${expectedRegisteredToolCount} registered compact tools and no UI resource entrypoint`);
