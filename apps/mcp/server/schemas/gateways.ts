import { z } from "zod";

const workspaceId = z.string().min(1).max(200);
const workerId = z.string().min(1).max(200).optional();
const workbenchSessionId = z.string().regex(/^wbs_[A-Za-z0-9_-]{16,80}$/);
const sha256 = z.string().regex(/^[a-f0-9]{64}$/);

export const workbenchSessionsGatewaySchema = {
  action: z.enum(["list", "get", "events", "bind", "rename", "archive", "request_delete", "confirm_delete"]),
  workbench_session_id: workbenchSessionId.optional(),
  include_archived: z.boolean().default(false),
  limit: z.number().int().min(1).max(200).default(50),
  after_sequence: z.number().int().min(0).max(100_000_000).default(0),
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

export const directWorkersGatewaySchema = {
  action: z.enum(["overview", "get"]),
  workspace_id: workspaceId,
  worker_id: z.string().min(1).max(200).optional(),
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

export const sshGatewaySchema = {
  action: z.enum(["hosts", "run", "status", "cancel"]),
  workspace_id: workspaceId,
  alias: z.string().min(1).max(128).optional(),
  command: z.string().min(1).max(20_000).optional(),
  command_id: z.string().min(1).max(200).optional(),
  wait_seconds: z.number().int().min(0).max(60).default(0),
  offset: z.number().int().min(0).max(100_000_000).default(0),
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

export const delegateTaskGatewaySchema = {
  action: z.enum(["models", "list", "start", "execute", "get", "output", "events", "review", "decide_review", "message", "cancel"]),
  workspace_id: workspaceId.optional(),
  task_id: z.string().min(1).max(200).optional(),
  prompt: z.string().min(1).max(100_000).optional(),
  model_id: z.string().min(1).max(500).optional(),
  status: z.string().max(120).optional(),
  limit: z.number().int().min(1).max(100).default(20),
  wait_seconds: z.number().int().min(1).max(60).default(30),
  idempotency_key: z.string().min(1).max(200).optional(),
  execution_policy: taskExecutionPolicy,
  workbench_session_id: workbenchSessionId.optional(),
  offset: z.number().int().min(0).default(0),
  max_chars: z.number().int().min(1).max(200_000).default(20_000),
  after_sequence: z.number().int().min(0).default(0),
  max_events: z.number().int().min(1).max(500).default(50),
  max_diff_bytes: z.number().int().min(1).max(2_000_000).default(100_000),
  decision: z.enum(["ACCEPT", "REJECT", "REQUEST_CHANGES"]).optional(),
  note: z.string().max(50_000).optional(),
  content: z.string().min(1).max(50_000).optional(),
};

export const delegateMonitorGatewaySchema = {
  action: z.enum(["list", "start", "get", "events", "evidence", "steer", "approve", "cancel"]),
  workspace_id: workspaceId.optional(),
  monitor_id: z.string().min(1).max(200).optional(),
  goal: z.string().min(1).max(100_000).optional(),
  acceptance_criteria: z.array(z.string().min(1).max(10_000)).min(1).max(100).optional(),
  model_id: z.string().min(1).max(500).optional(),
  status: z.string().max(120).optional(),
  limit: z.number().int().min(1).max(100).default(20),
  idempotency_key: z.string().min(1).max(200).optional(),
  execution_policy: taskExecutionPolicy,
  workbench_session_id: workbenchSessionId.optional(),
  after_sequence: z.number().int().min(0).default(0),
  max_events: z.number().int().min(1).max(500).default(100),
  scope_id: z.string().max(200).optional(),
  content: z.string().min(1).max(50_000).optional(),
  approval_id: z.string().min(1).max(200).optional(),
  approved: z.boolean().optional(),
  note: z.string().max(50_000).optional(),
};
