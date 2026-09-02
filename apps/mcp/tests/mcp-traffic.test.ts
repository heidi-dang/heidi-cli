import assert from "node:assert/strict";
import test from "node:test";

import {
  McpTrafficEmitter,
  enrichMcpClientSession,
  mcpRequestContext,
  normalizeMcpClient,
  normalizeTrafficErrorCode,
  type McpRequestContextValue,
  type McpTrafficEvent,
} from "../server/mcp-traffic.js";

test("traffic client normalization and ChatGPT session enrichment are bounded and truthful", () => {
  const base = normalizeMcpClient({ name: "ChatGPT", version: "1" });
  assert.equal(base.id, "chatgpt");
  assert.equal(normalizeMcpClient({ name: "Claude Desktop" }).label, "Claude");
  assert.equal(normalizeMcpClient({ name: "x".repeat(200) }).label.length, 80);
  const enriched = enrichMcpClientSession(base, {
    sessionId: "session-1",
    sessionName: "Convergence",
    model: "GPT-5.6 Sol",
    workspaceId: "workspace-1",
    workspaceName: "Desktop",
  });
  assert.equal(enriched.id, "chatgpt-session-session-1");
  assert.equal(enriched.model, "GPT-5.6 Sol");
  assert.equal(enriched.workspace_id, "workspace-1");
});

test("traffic emitter is non-blocking, bounded, batched, and request contexts stay isolated", async () => {
  const delivered: McpTrafficEvent[][] = [];
  const emitter = new McpTrafficEmitter({
    env: {
      CPTR_MCP_TRAFFIC_PLUGIN_BATCH_SIZE: "2",
      CPTR_MCP_TRAFFIC_PLUGIN_FLUSH_MS: "10000",
      CPTR_MCP_TRAFFIC_PLUGIN_MAX_QUEUE: "4",
    },
    deliver: async (events) => { delivered.push(events); },
  });
  const client = normalizeMcpClient({ name: "ChatGPT" });
  const context = (requestId: string): McpRequestContextValue => ({
    requestId,
    correlationId: `corr-${requestId}`,
    sessionId: "session-1",
    client,
    method: "tools/call",
    startedAt: Date.now(),
    requestBytes: 20,
    outcome: { failed: false, errorCode: null },
  });
  await Promise.all([
    mcpRequestContext.run(context("a"), async () => emitter.toolStarted("tool-a")),
    mcpRequestContext.run(context("b"), async () => emitter.toolStarted("tool-b")),
  ]);
  await emitter.flush();
  assert.deepEqual(delivered.flat().map((event) => event.request_id).sort(), ["a", "b"]);
  await emitter.close();
});

test("traffic error normalization never exposes exception text", () => {
  assert.equal(normalizeTrafficErrorCode({ status: 401 }), "unauthorized");
  assert.equal(normalizeTrafficErrorCode({ status: 400 }), "validation_error");
  assert.equal(normalizeTrafficErrorCode(new Error("Bearer secret /home/private")), "internal_error");
});
