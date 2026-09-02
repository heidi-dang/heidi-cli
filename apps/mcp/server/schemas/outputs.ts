import { z } from "zod";

const looseObject = <T extends z.ZodRawShape>(shape: T) => z.object(shape).passthrough();
const unknownObject = looseObject({});
const unknownObjectArray = z.array(unknownObject);

const workspaceSchema = looseObject({
  workspace_id: z.string().optional(),
  name: z.string().optional(),
  available: z.boolean().optional(),
  path: z.string().optional(),
});

const workbenchSessionSchema = looseObject({
  session_id: z.string().optional(),
  name: z.string().optional(),
  workspace_id: z.string().nullable().optional(),
  status: z.string().optional(),
  active_target_type: z.enum(["task", "monitor", "command"]).nullable().optional(),
  active_target_id: z.string().nullable().optional(),
  active_workspace_id: z.string().nullable().optional(),
  event_count: z.number().int().optional(),
  created_at: z.number().optional(),
  updated_at: z.number().optional(),
  last_event_at: z.number().nullable().optional(),
  archived_at: z.number().nullable().optional(),
  deleted_at: z.number().nullable().optional(),
});

const directWorkerSchema = looseObject({
  worker_id: z.string().optional(),
  workspace_id: z.string().optional(),
  name: z.string().optional(),
  responsibility: z.string().optional(),
  repo_path: z.string().optional(),
  status: z.string().optional(),
  branch: z.string().optional(),
  base_revision: z.string().optional(),
  changed_file_count: z.number().int().optional(),
  changed_paths: z.array(z.string()).optional(),
  active_command_ids: z.array(z.string()).optional(),
  recent_command_ids: z.array(z.string()).optional(),
  created_at: z.number().optional(),
  updated_at: z.number().optional(),
  integrated_at: z.number().nullable().optional(),
  closed_at: z.number().nullable().optional(),
});

const commandSchema = looseObject({
  workspace_id: z.string().optional(),
  alias: z.string().optional(),
  command_id: z.string().optional(),
  status: z.string().optional(),
  exit_code: z.number().int().nullable().optional(),
  output: z.string().optional(),
  next_offset: z.number().int().nonnegative().optional(),
  duration_ms: z.number().int().nonnegative().optional(),
  output_truncated: z.boolean().optional(),
  timed_out: z.boolean().optional(),
});

const taskSchema = looseObject({
  id: z.string().optional(),
  task_id: z.string().optional(),
  workspace_id: z.string().optional(),
  status: z.string().optional(),
  prompt: z.string().optional(),
  model_id: z.string().optional(),
  output: z.string().optional(),
  content: z.string().optional(),
  error: z.string().nullable().optional(),
  completed: z.boolean().optional(),
  output_truncated: z.boolean().optional(),
  wait_seconds: z.number().optional(),
  completion_integrity: unknownObject.optional(),
  review: unknownObject.nullable().optional(),
  review_summary: unknownObject.nullable().optional(),
  raw_output: z.array(z.unknown()).optional(),
  created_at: z.number().optional(),
  updated_at: z.number().optional(),
});

const monitorSchema = looseObject({
  monitor_id: z.string().optional(),
  goal_id: z.string().optional(),
  workspace_id: z.string().optional(),
  status: z.string().optional(),
  scope_count: z.number().int().optional(),
  verified_count: z.number().int().optional(),
  current_scope: z.string().nullable().optional(),
  original_goal: z.string().optional(),
  acceptance_criteria: z.array(z.string()).optional(),
  scopes: z.array(z.unknown()).optional(),
  approval_id: z.string().optional(),
});

