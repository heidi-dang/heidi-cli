import assert from "node:assert/strict";
import test from "node:test";
import { Client } from "@modelcontextprotocol/client";
import { InMemoryTransport } from "@modelcontextprotocol/server";
import { ComputerClient } from "../server/client/computer-client.js";
import { createMcpServer } from "../server/mcp.js";
import { MCP_COMPACT_TOOL_NAMES, MCP_CONTRACT_TOOL_COUNT } from "../server/release.js";

const COMPACT_TOOLS = [
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
].sort();

function fixtureClient(fetchImpl: typeof fetch = async () => new Response(JSON.stringify({}), { status: 200 })) {
  return new ComputerClient({ baseUrl: "http://cptr.test", token: "test-token", fetchImpl });
}

async function connectedServer(options: {
  legacyContract?: boolean;
  workbenchUiEnabled?: boolean;
  connectDomain?: string;
  widgetBundle?: string;
  widgetStyles?: string;
} = {}) {
  const server = createMcpServer(fixtureClient(), options);
  const client = new Client({ name: "compact-contract-test", version: "1.0.0" });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  return { server, client };
}

function assertEveryToolHasObjectOutputSchema(tools: Array<{ name: string; outputSchema?: Record<string, unknown> }>) {
  const missing = tools.filter((tool) => !tool.outputSchema).map((tool) => tool.name).sort();
  assert.deepEqual(missing, []);
  for (const tool of tools) {
    assert.equal(tool.outputSchema?.type, "object", `${tool.name} must advertise an object outputSchema`);
  }
}

test("default MCP contract advertises split read/control safety surfaces", async () => {
  const { server, client } = await connectedServer();
  const listed = await client.listTools();
  const names = listed.tools.map((tool) => tool.name).sort();

  assert.equal(MCP_CONTRACT_TOOL_COUNT, 26);
  assert.deepEqual([...MCP_COMPACT_TOOL_NAMES].sort(), COMPACT_TOOLS);
  assert.deepEqual(names, COMPACT_TOOLS);
  assert.equal(listed.tools.length, 26);
  assertEveryToolHasObjectOutputSchema(listed.tools);

  const tools = new Map(listed.tools.map((tool) => [tool.name, tool]));
  for (const tool of listed.tools) {
    assert.ok(tool.outputSchema, `${tool.name} must advertise outputSchema`);
  }
  const openWorkbenchTool = tools.get("cptr_open_live_workbench");
  assert.equal(openWorkbenchTool?.annotations?.readOnlyHint, false);
  assert.equal(openWorkbenchTool?.annotations?.destructiveHint, false);
  assert.equal(openWorkbenchTool?.annotations?.openWorldHint, false);
  assert.match(openWorkbenchTool?.title ?? "", /optional/i);
  assert.match(openWorkbenchTool?.description ?? "", /optional/i);
  assert.match(openWorkbenchTool?.description ?? "", /ordinary direct coding does not require/i);
  assert.doesNotMatch(openWorkbenchTool?.description ?? "", /call this first|activation tool|before (?:a |the )?cptr/i);
  assert.equal(tools.get("cptr_code_read")?.annotations?.readOnlyHint, true);
  assert.equal(tools.get("cptr_code_mutate")?.annotations?.destructiveHint, true);
  assert.equal(tools.get("cptr_workspace_lifecycle")?.annotations?.destructiveHint, true);
  assert.equal(tools.get("cptr_workspace_lifecycle")?.annotations?.openWorldHint, true);
  assert.equal(tools.get("cptr_git")?.annotations?.readOnlyHint, true);
  for (const name of [
    "cptr_workbench_sessions_read",
    "cptr_ssh_read",
    "cptr_chrome_read",
    "cptr_delegate_task_read",
    "cptr_delegate_monitor_read",
  ]) {
    assert.equal(tools.get(name)?.annotations?.readOnlyHint, true, name);
    assert.equal(tools.get(name)?.annotations?.destructiveHint, false, name);
    assert.equal(tools.get(name)?.annotations?.openWorldHint, false, name);
  }
  assert.equal(tools.get("cptr_workbench_sessions_control")?.annotations?.destructiveHint, true);
  for (const name of [
    "cptr_ssh_control",
    "cptr_chrome_control",
    "cptr_delegate_task_control",
    "cptr_delegate_monitor_control",
  ]) {
    assert.equal(tools.get(name)?.annotations?.destructiveHint, true, name);
    assert.equal(tools.get(name)?.annotations?.openWorldHint, true, name);
  }
  assert.match(tools.get("cptr_delegate_task_read")?.description ?? "", /allow:delegate/i);
  assert.match(tools.get("cptr_delegate_task_control")?.description ?? "", /allow:delegate/i);
  assert.match(tools.get("cptr_delegate_monitor_read")?.description ?? "", /allow:delegate/i);
  assert.match(tools.get("cptr_delegate_monitor_control")?.description ?? "", /allow:delegate/i);
  assert.deepEqual(
    listed.tools
      .filter((tool) => (tool._meta as { ui?: { resourceUri?: string } } | undefined)?.ui?.resourceUri)
      .map((tool) => tool.name),
    [],
  );
  assert.equal(client.getServerCapabilities()?.resources, undefined);

  await client.close();
  await server.close();
});

