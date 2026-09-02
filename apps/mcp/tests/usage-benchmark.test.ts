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

async function connect(computer: ComputerClient, options: { legacyContract?: boolean } = {}) {
  const server = createMcpServer(computer, options);
  const client = new Client({ name: "usage-benchmark-test", version: "1.0.0" });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  return { server, client };
}

test("global MCP wrapper consumes client_model and persists payload-free MCP-visible usage", async () => {
  const requests: Array<{ url: string; method: string; body: Record<string, unknown> | null }> = [];
  const computer = new ComputerClient({
    baseUrl: "http://cptr.test",
    token: "test-token",
    fetchImpl: async (input, init) => {
      const url = String(input);
      const raw = typeof init?.body === "string" ? init.body : "";
      const body = raw ? JSON.parse(raw) as Record<string, unknown> : null;
      requests.push({ url, method: String(init?.method ?? "GET"), body });
      if (url.endsWith("/api/control/v1/workspaces/ws/coding/read-many")) {
        return json({ workspace_id: "ws", files: [], total_chars: 0, truncated: false });
      }
      if (url.endsWith("/api/control/v1/mcp/analytics/usage/events")) {
        return json({ event_id: String(body?.event_id ?? ""), accepted: true, duplicate: false });
      }
      return json({});
    },
  });
  const { server, client } = await connect(computer, { legacyContract: true });

  const listed = await client.listTools();
  const readTool = listed.tools.find((tool) => tool.name === "cptr_code_read_many_files");
  assert.notEqual(readTool?.inputSchema.properties?.client_model, undefined);

  const response = await client.callTool({
    name: "cptr_code_read_many_files",
    arguments: {
      workspace_id: "ws",
      files: [{ path: "README.md" }],
      max_chars: 2000,
      client_model: "GPT-5.6 Sol",
    },
  });
  assert.equal(response.isError, undefined);

  const business = requests.find((item) => item.url.endsWith("/api/control/v1/workspaces/ws/coding/read-many"));
  assert.ok(business?.body);
  assert.equal("client_model" in business.body, false, "client_model must never leak into CPTR business payloads");

  const usageRequest = requests.find((item) => item.url.endsWith("/api/control/v1/mcp/analytics/usage/events"));
  assert.ok(usageRequest?.body);
  assert.equal(usageRequest.body.kind, "usage");
  assert.equal(usageRequest.body.model_reported, "GPT-5.6 Sol");
  assert.equal(usageRequest.body.model_canonical, "gpt-5.6-sol");
  assert.equal(usageRequest.body.model_source, "self_reported");
  assert.equal(usageRequest.body.tool_name, "cptr_code_read_many_files");
  assert.equal(usageRequest.body.estimator_exact_for_model, false);
  assert.match(String(usageRequest.body.estimator_method), /^input=.*(?:model-map|fallback);output=.*(?:model-map|fallback)$/);
  assert.ok(Number(usageRequest.body.input_tokens_estimated) > 0);
  assert.ok(Number(usageRequest.body.output_tokens_estimated) > 0);
  for (const forbidden of ["arguments", "arguments_json", "result", "result_json", "prompt", "source", "content"]) {
    assert.equal(forbidden in usageRequest.body, false, `usage payload must not persist ${forbidden}`);
  }

  await client.close();
  await server.close();
});

test("compact benchmark gateway forwards exact current ChatGPT model to the server-owned run", async () => {
  const requests: Array<{ url: string; method: string; body: Record<string, unknown> | null }> = [];
  const computer = new ComputerClient({
    baseUrl: "http://cptr.test",
    token: "test-token",
    fetchImpl: async (input, init) => {
      const url = String(input);
      const raw = typeof init?.body === "string" ? init.body : "";
      const body = raw ? JSON.parse(raw) as Record<string, unknown> : null;
      requests.push({ url, method: String(init?.method ?? "GET"), body });
      if (url.endsWith("/api/control/v1/benchmarks/runs")) {
        return json({
          run_id: "bench_1234567890abcdef",
          suite_id: "cptr-python-core",
          suite_version: "1",
          status: "READY",
          model_reported: body?.model_reported ?? null,
          model_canonical: "gpt-5.6-sol",
          workspace_id: "benchmark-workspace",
          score: null,
          max_score: 100,
          case_results: [],
          error_summary: null,
          started_at_ms: 1,
          completed_at_ms: null,
          duration_ms: null,
          comparable: true,
          comparability: "standardized_suite_only",
          tasks: [],
        });
      }
      if (url.endsWith("/api/control/v1/mcp/analytics/usage/events")) {
        return json({ event_id: String(body?.event_id ?? ""), accepted: true, duplicate: false });
      }
      return json({});
    },
  });
  const { server, client } = await connect(computer);
  const listed = await client.listTools();
  const benchmark = listed.tools.find((tool) => tool.name === "cptr_benchmark");
  assert.ok(benchmark);
  assert.notEqual(benchmark.inputSchema.properties?.client_model, undefined);
  assert.equal(benchmark.annotations?.readOnlyHint, false);
  assert.equal(benchmark.annotations?.destructiveHint, false);
  assert.equal(benchmark.annotations?.openWorldHint, false);

  const started = await client.callTool({
    name: "cptr_benchmark",
    arguments: {
      action: "start",
      suite_id: "cptr-python-core",
      client_model: "GPT-5.6 Sol",
    },
  });
  assert.equal(started.isError, undefined);

  const startRequest = requests.find((item) => item.url.endsWith("/api/control/v1/benchmarks/runs"));
  assert.ok(startRequest?.body);
  assert.deepEqual(startRequest.body, {
    suite_id: "cptr-python-core",
    model_reported: "GPT-5.6 Sol",
  });

  await client.close();
  await server.close();
});