export const compactGatewayOutputSchemas = {
  cptr_workbench_sessions_read: looseObject({
    ...workbenchSessionSchema.shape,
    sessions: z.array(workbenchSessionSchema).optional(),
    events: unknownObjectArray.optional(),
    last_sequence: z.number().int().optional(),
    confirmation_id: z.string().optional(),
    expires_at: z.number().optional(),
    impact: z.string().optional(),
  }),

  cptr_workbench_sessions_control: looseObject({
    ...workbenchSessionSchema.shape,
    sessions: z.array(workbenchSessionSchema).optional(),
    events: unknownObjectArray.optional(),
    last_sequence: z.number().int().optional(),
    confirmation_id: z.string().optional(),
    expires_at: z.number().optional(),
    impact: z.string().optional(),
  }),

  cptr_workspaces: looseObject({
    ...workspaceSchema.shape,
    workspaces: z.array(workspaceSchema).optional(),
  }),

  cptr_workspace_lifecycle: looseObject({
    workspace_id: z.string().optional(),
    status: z.string().optional(),
    confirmation_id: z.string().optional(),
    expires_at: z.number().optional(),
    workspace: workspaceSchema.optional(),
    fdx: unknownObject.optional(),
  }),

  cptr_workspace_inspect: looseObject({
    workspace_id: z.string().optional(),
    kind: z.string().optional(),
    root: z.string().optional(),
    path: z.string().optional(),
    project_files: z.array(z.string()).optional(),
    detected_runtimes: z.array(z.string()).optional(),
    entries: unknownObjectArray.optional(),
    tests: z.array(z.unknown()).optional(),
    dependencies: z.unknown().optional(),
    scripts: z.unknown().optional(),
    release: z.unknown().optional(),
  }),

  cptr_code_read: looseObject({
    workspace_id: z.string().optional(),
    path: z.string().optional(),
    entries: unknownObjectArray.optional(),
    total: z.number().int().optional(),
    truncated: z.boolean().optional(),
    max_entries: z.number().int().optional(),
    cursor: z.string().nullable().optional(),
    content: z.string().optional(),
    content_sha256: z.string().optional(),
    start_line: z.number().int().optional(),
    end_line: z.number().int().optional(),
    total_lines: z.number().int().optional(),
    size: z.number().int().optional(),
    files: unknownObjectArray.optional(),
    matches: unknownObjectArray.optional(),
    max_results: z.number().int().optional(),
  }),

  cptr_code_mutate: looseObject({
    workspace_id: z.string().optional(),
    path: z.string().optional(),
    bytes_written: z.number().int().optional(),
    sha256: z.string().optional(),
    replaced_characters: z.number().int().optional(),
    inserted_characters: z.number().int().optional(),
    diff: z.string().optional(),
    edits_applied: z.number().int().optional(),
  }),

  cptr_code_files: looseObject({
    workspace_id: z.string().optional(),
    path: z.string().optional(),
    type: z.string().optional(),
    created: z.boolean().optional(),
    source: z.string().optional(),
    destination: z.string().optional(),
    sha256: z.string().optional(),
    deleted: z.boolean().optional(),
    existed: z.boolean().optional(),
  }),

  cptr_git: looseObject({
    workspace_id: z.string().optional(),
    branch: z.string().optional(),
    upstream: z.string().nullable().optional(),
    remote_url: z.string().nullable().optional(),
    ahead: z.number().int().optional(),
    behind: z.number().int().optional(),
    files: z.array(z.unknown()).optional(),
    is_repo: z.boolean().optional(),
    diff: z.string().optional(),
    max_bytes: z.number().int().optional(),
    bytes_returned: z.number().int().optional(),
    truncated: z.boolean().optional(),
    omitted_paths: z.array(z.string()).optional(),
  }),

  cptr_terminal_control: commandSchema,

  cptr_lsp_read: looseObject({
    workspace_id: z.string().optional(),
    lsp_id: z.string().optional(),
    response: z.unknown().optional(),
    servers: z.array(z.unknown()).optional(),
  }),

  cptr_lsp_control: looseObject({
    workspace_id: z.string().optional(),
    lsp_id: z.string().optional(),
    server_id: z.string().optional(),
    root: z.string().optional(),
    status: z.string().optional(),
    stopped: z.boolean().optional(),
  }),

  cptr_direct_workers: looseObject({
    ...directWorkerSchema.shape,
    workers: z.array(directWorkerSchema).optional(),
    total: z.number().int().optional(),
    active: z.number().int().optional(),
    ready: z.number().int().optional(),
    integrated: z.number().int().optional(),
  }),

  cptr_direct_worker_control: looseObject({
    ...directWorkerSchema.shape,
    workers: z.array(directWorkerSchema).optional(),
    integrated_worker_ids: z.array(z.string()).optional(),
    closed: z.boolean().optional(),
  }),

  cptr_benchmark: looseObject({
    run_id: z.string().optional(),
    suite_id: z.string().optional(),
    suite_version: z.string().optional(),
    status: z.string().optional(),
    model_reported: z.string().nullable().optional(),
    model_canonical: z.string().nullable().optional(),
    workspace_id: z.string().nullable().optional(),
    score: z.number().int().nullable().optional(),
    max_score: z.number().int().nonnegative().optional(),
    case_results: unknownObjectArray.optional(),
    error_summary: z.string().nullable().optional(),
    started_at_ms: z.number().int().nonnegative().optional(),
    completed_at_ms: z.number().int().nonnegative().nullable().optional(),
    duration_ms: z.number().int().nonnegative().nullable().optional(),
    comparable: z.boolean().optional(),
    comparability: z.string().optional(),
    tasks: unknownObjectArray.optional(),
    grader_seed: z.string().optional(),
    models: unknownObjectArray.optional(),
  }),

  cptr_ssh_read: looseObject({
    ...commandSchema.shape,
    aliases: z.array(z.string()).optional(),
  }),

  cptr_ssh_control: looseObject({
    ...commandSchema.shape,
    aliases: z.array(z.string()).optional(),
  }),

  cptr_chrome_read: unknownObject,
  cptr_chrome_control: unknownObject,

  cptr_delegate_task_read: looseObject({
    ...taskSchema.shape,
    models: unknownObjectArray.optional(),
    tasks: z.array(taskSchema).optional(),
    events: unknownObjectArray.optional(),
    review_available: z.boolean().optional(),
    message_id: z.string().optional(),
    accepted: z.boolean().optional(),
    control_message_id: z.string().optional(),
    delivery_status: z.string().optional(),
  }),

  cptr_delegate_task_control: looseObject({
    ...taskSchema.shape,
    models: unknownObjectArray.optional(),
    tasks: z.array(taskSchema).optional(),
    events: unknownObjectArray.optional(),
    review_available: z.boolean().optional(),
    message_id: z.string().optional(),
    accepted: z.boolean().optional(),
    control_message_id: z.string().optional(),
    delivery_status: z.string().optional(),
  }),

  cptr_delegate_monitor_read: looseObject({
    ...monitorSchema.shape,
    monitors: z.array(monitorSchema).optional(),
    events: unknownObjectArray.optional(),
    evidence: z.unknown().optional(),
    approval: unknownObject.optional(),
  }),

  cptr_delegate_monitor_control: looseObject({
    ...monitorSchema.shape,
    monitors: z.array(monitorSchema).optional(),
    events: unknownObjectArray.optional(),
    evidence: z.unknown().optional(),
    approval: unknownObject.optional(),
  }),
} as const;

export type CompactGatewayOutputSchemaName = keyof typeof compactGatewayOutputSchemas;

export function getCompactGatewayOutputSchema(name: string) {
  return compactGatewayOutputSchemas[name as CompactGatewayOutputSchemaName];
}
