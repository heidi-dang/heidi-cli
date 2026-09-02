import assert from "node:assert/strict";
import test from "node:test";

import { McpActivityEmitter, type McpActivityEvent } from "../server/mcp-activity.js";
import { normalizeMcpClient } from "../server/mcp-traffic.js";

const client = normalizeMcpClient({ name: "ChatGPT", version: "1" });

test("activity telemetry is bounded and drops oldest events", async () => {
  const delivered: McpActivityEvent[][] = [];
  const emitter = new McpActivityEmitter({
    batchSize: 2,
    flushMs: 10_000,
    maxQueue: 2,
    deliver: async (events) => { delivered.push(events); },
  });
  const input = (index: number) => ({
    client,
    sessionId: "session-1",
    requestId: `request-${index}`,
    correlationId: `corr-${index}`,
    toolName: "cptr_code_read",
    title: "Read code",
    summary: "Reading code.",
    argumentsJson: "x".repeat(20_000),
  });
  emitter.started(input(1));
  emitter.started(input(2));
  emitter.started(input(3));
  assert.equal(emitter.stats().dropped, 1);
  await emitter.flush();
  assert.equal(delivered.flat()[0]?.arguments_json?.length, 13_000);
  await emitter.close();
});

test("activity delivery failure is swallowed", async () => {
  const emitter = new McpActivityEmitter({
    batchSize: 1,
    flushMs: 10_000,
    maxQueue: 2,
    deliver: async () => { throw new Error("destination unavailable"); },
  });
  emitter.started({
    client,
    sessionId: "session-1",
    requestId: "request-1",
    correlationId: "corr-1",
    toolName: "cptr_code_read",
    title: "Read code",
    summary: "Reading code.",
    argumentsJson: "{}",
  });
  await assert.doesNotReject(() => emitter.flush());
  assert.ok(emitter.stats().dropped >= 1);
  await emitter.close();
});
