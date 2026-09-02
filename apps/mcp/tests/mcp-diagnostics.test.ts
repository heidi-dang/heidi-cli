import assert from "node:assert/strict";
import test from "node:test";

import { ComputerApiError, ComputerClient } from "../server/client/computer-client.js";
import { McpDiagnosticsEmitter } from "../server/mcp-diagnostics.js";

test("diagnostics emitter bounds events and sanitizes failure summaries", async () => {
  const delivered: Array<Array<Record<string, unknown>>> = [];
  const emitter = new McpDiagnosticsEmitter({
    batchSize: 2,
    flushMs: 10_000,
    maxQueue: 2,
    deliver: async (events) => { delivered.push(events as Array<Record<string, unknown>>); },
  });
  emitter.latency({
    request_id: "request-1",
    correlation_id: "corr-1",
    edge_id: "client-mcp-connector",
    metric_type: "observed_request_time",
    duration_ms: 12,
    status: "ok",
  });
  emitter.failure({
    request_id: "request-1",
    correlation_id: "corr-1",
    session_id: "session-1",
    client_id: "chatgpt",
    method: "tools/call",
    tool_name: "cptr_code_read",
    stage: "cptr_backend",
    error_code: "backend_failure",
    http_status: 503,
    retryable: true,
    started_at_ms: 100,
    duration_ms: 25,
    request_bytes: 10,
    response_bytes: 20,
    summary: "Backend failed at /home/private and Bearer top-secret\nnext line",
  });
  await emitter.flush();
  const encoded = JSON.stringify(delivered).toLowerCase();
  assert.equal(encoded.includes("top-secret"), false);
  assert.equal(encoded.includes("/home/private"), false);
  const failure = delivered.flat().find((event) => event.kind === "failure");
  assert.equal(failure?.summary, "Backend failed at <redacted-path> and Bearer [REDACTED] next line");
  await emitter.close();
});

test("ComputerClient exposes dedicated telemetry ingestion endpoints", async () => {
  const calls: string[] = [];
  const computer = new ComputerClient({
    baseUrl: "http://cptr.test",
    token: "secret-token",
    fetchImpl: async (input) => {
      calls.push(String(input));
      return new Response(JSON.stringify({ accepted: 1, duplicates: 0, dropped: 0 }), { status: 200 });
    },
  });
  await computer.ingestMcpDiagnostics([]);
  await computer.ingestMcpTraffic([]);
  await computer.ingestMcpActivity([]);
  assert.deepEqual(calls, [
    "http://cptr.test/api/mcp/diagnostics/events",
    "http://cptr.test/api/mcp/traffic/events",
    "http://cptr.test/api/mcp/activity/events",
  ]);

  const failing = new ComputerClient({
    baseUrl: "http://cptr.test",
    token: "never-leak-me",
    fetchImpl: async () => new Response(JSON.stringify({ detail: "Bearer never-leak-me /private/path" }), { status: 500 }),
  });
  await assert.rejects(failing.ingestMcpDiagnostics([]), (error: unknown) => {
    assert.ok(error instanceof ComputerApiError);
    assert.equal(error.message.includes("never-leak-me"), false);
    assert.equal(error.message.includes("/private/path"), false);
    return true;
  });
});
