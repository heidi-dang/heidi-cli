import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { OverviewView } from "../web/src/overview-view.js";

test("renders the bounded CPTR overview and refresh affordance", () => {
  const html = renderToStaticMarkup(
    <OverviewView
      overview={{
        status: "ok",
        databaseStatus: "ok",
        uptimeSeconds: 3661,
        requestCount: 42,
        requestP95Ms: 18.25,
        eventLoopLagMs: 0.75,
        workspaceCount: 4,
        availableWorkspaceCount: 3,
        modelCount: 8,
        defaultModel: "provider/default",
        mcpServerCount: 2,
        sourceRevision: "a4a3a022",
        apiFamilies: ["system", "mcp", "workspace"],
        usageWeek: { requests: 12, inputTokens: 1100, outputTokens: 400, totalTokens: 1500, simulatedCostUsd: "0.0123" },
        usageMonth: { requests: 42, inputTokens: 8100, outputTokens: 1900, totalTokens: 10000, simulatedCostUsd: "0.0876" },
        engineering: { model: "GPT-5.6 Sol", reliability: 0.875, verificationRatio: 0.75, toolCalls: 24 },
        benchmark: { model: "GPT-5.6 Sol", bestScore: 96, averageScore: 91.5, maxScore: 100, attempts: 3, perfectRuns: 0 },
        benchmarkSuite: "cptr-python-core",
        benchmarkVersion: "1",
      }}
      loading={false}
      error=""
      refreshedAt="20:45"
      onRefresh={() => undefined}
    />,
  );

  assert.match(html, /CPTR overview/);
  assert.match(html, /3\/4/);
  assert.match(html, />8</);
  assert.match(html, />2</);
  assert.match(html, /provider\/default/);
  assert.match(html, /a4a3a022/);
  assert.match(html, /system/);
  assert.match(html, /Refresh/);
  assert.match(html, /1h 1m/);
  assert.match(html, /Model usage &amp; simulated cost/);
  assert.match(html, /This week/);
  assert.match(html, /This month/);
  assert.match(html, /1\.50K/);
  assert.match(html, /10\.0K/);
  assert.match(html, /\$0\.0123/);
  assert.match(html, /\$0\.0876/);
  assert.match(html, /not your ChatGPT bill/);
  assert.match(html, /Coding benchmark/);
  assert.match(html, /Comparable standardized/);
  assert.match(html, /Observed real-work · not comparable/);
  assert.match(html, /96\/100/);
  assert.match(html, /88%/);
  assert.doesNotMatch(html, /secret|Authorization|Bearer/);
});

test("renders a bounded unavailable state without inventing runtime data", () => {
  const html = renderToStaticMarkup(
    <OverviewView overview={null} loading={false} error="overview unavailable" refreshedAt="" onRefresh={() => undefined} />,
  );

  assert.match(html, /Overview unavailable/);
  assert.match(html, /overview unavailable/);
  assert.match(html, /Refresh/);
});
