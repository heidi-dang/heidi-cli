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
