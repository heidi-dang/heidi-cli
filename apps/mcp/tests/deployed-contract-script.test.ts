import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { MCP_COMPACT_TOOL_NAMES } from "../server/release.js";

const source = readFileSync(new URL("../scripts/check-deployed-contract.mjs", import.meta.url), "utf8");
const packageMetadata = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8")) as {
  version?: string;
  scripts?: Record<string, string>;
};

test("deployed contract verifier tracks the canonical compact v2 contract", () => {
  const toolsBlock = source.match(/const expectedTools = \[(.*?)\];/s)?.[1] ?? "";
  const tools = [...toolsBlock.matchAll(/"([^"]+)"/g)].map((match) => match[1]);

  assert.equal(tools.length, 26);
  assert.deepEqual([...tools].sort(), [...MCP_COMPACT_TOOL_NAMES].sort());
  assert.equal(tools.includes("cptr_workspace_lifecycle"), true);
  assert.equal(tools.includes("cptr_chrome_read"), true);
  assert.equal(tools.includes("cptr_chrome_control"), true);
  assert.equal(tools.includes("cptr_plugin_update"), true);
  assert.equal(tools.includes("cptr_workbench_sessions_read"), true);
  assert.equal(tools.includes("cptr_workbench_sessions_control"), true);
  assert.equal(tools.includes("cptr_workspace_run_test_target"), true);
  assert.equal(tools.includes("cptr_fdx_intelligence"), true);
  assert.equal(tools.includes("cptr_direct_worker_control"), true);
  assert.match(packageMetadata.version ?? "", /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/);
  assert.equal(packageMetadata.scripts?.build, "tsc -p tsconfig.json");
  assert.equal(packageMetadata.scripts?.["build:compat-ui"], "npm run build:web && npm run copy:web");
  assert.match(source, /const expectedContractVersion = packageMetadata\.version;/);
  assert.match(source, /const expectedRegisteredToolCount = expectedTools\.length;/);
  assert.match(source, /health\?\.app_version !== expectedContractVersion/);
  assert.match(source, /workbench\?\.compatibility_enabled !== false/);
  assert.match(source, /tool-only production health must not depend on Workbench assets/);
  assert.doesNotMatch(source, /deployed workbench is not ready|build fingerprint is missing/);
  assert.match(source, /initialize\.capabilities\?\.resources !== undefined/);
  assert.match(source, /tool-only MCP contract/);
  assert.doesNotMatch(source, /resources\/list|resources\/read|expectedResource/);
});
