import assert from "node:assert/strict";
import test from "node:test";
import { Client } from "@modelcontextprotocol/client";
import { InMemoryTransport } from "@modelcontextprotocol/server";
import { ComputerClient } from "../server/client/computer-client.js";
import { createMcpServer } from "../server/mcp.js";
import { MCP_COMPACT_TOOL_NAMES, MCP_CONTRACT_TOOL_COUNT } from "../server/release.js";

const COMPACT_TOOLS = [
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
].sort();

function fixtureClient(fetchImpl: typeof fetch = async () => new Response(JSON.stringify({}), { status: 200 })) {
  return new ComputerClient({ baseUrl: "http://cptr.test", token: "test-token", fetchImpl });
}

async function connectedServer(options: { legacyContract?: boolean } = {}) {
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

test("default MCP contract advertises exactly the 21 compact owner-control tools", async () => {
  const { server, client } = await connectedServer();
  const listed = await client.listTools();
  const names = listed.tools.map((tool) => tool.name).sort();

  assert.equal(MCP_CONTRACT_TOOL_COUNT, 21);
  assert.deepEqual([...MCP_COMPACT_TOOL_NAMES].sort(), COMPACT_TOOLS);
  assert.deepEqual(names, COMPACT_TOOLS);
  assert.equal(listed.tools.length, 21);
  assertEveryToolHasObjectOutputSchema(listed.tools);

  const tools = new Map(listed.tools.map((tool) => [tool.name, tool]));
  assert.equal(tools.get("cptr_code_read")?.annotations?.readOnlyHint, true);
  assert.equal(tools.get("cptr_code_mutate")?.annotations?.destructiveHint, true);
  assert.equal(tools.get("cptr_workspace_lifecycle")?.annotations?.destructiveHint, true);
  assert.equal(tools.get("cptr_workspace_lifecycle")?.annotations?.openWorldHint, true);
  assert.equal(tools.get("cptr_git")?.annotations?.readOnlyHint, true);
  assert.equal(tools.get("cptr_ssh")?.annotations?.openWorldHint, true);
  assert.match(tools.get("cptr_delegate_task")?.description ?? "", /allow:delegate/i);
  assert.match(tools.get("cptr_delegate_monitor")?.description ?? "", /allow:delegate/i);
  assert.deepEqual(
    listed.tools
      .filter((tool) => (tool._meta as { ui?: { resourceUri?: string } } | undefined)?.ui?.resourceUri)
      .map((tool) => tool.name),
    ["cptr_open_live_workbench"],
  );

  await client.close();
  await server.close();
});

test("legacy contract is opt-in and retains the 69-action recovery surface", async () => {
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

  const blocked = await client.callTool({ name: "cptr_delegate_task", arguments: { action: "models" } });
  assert.equal(blocked.isError, true);
  assert.match(JSON.stringify(blocked.content), /allow:delegate/i);
  assert.equal(modelRequests, 0);

  await client.callTool({
    name: "cptr_open_live_workbench",
    arguments: { delegation_authorization: "allow:delegate" },
  });
  const allowed = await client.callTool({ name: "cptr_delegate_task", arguments: { action: "models" } });
  assert.equal(allowed.isError, undefined);
  assert.equal(modelRequests, 1);

  await client.close();
  await server.close();
});