test("production Workbench UI adds one Apps resource without changing the 26-tool compact contract", async () => {
  const previousHotReload = process.env.CPTR_HOT_RELOAD;
  process.env.CPTR_HOT_RELOAD = "0";
  try {
    const { server, client } = await connectedServer({
      workbenchUiEnabled: true,
      connectDomain: "https://mcp.example.test",
      widgetBundle: "document.body.textContent = 'CPTR Workbench';",
      widgetStyles: "body { color: white; }",
    });
    const listed = await client.listTools();
    assert.equal(listed.tools.length, 26);
    assert.deepEqual(listed.tools.map((tool) => tool.name).sort(), COMPACT_TOOLS);
    assert.notEqual(client.getServerCapabilities()?.resources, undefined);

    const uiTools = listed.tools
      .filter((tool) => (tool._meta as { ui?: { resourceUri?: string } } | undefined)?.ui?.resourceUri)
      .map((tool) => ({
        name: tool.name,
        resourceUri: (tool._meta as { ui?: { resourceUri?: string } }).ui?.resourceUri,
      }));
    assert.deepEqual(uiTools, [{ name: "cptr_open_live_workbench", resourceUri: "ui://cptr/live-workbench.html" }]);

    const resources = await client.listResources();
    assert.deepEqual(resources.resources.map((resource) => resource.uri), ["ui://cptr/live-workbench.html"]);
    const resource = await client.readResource({ uri: "ui://cptr/live-workbench.html" });
    assert.equal(resource.contents.length, 1);
    const content = resource.contents[0];
    assert.equal(content?.mimeType, "text/html;profile=mcp-app");
    assert.match(content && "text" in content ? String(content.text) : "", /CPTR Workbench/);
    const ui = content?._meta?.ui as { csp?: { resourceDomains?: string[]; connectDomains?: string[] } } | undefined;
    assert.deepEqual(ui?.csp?.connectDomains, ["https://mcp.example.test"]);
    assert.deepEqual(ui?.csp?.resourceDomains, []);

    await client.close();
    await server.close();
  } finally {
    if (previousHotReload === undefined) delete process.env.CPTR_HOT_RELOAD;
    else process.env.CPTR_HOT_RELOAD = previousHotReload;
  }
});

test("legacy contract cannot be enabled through a production environment toggle", async () => {
  const previous = process.env.CPTR_MCP_LEGACY_CONTRACT;
  process.env.CPTR_MCP_LEGACY_CONTRACT = "1";
  try {
    const { server, client } = await connectedServer();
    const listed = await client.listTools();
    assert.equal(listed.tools.length, 26);
    assert.equal(listed.tools.some((tool) => tool.name === "cptr_code_read_file"), false);
    assert.equal(listed.tools.some((tool) => tool.name === "cptr_code_read"), true);
    await client.close();
    await server.close();
  } finally {
    if (previous === undefined) delete process.env.CPTR_MCP_LEGACY_CONTRACT;
    else process.env.CPTR_MCP_LEGACY_CONTRACT = previous;
  }
});

test("internal compatibility harness retains the legacy 69-action fixture for regression tests only", async () => {
  const { server, client } = await connectedServer({ legacyContract: true });
  const listed = await client.listTools();
  assert.equal(listed.tools.length, 69);
  assert.equal(listed.tools.some((tool) => tool.name === "cptr_code_read_file"), true);
  assert.equal(listed.tools.some((tool) => tool.name === "cptr_code_read"), false);
  assertEveryToolHasObjectOutputSchema(listed.tools);
  await client.close();
  await server.close();
});

test("compact delegated gateway fails closed until Workbench records allow:delegate", async () => {
  let modelRequests = 0;
  const computer = fixtureClient(async (input) => {
    const url = String(input);
    if (url.endsWith("/models")) {
      modelRequests += 1;
      return new Response(JSON.stringify({ models: [] }), { status: 200 });
    }
    if (url.includes("/workspaces?")) {
      return new Response(JSON.stringify({ workspaces: [] }), { status: 200 });
    }
    if (url.endsWith("/workbench-sessions")) {
      return new Response(JSON.stringify({
        session_id: "wbs_session_00000001",
        name: "Compact fixture",
        status: "OPEN",
        workspace_id: null,
        active_target_type: null,
        active_target_id: null,
        active_workspace_id: null,
        event_count: 0,
        created_at: 1,
        updated_at: 1,
        last_event_at: null,
        archived_at: null,
      }), { status: 200 });
    }
    return new Response(JSON.stringify({}), { status: 200 });
  });
  const server = createMcpServer(computer);
  const client = new Client({ name: "compact-delegation-test", version: "1.0.0" });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);

  const blocked = await client.callTool({ name: "cptr_delegate_task_read", arguments: { action: "models" } });
  assert.equal(blocked.isError, true);
  assert.match(JSON.stringify(blocked.content), /allow:delegate/i);
  assert.equal(modelRequests, 0);

  await client.callTool({
    name: "cptr_open_live_workbench",
    arguments: { delegation_authorization: "allow:delegate" },
  });
  const allowed = await client.callTool({ name: "cptr_delegate_task_read", arguments: { action: "models" } });
  assert.equal(allowed.isError, undefined);
  assert.equal(modelRequests, 1);

  await client.close();
  await server.close();
});
