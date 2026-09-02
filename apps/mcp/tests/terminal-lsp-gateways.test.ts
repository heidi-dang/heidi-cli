import assert from "node:assert/strict";
import test from "node:test";
import { Client } from "@modelcontextprotocol/client";
import { InMemoryTransport } from "@modelcontextprotocol/server";

import { ComputerClient } from "../server/client/computer-client.js";
import { createMcpServer } from "../server/mcp.js";

function json(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

test("compact terminal and LSP gateways route bounded actions without leaking client_model", async () => {
  const requests: Array<{ url: string; method: string; body: Record<string, unknown> | null }> = [];
  const computer = new ComputerClient({
    baseUrl: "http://cptr.test",
    token: "test-token",
    fetchImpl: async (input, init) => {
      const raw = typeof init?.body === "string" ? init.body : "";
      const body = raw ? JSON.parse(raw) as Record<string, unknown> : null;
      requests.push({ url: String(input), method: String(init?.method ?? "GET"), body });
      return json({ workspace_id: "ws", command_id: "cmd", lsp_id: "lsp_123", status: "ok", servers: [] });
    },
  });
  const server = createMcpServer(computer);
  const client = new Client({ name: "terminal-lsp-gateway-test", version: "1.0.0" });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);

  const tools = new Map((await client.listTools()).tools.map((tool) => [tool.name, tool]));
  for (const name of ["cptr_terminal_control", "cptr_lsp_read", "cptr_lsp_control"]) {
    assert.ok(tools.has(name), `${name} must be production-registered`);
    assert.notEqual(tools.get(name)?.inputSchema.properties?.client_model, undefined, `${name} must accept client_model`);
  }
  for (const legacy of [
    "cptr_code_send_input",
    "cptr_code_resize_command",
    "cptr_code_signal_command",
    "cptr_lsp_discover",
    "cptr_lsp_start",
    "cptr_lsp_request",
    "cptr_lsp_stop",
  ]) {
    assert.equal(tools.has(legacy), false, `${legacy} must not be production-registered`);
  }

  const model = "GPT-5.6 Sol";
  const calls = [
    client.callTool({ name: "cptr_terminal_control", arguments: { action: "send_input", workspace_id: "ws", command_id: "cmd", data: "echo ok\n", client_model: model } }),
    client.callTool({ name: "cptr_terminal_control", arguments: { action: "resize", workspace_id: "ws", command_id: "cmd", rows: 40, cols: 120, client_model: model } }),
    client.callTool({ name: "cptr_terminal_control", arguments: { action: "signal", workspace_id: "ws", command_id: "cmd", signal: "interrupt", client_model: model } }),
    client.callTool({ name: "cptr_lsp_read", arguments: { action: "discover", workspace_id: "ws", client_model: model } }),
    client.callTool({ name: "cptr_lsp_read", arguments: { action: "request", workspace_id: "ws", lsp_id: "lsp_123", method: "textDocument/hover", params: { position: { line: 0, character: 0 } }, timeout_seconds: 12, client_model: model } }),
    client.callTool({ name: "cptr_lsp_control", arguments: { action: "start", workspace_id: "ws", server_id: "typescript", root: ".", client_model: model } }),
    client.callTool({ name: "cptr_lsp_control", arguments: { action: "stop", workspace_id: "ws", lsp_id: "lsp_123", client_model: model } }),
  ];
  const responses = await Promise.all(calls);
  assert.equal(responses.every((response) => response.isError !== true), true);

  const usageUrl = "http://cptr.test/api/control/v1/mcp/analytics/usage/events";
  const businessRequests = requests.filter((request) => request.url !== usageUrl);
  const usageRequests = requests.filter((request) => request.url === usageUrl);
  assert.deepEqual(businessRequests.map((request) => request.url), [
    "http://cptr.test/api/control/v1/workspaces/ws/coding/commands/cmd/input",
    "http://cptr.test/api/control/v1/workspaces/ws/coding/commands/cmd/resize",
    "http://cptr.test/api/control/v1/workspaces/ws/coding/commands/cmd/signal",
    "http://cptr.test/api/control/v1/workspaces/ws/coding/lsp/discover",
    "http://cptr.test/api/control/v1/workspaces/ws/coding/lsp/request",
    "http://cptr.test/api/control/v1/workspaces/ws/coding/lsp/start",
    "http://cptr.test/api/control/v1/workspaces/ws/coding/lsp/stop",
  ]);
  assert.equal(businessRequests.every((request) => request.method === "POST"), true);
  assert.equal(usageRequests.length, 7, "each compact gateway action must retain MCP usage telemetry");
  for (const request of requests) {
    assert.ok(request.body);
    assert.equal("client_model" in request.body, false, `${request.url} must not receive client_model`);
  }

  await client.close();
  await server.close();
});
