import { readFileSync } from "node:fs";

const endpoint = process.env.CPTR_DEPLOYED_MCP_URL?.trim();
const token = process.env.CPTR_DEPLOYED_MCP_TOKEN?.trim();
const packageMetadata = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
const expectedContractVersion = packageMetadata.version;
if (typeof expectedContractVersion !== "string" || !expectedContractVersion.trim()) {
  throw new Error("package.json is missing the canonical CPTR Computer version");
}

const expectedTools = [
  "cptr_chrome_browser",
  "cptr_code_cancel_command",
  "cptr_code_files",
  "cptr_code_get_command",
  "cptr_code_mutate",
  "cptr_code_read",
  "cptr_code_run_command",
  "cptr_delegate_monitor",
  "cptr_delegate_task",
  "cptr_direct_worker_control",
  "cptr_direct_workers",
  "cptr_fdx_intelligence",
  "cptr_git",
  "cptr_open_live_workbench",
  "cptr_plugin_update",
  "cptr_ssh",
  "cptr_workbench_sessions",
  "cptr_workspace_inspect",
  "cptr_workspace_run_test_target",
  "cptr_workspaces",
];
const expectedRegisteredToolCount = 20;
const expectedResource = "ui://cptr/live-workbench.html";

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
if (health?.workbench?.hot_reload !== true) throw new Error("deployed workbench hot reload is not enabled");
if (typeof health?.workbench?.build_id !== "string" || health.workbench.build_id.length < 12) {
  throw new Error("deployed workbench build fingerprint is missing");
}
if (health?.mcp_contract?.version !== expectedContractVersion) {
  throw new Error(`MCP contract version drift: expected ${expectedContractVersion}, got ${health?.mcp_contract?.version ?? "missing"}`);
}
if (health?.mcp_contract?.tool_count !== expectedRegisteredToolCount) {
  throw new Error(`MCP health tool-count drift: expected ${expectedRegisteredToolCount}, got ${health?.mcp_contract?.tool_count ?? "missing"}`);
}

await rpc("initialize", {
  protocolVersion: "2026-01-26",
  capabilities: {},
  clientInfo: { name: "cptr-deployed-contract-check", version: expectedContractVersion },
});
const tools = await rpc("tools/list", {});
exactSet((tools.tools ?? []).map((tool) => tool.name), expectedTools, "tool contract");
if ((tools.tools ?? []).length !== expectedRegisteredToolCount) {
  throw new Error(`MCP registered-tool-count drift: expected ${expectedRegisteredToolCount}, got ${(tools.tools ?? []).length}`);
}
const uiTools = (tools.tools ?? [])
  .filter((tool) => tool?._meta?.ui?.resourceUri === expectedResource)
  .map((tool) => tool.name);
if (JSON.stringify(uiTools) !== JSON.stringify(["cptr_open_live_workbench"])) {
  throw new Error(`live-terminal UI ownership drift: expected only cptr_open_live_workbench, got [${uiTools.join(", ") || "none"}]`);
}
const resources = await rpc("resources/list", {});
if (!(resources.resources ?? []).some((resource) => resource.uri === expectedResource)) {
  throw new Error(`resource contract drift: ${expectedResource} is unavailable`);
}
const resourceResult = await rpc("resources/read", { uri: expectedResource });
const resource = (resourceResult.contents ?? []).find((content) => content.uri === expectedResource);
if (!resource) throw new Error(`resource contract drift: ${expectedResource} has no readable content`);
if (resource.mimeType !== "text/html;profile=mcp-app") {
  throw new Error(`resource MIME drift: expected text/html;profile=mcp-app, got ${resource.mimeType ?? "missing"}`);
}
const ui = resource._meta?.ui;
const expectedWidgetDomain = process.env.CPTR_DEPLOYED_PUBLIC_ORIGIN?.trim() || new URL(endpoint).origin;
if (ui?.domain !== expectedWidgetDomain) {
  throw new Error(`resource widget domain drift: expected ${expectedWidgetDomain}, got ${ui?.domain ?? "missing"}`);
}
const connectDomains = ui?.csp?.connectDomains;
if (!Array.isArray(connectDomains) || JSON.stringify(connectDomains) !== JSON.stringify([expectedWidgetDomain])) {
  throw new Error(`resource connect-domain drift: expected [${expectedWidgetDomain}]`);
}
const resourceDomains = ui?.csp?.resourceDomains;
const expectedResourceDomains = health.workbench.hot_reload ? [expectedWidgetDomain] : [];
if (!Array.isArray(resourceDomains) || JSON.stringify(resourceDomains) !== JSON.stringify(expectedResourceDomains)) {
  throw new Error(`resource domain policy drift: expected [${expectedResourceDomains.join(", ")}]`);
}
console.log(`CPTR deployed MCP contract verified: ${expectedRegisteredToolCount} registered compact tools, ${expectedResource}, and widget domain ${expectedWidgetDomain}`);
