import { z } from "zod";

const workspaceId = z.string().min(1).max(200);
const workerId = z.string().min(1).max(200).optional();
const workbenchSessionId = z.string().regex(/^wbs_[A-Za-z0-9_-]{16,80}$/);
const sha256 = z.string().regex(/^[a-f0-9]{64}$/);

export const workbenchSessionsReadGatewaySchema = {
  action: z.enum(["list", "get", "events"]),
  workbench_session_id: workbenchSessionId.optional(),
  include_archived: z.boolean().default(false),
  limit: z.number().int().min(1).max(200).default(50),
  after_sequence: z.number().int().min(0).max(100_000_000).default(0),
};

export const workbenchSessionsControlGatewaySchema = {
  action: z.enum(["bind", "rename", "archive", "request_delete", "confirm_delete"]),
  workbench_session_id: workbenchSessionId.optional(),
  target_type: z.enum(["task", "monitor", "command"]).optional(),
  target_id: z.string().min(1).max(200).optional(),
  workspace_id: workspaceId.optional(),
  name: z.string().min(1).max(160).optional(),
  confirmation_id: z.string().min(1).max(200).optional(),
};

export const workspacesGatewaySchema = {
  action: z.enum(["list", "get"]),
  workspace_id: workspaceId.optional(),
  include_unavailable: z.boolean().default(false),
};

export const workspaceLifecycleGatewaySchema = {
  action: z.enum(["create", "clone", "import", "refresh", "archive", "request_delete", "confirm_delete"]),
  workspace_id: workspaceId.optional(),
  name: z.string().min(1).max(100).optional(),
  repository_url: z.string().min(1).max(4_096).optional(),
  path: z.string().min(1).max(1_000).optional(),
  confirmation_id: z.string().min(1).max(200).optional(),
  warm_fdx: z.boolean().default(true),
};

export const workspaceInspectGatewaySchema = {
  action: z.enum(["project", "metadata", "tests", "dependencies", "scripts", "release"]),
  workspace_id: workspaceId,
  worker_id: workerId,
  path: z.string().min(1).max(1_000).optional(),
  depth: z.number().int().min(1).max(4).optional(),
};

export const codeReadGatewaySchema = {
  action: z.enum(["list", "read", "read_many", "search"]),
  workspace_id: workspaceId,
  worker_id: workerId,
  path: z.string().min(1).max(1_000).optional(),
  recursive: z.boolean().default(false),
  max_entries: z.number().int().min(1).max(5_000).default(500),
  cursor: z.string().optional(),
  start_line: z.number().int().min(0).max(1_000_000).optional(),
  end_line: z.number().int().min(0).max(1_000_000).optional(),
  files: z.array(z.object({
    path: z.string().min(1).max(1_000),
    start_line: z.number().int().min(0).optional(),
    end_line: z.number().int().min(0).optional(),
  })).min(1).max(10).optional(),
  max_chars: z.number().int().min(1).max(200_000).default(20_000),
  query: z.string().min(1).max(10_000).optional(),
  regex: z.boolean().default(false),
  case_insensitive: z.boolean().default(false),
  include: z.string().max(1_000).default(""),
  filenames_only: z.boolean().default(false),
  max_results: z.number().int().min(1).max(1_000).default(100),
  context_lines: z.number().int().min(0).max(10).default(0),
};

export const codeMutateGatewaySchema = {
  action: z.enum(["write", "edit", "apply_edits"]),
  workspace_id: workspaceId,
  worker_id: workerId,
  path: z.string().min(1).max(1_000),
  content: z.string().max(1_000_000).optional(),
  overwrite: z.boolean().default(false),
  expected_sha256: sha256.optional(),
  target: z.string().min(1).max(1_000_000).optional(),
  replacement: z.string().max(1_000_000).optional(),
  start_line: z.number().int().min(0).max(1_000_000).default(0),
  end_line: z.number().int().min(0).max(1_000_000).default(0),
  replace_all: z.boolean().default(false),
  edits: z.array(z.object({ target: z.string().min(1), replacement: z.string() })).min(1).max(20).optional(),
};

export const codeFilesGatewaySchema = {
  action: z.enum(["mkdir", "move", "delete"]),
  workspace_id: workspaceId,
  worker_id: workerId,
  path: z.string().min(1).max(1_000).optional(),
  source: z.string().min(1).max(1_000).optional(),
  destination: z.string().min(1).max(1_000).optional(),
  overwrite: z.boolean().default(false),
};

