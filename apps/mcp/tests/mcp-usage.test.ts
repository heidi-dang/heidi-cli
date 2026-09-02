import assert from "node:assert/strict";
import test from "node:test";

import {
  canonicalToolCallEnvelope,
  estimateModelTokens,
  normalizeReportedModel,
} from "../server/mcp-usage.js";

test("reported model normalization remains exact and bounded", () => {
  assert.deepEqual(normalizeReportedModel("GPT-5.6 Sol"), {
    reported: "GPT-5.6 Sol",
    canonical: "gpt-5.6-sol",
  });
  assert.equal(normalizeReportedModel("mystery-gpt-5.6-special").canonical, null);
  assert.equal(normalizeReportedModel("x".repeat(500)).reported?.length, 120);
});

test("model-aware token estimation is deterministic and exposes bounded fallback", () => {
  const envelope = canonicalToolCallEnvelope("cptr_code_read", {
    action: "file",
    workspace_id: "workspace-1",
    path: "README.md",
  });
  const first = estimateModelTokens("gpt-4o", envelope);
  const second = estimateModelTokens("gpt-4o", envelope);
  assert.deepEqual(first, second);
  assert.ok(first.tokens > 0);
  assert.match(first.method, /model-map|fallback/);

  const oversized = estimateModelTokens("gpt-4o", "x".repeat(600_000));
  assert.ok(oversized.tokens > 0);
  assert.equal(oversized.method, "utf8-byte-fallback");
  assert.equal(oversized.exact_for_model, false);
});
