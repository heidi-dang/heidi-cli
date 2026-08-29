import assert from "node:assert/strict";
import test from "node:test";
import {
  appendDirectWorkerActivity,
  appendMcpToolActivity,
  initialWorkbenchState,
  summarizeWorkbench,
} from "../web/src/state.js";

test("records structured MCP activity for native workbench panels", () => {
  const started = appendMcpToolActivity(initialWorkbenchState(), {
    event_id: "fdx-start",
    timestamp: "2026-08-29T03:00:00Z",
    type: "mcp.tool",
    payload: {
      tool_name: "cptr_fdx_intelligence",
      summary: "Inspecting repository impact.",
      status: "STARTED",
      arguments_json: "{\"action\":\"impact\"}",
    },
  });
  const completed = appendMcpToolActivity(started, {
    event_id: "fdx-complete",
    timestamp: "2026-08-29T03:00:01Z",
    type: "mcp.tool",
    payload: {
      tool_name: "cptr_fdx_intelligence",
      summary: "Repository impact inspected.",
      status: "COMPLETE",
      result_json: "{\"affected_files\":7}",
    },
  });

  assert.equal(completed.toolActivity?.length, 2);
  assert.deepEqual(completed.toolActivity?.map((item) => item.toolName), [
    "cptr_fdx_intelligence",
    "cptr_fdx_intelligence",
  ]);
  assert.equal(completed.toolActivity?.[1]?.status, "COMPLETE");
  assert.equal(completed.toolActivity?.[1]?.resultJson, "{\"affected_files\":7}");
});

test("summarizes workers, changes, intelligence and verification for the inline card", () => {
  let state = initialWorkbenchState();
  state = appendDirectWorkerActivity(state, {
    event_id: "worker-a",
    timestamp: "2026-08-29T03:01:00Z",
    type: "direct.worker",
    payload: {
      worker_id: "worker-a",
      workspace_id: "ws",
      name: "Backend",
      responsibility: "Backend implementation",
      status: "RUNNING",
      summary: "Editing API state.",
      changed_file_count: 2,
      changed_paths: ["server/api.ts", "server/state.ts"],
    },
  });
  state = appendDirectWorkerActivity(state, {
    event_id: "worker-b",
    timestamp: "2026-08-29T03:01:01Z",
    type: "direct.worker",
    payload: {
      worker_id: "worker-b",
      workspace_id: "ws",
      name: "Tests",
      responsibility: "Regression coverage",
      status: "COMPLETE",
      summary: "Coverage added.",
      changed_file_count: 1,
      changed_paths: ["tests/state.test.ts"],
    },
  });
  state = appendMcpToolActivity(state, {
    event_id: "fdx",
    timestamp: "2026-08-29T03:01:02Z",
    type: "mcp.tool",
    payload: { tool_name: "cptr_fdx_intelligence", summary: "Impact mapped.", status: "COMPLETE" },
  });
  state = appendMcpToolActivity(state, {
    event_id: "tests",
    timestamp: "2026-08-29T03:01:03Z",
    type: "mcp.tool",
    payload: { tool_name: "cptr_workspace_run_test_target", summary: "68 tests passed.", status: "COMPLETE" },
  });

  const summary = summarizeWorkbench(state);

  assert.equal(summary.phase, "implementing");
  assert.equal(summary.workerCount, 2);
  assert.equal(summary.activeWorkers, 1);
  assert.equal(summary.completedWorkers, 1);
  assert.equal(summary.changedFiles, 3);
  assert.equal(summary.intelligenceEvents, 1);
  assert.equal(summary.verificationEvents, 1);
});

test("moves to verification when workers are complete and verification is active", () => {
  let state = initialWorkbenchState();
  state = appendDirectWorkerActivity(state, {
    event_id: "worker-done",
    timestamp: "2026-08-29T03:02:00Z",
    type: "direct.worker",
    payload: {
      worker_id: "worker-done",
      workspace_id: "ws",
      status: "COMPLETE",
      summary: "Implementation complete.",
      changed_file_count: 1,
      changed_paths: ["server/api.ts"],
    },
  });
  state = appendMcpToolActivity(state, {
    event_id: "verify-start",
    timestamp: "2026-08-29T03:02:01Z",
    type: "mcp.tool",
    payload: {
      tool_name: "cptr_workspace_run_test_target",
      summary: "Running verification.",
      status: "STARTED",
    },
  });

  assert.equal(summarizeWorkbench(state).phase, "verifying");
});