export const gitGatewaySchema = {
  action: z.enum(["status", "diff"]),
  workspace_id: workspaceId,
  worker_id: workerId,
  paths: z.array(z.string().min(1).max(1_000)).max(100).optional(),
  max_bytes: z.number().int().min(1).max(2_000_000).default(100_000),
};

export const terminalControlGatewaySchema = {
  action: z.enum(["send_input", "resize", "signal"]),
  workspace_id: workspaceId,
  worker_id: workerId,
  command_id: z.string().min(1).max(200),
  data: z.string().max(65_536).optional(),
  rows: z.number().int().min(5).max(300).optional(),
  cols: z.number().int().min(20).max(500).optional(),
  signal: z.enum(["interrupt", "terminate", "kill"]).optional(),
};

export const lspReadGatewaySchema = {
  action: z.enum(["discover", "request"]),
  workspace_id: workspaceId,
  worker_id: workerId,
  lsp_id: z.string().min(1).max(80).optional(),
  method: z.string().min(1).max(256).optional(),
  params: z.unknown().optional(),
  timeout_seconds: z.number().min(0.1).max(60).default(15),
};

export const lspControlGatewaySchema = {
  action: z.enum(["start", "stop"]),
  workspace_id: workspaceId,
  worker_id: workerId,
  server_id: z.string().regex(/^[a-z0-9][a-z0-9._-]{0,63}$/).optional(),
  root: z.string().min(1).max(1_000).default("."),
  lsp_id: z.string().min(1).max(80).optional(),
};

export const directWorkersGatewaySchema = {
  action: z.enum(["overview", "get"]),
  workspace_id: workspaceId,
  worker_id: z.string().min(1).max(200).optional(),
};

export const benchmarkGatewaySchema = {
  action: z.enum(["start", "get", "submit", "leaderboard"]),
  suite_id: z.string().min(1).max(80).default("cptr-python-core"),
  run_id: z.string().regex(/^bench_[A-Za-z0-9_-]{8,80}$/).optional(),
};

export const directWorkerControlGatewaySchema = {
  action: z.enum(["create", "integrate", "close"]),
  workspace_id: workspaceId,
  worker_id: z.string().min(1).max(200).optional(),
  worker_ids: z.array(z.string().min(1).max(200)).min(1).max(16).optional(),
  name: z.string().min(1).max(80).optional(),
  responsibility: z.string().max(500).default(""),
  repo_path: z.string().min(1).max(1_000).default("."),
  discard_changes: z.boolean().default(false),
};

export const sshReadGatewaySchema = {
  action: z.enum(["hosts", "status"]),
  workspace_id: workspaceId,
  command_id: z.string().min(1).max(200).optional(),
  wait_seconds: z.number().int().min(0).max(60).default(0),
  offset: z.number().int().min(0).max(100_000_000).default(0),
};

export const sshControlGatewaySchema = {
  action: z.enum(["run", "cancel"]),
  workspace_id: workspaceId,
  alias: z.string().min(1).max(128).optional(),
  command: z.string().min(1).max(20_000).optional(),
  command_id: z.string().min(1).max(200).optional(),
  wait_seconds: z.number().int().min(0).max(60).default(0),
};

export const chromeReadGatewaySchema = {
  target: z.enum(["managed", "user"]).default("managed"),
  action: z.enum(["status", "snapshot", "list_devices", "get_frame"]),
  workspace_id: workspaceId.optional(),
  session_id: z.string().min(1).max(120).optional(),
  after_frame_id: z.string().min(1).max(160).optional(),
};

