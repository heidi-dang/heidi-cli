import assert from "node:assert/strict";
import test from "node:test";

import {
  findUiOverviewMetadata,
  normalizeUiOverview,
  uiOverviewUrl,
} from "../web/src/overview-model.js";

test("finds the bounded CPTR UI snapshot in nested Apps SDK tool metadata", () => {
  const overview = {
    status: "ok",
    system: { database: "ok", uptime_seconds: 42 },
    workspaces: { count: 2, available: 1, items: [] },
    models: { count: 3, default_model: "provider/model", items: [] },
    mcp_servers: { count: 1, connected_configurations: [] },
    api_surface: { source: "heidi-dang/computer@a4a3a022", families: ["system", "mcp"] },
  };

  assert.deepEqual(
    findUiOverviewMetadata({ result: { _meta: { "cptr/ui": overview } } }),
    overview,
  );
});

test("normalizes untrusted overview data into bounded display fields", () => {
  const normalized = normalizeUiOverview({
    status: "ok",
    system: {
      database: "ok",
      uptime_seconds: 123,
      requests: { count: 8, latency_ms: { p95: 12.34567 } },
      event_loop: { last_lag_ms: 1.23456 },
    },
    workspaces: {
      count: 999999,
      available: 4,
      items: [{ workspace_id: "ws_1", name: "A", available: true, path: "/secret" }],
    },
    models: {
      count: 8,
      default_model: "provider/default",
      items: [{ model_id: "provider/default", name: "Default", default: true, api_key: "secret" }],
    },
    mcp_servers: {
      count: 2,
      connected_configurations: [{ id: "server", name: "Tools", type: "mcp", enabled: true, url: "https://secret" }],
    },
    mcp_usage: {
      week: { requests: 12, input_tokens_estimated: 1100, output_tokens_estimated: 400, total_tokens_estimated: 1500, simulated_cost_usd: "0.0123" },
      month: { requests: 42, input_tokens_estimated: 8100, output_tokens_estimated: 1900, total_tokens_estimated: 10000, simulated_cost_usd: "0.0876" },
    },
    engineering: {
      comparable: false,
      sessions: [{ model_reported: "GPT-5.6 Sol", reliability: 0.875, verification_ratio: 0.75, tool_calls: 24, prompt: "secret" }],
    },
    coding_benchmark: {
      comparable: true,
      suite_id: "cptr-python-core",
      suite_version: "1",
      max_score: 100,
      models: [{ model_reported: "GPT-5.6 Sol", best_score: 96, average_score: 91.5, attempts: 3, perfect_runs: 0, grader_seed: "secret" }],
    },
    api_surface: {
      source: "heidi-dang/computer@a4a3a02251312e5f5c04b910d1e11857323b0ab5",
      families: Array.from({ length: 40 }, (_, index) => `family-${index}`),
    },
  });

  assert.equal(normalized.status, "ok");
  assert.equal(normalized.uptimeSeconds, 123);
  assert.equal(normalized.requestCount, 8);
  assert.equal(normalized.requestP95Ms, 12.346);
  assert.equal(normalized.eventLoopLagMs, 1.235);
  assert.equal(normalized.workspaceCount, 9999);
  assert.equal(normalized.availableWorkspaceCount, 4);
  assert.equal(normalized.modelCount, 8);
  assert.equal(normalized.defaultModel, "provider/default");
  assert.equal(normalized.mcpServerCount, 2);
  assert.equal(normalized.usageWeek.requests, 12);
  assert.equal(normalized.usageWeek.totalTokens, 1500);
  assert.equal(normalized.usageWeek.simulatedCostUsd, "0.0123");
  assert.equal(normalized.usageMonth.requests, 42);
  assert.equal(normalized.usageMonth.totalTokens, 10000);
  assert.equal(normalized.engineering?.model, "GPT-5.6 Sol");
  assert.equal(normalized.engineering?.reliability, 0.875);
  assert.equal(normalized.engineering?.verificationRatio, 0.75);
  assert.equal(normalized.benchmark?.bestScore, 96);
  assert.equal(normalized.benchmark?.attempts, 3);
  assert.equal(normalized.benchmarkSuite, "cptr-python-core");
  assert.equal(normalized.benchmarkVersion, "1");
  assert.equal(normalized.apiFamilies.length, 16);
  assert.equal(normalized.sourceRevision, "a4a3a022");
  assert.doesNotMatch(JSON.stringify(normalized), /secret|api_key|\/secret/);
});

test("derives the UI overview endpoint from the trusted prompt stream origin only", () => {
  assert.equal(
    uiOverviewUrl("https://mcp.example.test/live/prompt/stream"),
    "https://mcp.example.test/ui/overview",
  );
  assert.equal(uiOverviewUrl(undefined), null);
  assert.equal(uiOverviewUrl("not a url"), null);
});
