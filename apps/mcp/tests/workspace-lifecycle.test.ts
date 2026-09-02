import assert from "node:assert/strict";
import test from "node:test";
import { Client } from "@modelcontextprotocol/client";
import { InMemoryTransport } from "@modelcontextprotocol/server";
import { ComputerClient } from "../server/client/computer-client.js";
import { createMcpServer } from "../server/mcp.js";


test("ComputerClient workspace lifecycle invalidates the workspace discovery cache", async () => {
  let listCalls = 0;
  const fetchImpl: typeof fetch = async (input, init) => {
    const url = String(input);
    if (url.includes("/workspaces?") && (!init?.method || init.method === "GET")) {
      listCalls += 1;
      return new Response(JSON.stringify({ workspaces: listCalls === 1 ? [] : [{ workspace_id: "ws_1", name: "repo", available: true }] }), { status: 200 });
    }
    if (url.endsWith("/workspaces/lifecycle") && init?.method === "POST") {
      return new Response(JSON.stringify({ workspace_id: "ws_1", name: "repo", available: true }), { status: 200 });
    }
    return new Response(JSON.stringify({}), { status: 200 });
  };
  const computer = new ComputerClient({ baseUrl: "http://cptr.test", token: "token", fetchImpl });

  assert.deepEqual((await computer.listWorkspaces()).workspaces, []);
  const created = await computer.workspaceLifecycle({ action: "create", name: "repo" });
  assert.equal(created.workspace_id, "ws_1");
  assert.equal((await computer.listWorkspaces()).workspaces.length, 1);
  assert.equal(listCalls, 2);
});


test("compact MCP exposes workspace lifecycle before any workspace exists", async () => {
  const seen: Array<{ url: string; method: string; body: unknown }> = [];
  const computer = new ComputerClient({
    baseUrl: "http://cptr.test",
    token: "token",
    fetchImpl: async (input, init) => {
      const url = String(input);
      seen.push({
        url,
        method: init?.method ?? "GET",
        body: init?.body ? JSON.parse(String(init.body)) : null,
      });
      if (url.endsWith("/workspaces/lifecycle")) {
        return new Response(JSON.stringify({
          workspace_id: "ws_clone",
          name: "heidi-cli",
          available: true,
          managed: true,
          git_repository: true,
          fdx: { status: "ok" },
        }), { status: 200 });
      }
      return new Response(JSON.stringify({ workspaces: [] }), { status: 200 });
    },
  });
  const server = createMcpServer(computer);
  const client = new Client({ name: "workspace-lifecycle-test", version: "1.0.0" });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);

  const listed = await client.listTools();
  const tool = listed.tools.find((item) => item.name === "cptr_workspace_lifecycle");
  assert.ok(tool);
  assert.equal(tool.annotations?.readOnlyHint, false);
  assert.equal(tool.annotations?.destructiveHint, true);
  assert.equal(tool.annotations?.openWorldHint, true);

  const result = await client.callTool({
    name: "cptr_workspace_lifecycle",
    arguments: {
      action: "clone",
      repository_url: "https://github.com/heidi-dang/heidi-cli.git",
      warm_fdx: true,
    },
  });
  assert.equal(result.isError, undefined);
  const lifecycleRequest = seen.find((item) => item.url.endsWith("/workspaces/lifecycle"));
  const usageRequest = seen.find((item) => item.url.endsWith("/mcp/analytics/usage/events"));
  assert.ok(lifecycleRequest);
  assert.ok(usageRequest, "workspace lifecycle must also persist one MCP usage event");
  assert.equal(lifecycleRequest.url, "http://cptr.test/api/control/v1/workspaces/lifecycle");
  assert.equal(lifecycleRequest.method, "POST");
  assert.deepEqual(lifecycleRequest.body, {
    action: "clone",
    repository_url: "https://github.com/heidi-dang/heidi-cli.git",
    warm_fdx: true,
  });

  await client.close();
  await server.close();
});