export const chromeControlGatewaySchema = {
  target: z.enum(["managed", "user"]).default("managed"),
  action: z.enum([
    "navigate", "click", "type", "press_key", "scroll", "screenshot", "close",
    "approve_pairing", "open_session", "command", "transfer_lease", "return_to_agent", "approve_evaluate",
  ]),
  workspace_id: workspaceId.optional(),
  pairing_id: z.string().min(1).max(120).optional(),
  code: z.string().regex(/^\d{6}$/).optional(),
  device_id: z.string().min(1).max(120).optional(),
  session_id: z.string().min(1).max(120).optional(),
  tab_id: z.number().int().min(0).max(2_147_483_647).optional(),
  workbench_session_id: z.string().min(1).max(120).optional(),
  surface_id: z.string().min(1).max(200).optional(),
  command_id: z.string().min(1).max(160).optional(),
  browser_action: z.string().min(1).max(120).optional(),
  expected_epoch: z.number().int().min(0).optional(),
  expected_owner: z.enum(["none", "agent", "human"]).optional(),
  new_owner: z.enum(["none", "agent", "human"]).optional(),
  fresh_snapshot_id: z.string().min(1).max(200).optional(),
  expression: z.string().min(1).max(20_000).optional(),
  payload: z.record(z.string(), z.unknown()).optional(),
  wait_seconds: z.number().min(0.1).max(60).default(15),
  url: z.string().max(4_096).optional(),
  ref: z.string().max(64).optional(),
  text: z.string().max(20_000).optional(),
  key: z.string().max(128).optional(),
  modifiers: z.array(z.enum(["Alt", "Control", "Meta", "Shift"])).max(4).default([]),
  direction: z.enum(["up", "down"]).default("down"),
  amount: z.number().int().min(1).max(20).default(3),
  width: z.number().int().min(320).max(3_840).optional(),
  height: z.number().int().min(240).max(2_160).optional(),
  allow_network: z.boolean().default(false),
};

const taskExecutionPolicy = z.object({
  allow_file_writes: z.boolean().default(true),
  allow_commands: z.boolean().default(true),
  allow_network: z.boolean().default(false),
  allow_package_install: z.boolean().default(false),
}).default({
  allow_file_writes: true,
  allow_commands: true,
  allow_network: false,
  allow_package_install: false,
});

export const delegateTaskReadGatewaySchema = {
  action: z.enum(["models", "list", "get", "output", "events", "review"]),
  workspace_id: workspaceId.optional(),
  task_id: z.string().min(1).max(200).optional(),
  status: z.string().max(120).optional(),
  limit: z.number().int().min(1).max(100).default(20),
  offset: z.number().int().min(0).default(0),
  max_chars: z.number().int().min(1).max(200_000).default(20_000),
  after_sequence: z.number().int().min(0).default(0),
  max_events: z.number().int().min(1).max(500).default(50),
  max_diff_bytes: z.number().int().min(1).max(2_000_000).default(100_000),
};

export const delegateTaskControlGatewaySchema = {
  action: z.enum(["start", "execute", "decide_review", "message", "cancel"]),
  workspace_id: workspaceId.optional(),
  task_id: z.string().min(1).max(200).optional(),
  prompt: z.string().min(1).max(100_000).optional(),
  model_id: z.string().min(1).max(500).optional(),
  wait_seconds: z.number().int().min(1).max(60).default(30),
  idempotency_key: z.string().min(1).max(200).optional(),
  execution_policy: taskExecutionPolicy,
  decision: z.enum(["ACCEPT", "REJECT", "REQUEST_CHANGES"]).optional(),
  note: z.string().max(50_000).optional(),
  content: z.string().min(1).max(50_000).optional(),
};

export const delegateMonitorReadGatewaySchema = {
  action: z.enum(["list", "get", "events", "evidence"]),
  workspace_id: workspaceId.optional(),
  monitor_id: z.string().min(1).max(200).optional(),
  status: z.string().max(120).optional(),
  limit: z.number().int().min(1).max(100).default(20),
  after_sequence: z.number().int().min(0).default(0),
  max_events: z.number().int().min(1).max(500).default(100),
  scope_id: z.string().max(200).optional(),
};

export const delegateMonitorControlGatewaySchema = {
  action: z.enum(["start", "steer", "approve", "cancel"]),
  workspace_id: workspaceId.optional(),
  monitor_id: z.string().min(1).max(200).optional(),
  goal: z.string().min(1).max(100_000).optional(),
  acceptance_criteria: z.array(z.string().min(1).max(10_000)).min(1).max(100).optional(),
  model_id: z.string().min(1).max(500).optional(),
  idempotency_key: z.string().min(1).max(200).optional(),
  execution_policy: taskExecutionPolicy,
  content: z.string().min(1).max(50_000).optional(),
  approval_id: z.string().min(1).max(200).optional(),
  approved: z.boolean().optional(),
  note: z.string().max(50_000).optional(),
};
