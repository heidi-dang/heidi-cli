import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { TerminalView } from "../web/src/terminal-view.js";

test("default widget surface renders a compact native workbench with terminal diagnostics excluded", () => {
  const html = renderToStaticMarkup(React.createElement(TerminalView, {
    rows: [{
      id: "row-1",
      sequence: 7,
      timestamp: "2026-08-27T00:00:00Z",
      tone: "system",
      text: "ChatGPT completed cptr_code_read_file.",
      label: "tool",
    }, {
      id: "row-2",
      sequence: 8,
      timestamp: "2026-08-27T00:00:01Z",
      tone: "stdout",
      text: "CPTR_LIVE_OUTPUT",
    }],
    status: "RUNNING",
    connection: "live",
    targetLabel: "task · task-1",
    canStop: true,
    onStop: () => {},
    onCopy: () => {},
    onPin: () => {},
    onExpand: () => {},
    displayMode: "inline",
  }));

  assert.match(html, /CPTR Workbench/);
  assert.match(html, /ChatGPT completed cptr_code_read_file/);
  assert.match(html, />tool</);
  assert.match(html, /Recent activity/);
  assert.match(html, />Pin</);
  assert.match(html, /Open Workbench/);
  assert.equal(html.includes("CPTR_LIVE_OUTPUT"), false, "raw stdout must stay outside the inline surface");
  assert.equal(html.includes("Redacted terminal diagnostics"), false, "diagnostic viewport must not render inline");
  assert.equal(html.includes(">Stop<"), false, "destructive controls stay inside fullscreen diagnostics");
  assert.equal(html.includes(">Copy<"), false, "raw-output controls stay inside fullscreen diagnostics");
  assert.equal(html.includes("Workbench views"), false, "inline mode must not render deep navigation");
});

test("fullscreen workbench exposes intelligence, verification, and terminal navigation", () => {
  const html = renderToStaticMarkup(React.createElement(TerminalView, {
    rows: [{
      id: "row-1",
      sequence: 7,
      timestamp: "2026-08-27T00:00:00Z",
      tone: "system",
      text: "Repository inspected.",
      label: "tool",
    }],
    toolActivity: [{
      id: "fdx",
      timestamp: "2026-08-27T00:00:00Z",
      toolName: "cptr_fdx_intelligence",
      summary: "Dependency impact mapped.",
      status: "COMPLETE",
      argumentsJson: "",
      resultJson: "",
      error: "",
    }, {
      id: "test",
      timestamp: "2026-08-27T00:00:01Z",
      toolName: "cptr_workspace_run_test_target",
      summary: "68 tests passed.",
      status: "COMPLETE",
      argumentsJson: "",
      resultJson: "",
      error: "",
    }],
    status: "RUNNING",
    connection: "live",
    targetLabel: "task · task-1",
    canStop: true,
    onStop: () => {},
    onCopy: () => {},
    onPin: () => {},
    onExpand: () => {},
    displayMode: "fullscreen",
  }));

  assert.match(html, />Overview</);
  assert.match(html, />Intelligence</);
  assert.match(html, />Verification</);
  assert.match(html, />Terminal</);
  assert.match(html, /1 FDX/);
  assert.match(html, /1 verification/);
  assert.equal(html.includes("Open Workbench"), false, "fullscreen mode must not offer a redundant fullscreen action");
});

test("workbench empty state contains no synthetic command output", () => {
  const html = renderToStaticMarkup(React.createElement(TerminalView, {
    rows: [],
    status: "READY",
    connection: "activity feed ready",
    targetLabel: "Ready for real CPTR activity",
    canStop: false,
    onStop: () => {},
    onCopy: () => {},
    onPin: () => {},
    onExpand: () => {},
    displayMode: "inline",
  }));

  assert.match(html, /Ready for CPTR activity/);
  assert.match(html, /Lifecycle and verification checkpoints will appear here as ChatGPT works/);
  assert.equal(html.includes("$ "), false);
  assert.equal(html.includes("mock"), false);
  assert.equal(html.includes("No command output available"), false, "hidden terminal diagnostics must not fabricate visible output");
});
