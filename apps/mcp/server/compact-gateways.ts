import type { McpServer } from "@modelcontextprotocol/server";
import type { ComputerClient } from "./client/computer-client.js";
import type { LiveTarget } from "./live-tickets.js";
import {
  codeFilesGatewaySchema,
  codeMutateGatewaySchema,
  codeReadGatewaySchema,
  delegateMonitorGatewaySchema,
  delegateTaskGatewaySchema,
  directWorkerControlGatewaySchema,
  directWorkersGatewaySchema,
  gitGatewaySchema,
  sshGatewaySchema,
  workbenchSessionsGatewaySchema,
  workspaceInspectGatewaySchema,
  workspaceLifecycleGatewaySchema,
  workspacesGatewaySchema,
} from "./schemas/gateways.js";
import { getCompactGatewayOutputSchema } from "./schemas/outputs.js";

const oauthMeta = { securitySchemes: [{ type: "oauth2", scopes: [] }] };

function result<T extends Record<string, unknown>>(value: T) {
  return {
    structuredContent: value,
    content: [{ type: "text" as const, text: JSON.stringify(value) }],
  };
}

function required(value: unknown, field: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${field} is required for this action`);
  return value;
}

function requiredArray<T>(value: T[] | undefined, field: string): T[] {
  if (!Array.isArray(value) || value.length === 0) throw new Error(`${field} is required for this action`);
  return value;
}

function delegatedPrompt(prompt: string): string {
  const value = prompt.trim();
  return /(^|\s)allow:delegate(?=\s|$)/i.test(value)
    ? value
    : `${value}\n\nDelegation authorization: allow:delegate`;
}

function workspaceScopedPrompt(prompt: string): string {
  const value = prompt.trim();
  if (value.includes("inspection_scope=assignment") || value.includes("inspection_scope=workspace")) return value;
  return `CPTR control-task safety contract: inspection_scope=workspace. Work only inside the selected CPTR workspace unless the assignment explicitly requires otherwise.\n\nAssignment:\n${value}`;
}

export function registerCompactGateways(
  server: McpServer,
  client: ComputerClient,
  options: {
    emitLive?: (target: LiveTarget) => void;
  } = {},
): void {
  const emitLive = options.emitLive ?? (() => undefined);
  const rawRegisterTool = server.registerTool.bind(server);
  (server as unknown as { registerTool: typeof server.registerTool }).registerTool = ((
    name: string,
    config: Record<string, unknown>,
    handler: (...args: unknown[]) => unknown,
  ) => rawRegisterTool(
    name as never,
    {
      ...config,
      outputSchema: config.outputSchema ?? getCompactGatewayOutputSchema(name),
    } as never,
    handler as never,
  )) as typeof server.registerTool;

  server.registerTool("cptr_workbench_sessions", {
    title: "Workbench session lifecycle",
    description: "List/get/events/bind/rename/archive/request-delete/confirm-delete durable Workbench sessions. Delete remains a two-step confirmed operation.",
    inputSchema: workbenchSessionsGatewaySchema,
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
    _meta: oauthMeta,
  }, async (input) => {
    switch (input.action) {
      case "list":
        return result(await client.listWorkbenchSessions({ include_archived: input.include_archived, limit: input.limit }));
      case "get":
        return result(await client.getWorkbenchSession(required(input.workbench_session_id, "workbench_session_id")));
      case "events":
        return result(await client.getWorkbenchSessionEvents({
          session_id: required(input.workbench_session_id, "workbench_session_id"),
          after_sequence: input.after_sequence,
          limit: input.limit,
        }));
      case "bind": {
        const targetType = input.target_type;
        if (!targetType) throw new Error("target_type is required for bind");
        const targetId = required(input.target_id, "target_id");
        const session = await client.bindWorkbenchSession({
          session_id: required(input.workbench_session_id, "workbench_session_id"),
          target_type: targetType,
          target_id: targetId,
          ...(input.workspace_id ? { workspace_id: input.workspace_id } : {}),
        });
        if (targetType === "command") {
          emitLive({ targetType: "command", targetId, workspaceId: required(input.workspace_id, "workspace_id") });
        } else {
          emitLive({ targetType, targetId });
        }
        return result(session);
      }
      case "rename":
        return result(await client.renameWorkbenchSession({
          session_id: required(input.workbench_session_id, "workbench_session_id"),
          name: required(input.name, "name"),
        }));
      case "archive":
        return result(await client.archiveWorkbenchSession(required(input.workbench_session_id, "workbench_session_id")));
      case "request_delete":
        return result(await client.requestWorkbenchSessionDelete(required(input.workbench_session_id, "workbench_session_id")));
      case "confirm_delete":
        return result(await client.confirmWorkbenchSessionDelete(required(input.confirmation_id, "confirmation_id")));
    }
  });

  server.registerTool("cptr_workspaces", {
    title: "Workspace discovery",
    description: "List authorized CPTR workspaces or get one workspace by ID.",
    inputSchema: workspacesGatewaySchema,
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    _meta: oauthMeta,
  }, async (input) => result(input.action === "list"
    ? await client.listWorkspaces(input.include_unavailable)
    : await client.getWorkspace(required(input.workspace_id, "workspace_id"))));

  server.registerTool("cptr_workspace_lifecycle", {
    title: "Workspace lifecycle",
    description: "Create, clone, import, refresh, archive, or confirmed-delete CPTR workspaces. Clone can bootstrap Heidi from zero workspaces and automatically warms FDX repository intelligence.",
    inputSchema: workspaceLifecycleGatewaySchema,
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    _meta: oauthMeta,
  }, async (input) => result(await client.workspaceLifecycle({
    action: input.action,
    ...(input.workspace_id ? { workspace_id: input.workspace_id } : {}),
    ...(input.name ? { name: input.name } : {}),
    ...(input.repository_url ? { repository_url: input.repository_url } : {}),
    ...(input.path ? { path: input.path } : {}),
    ...(input.confirmation_id ? { confirmation_id: input.confirmation_id } : {}),
    warm_fdx: input.warm_fdx,
  })));

  server.registerTool("cptr_workspace_inspect", {
    title: "Workspace static inspection",
    description: "Inspect project metadata, file metadata, tests, dependencies, package scripts, or static release readiness without executing code.",
    inputSchema: workspaceInspectGatewaySchema,
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    _meta: oauthMeta,
  }, async (input) => result(await client.inspectWorkspace({
    workspace_id: input.workspace_id,
    ...(input.worker_id ? { worker_id: input.worker_id } : {}),
    kind: input.action,
    ...(input.path ? { path: input.path } : {}),
    ...(input.depth ? { depth: input.depth } : {}),
  })));

  server.registerTool("cptr_code_read", {
    title: "Code read gateway",
    description: "List, read, batch-read, or search authorized workspace files. Exact reads include SHA-256 for safe mutation preconditions.",
    inputSchema: codeReadGatewaySchema,
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    _meta: oauthMeta,
  }, async (input) => {
    const base = { workspace_id: input.workspace_id, ...(input.worker_id ? { worker_id: input.worker_id } : {}) };
    switch (input.action) {
      case "list":
        return result(await client.listCodingFiles({
          ...base,
          path: input.path ?? ".",
          recursive: input.recursive,
          max_entries: input.max_entries,
          ...(input.cursor ? { cursor: input.cursor } : {}),
        }));
      case "read":
        return result(await client.readCodingFile({
          ...base,
          path: required(input.path, "path"),
          ...(input.start_line !== undefined ? { start_line: input.start_line } : {}),
          ...(input.end_line !== undefined ? { end_line: input.end_line } : {}),
        }));
      case "read_many":
        return result(await client.readManyFiles({ ...base, files: requiredArray(input.files, "files"), max_chars: input.max_chars }));
      case "search":
        return result(await client.searchCodingFiles({
          ...base,
          query: required(input.query, "query"),
          path: input.path ?? ".",
          regex: input.regex,
          case_insensitive: input.case_insensitive,
          include: input.include,
          filenames_only: input.filenames_only,
          max_results: input.max_results,
          context_lines: input.context_lines,
        }));
    }
  });

  server.registerTool("cptr_code_mutate", {
    title: "Code content mutation gateway",
    description: "Write, exact-edit, or apply multiple atomic text edits. Read existing content first and use SHA-256 preconditions for modifications.",
    inputSchema: codeMutateGatewaySchema,
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
    _meta: oauthMeta,
  }, async (input) => {
    const base = { workspace_id: input.workspace_id, ...(input.worker_id ? { worker_id: input.worker_id } : {}) };
    switch (input.action) {
      case "write":
        return result(await client.writeCodingFile({
          ...base,
          path: input.path,
          content: input.content ?? "",
          overwrite: input.overwrite,
          ...(input.expected_sha256 ? { expected_sha256: input.expected_sha256 } : {}),
        }));
      case "edit":
        return result(await client.editCodingFile({
          ...base,
          path: input.path,
          target: required(input.target, "target"),
          replacement: input.replacement ?? "",
          start_line: input.start_line,
          end_line: input.end_line,
          replace_all: input.replace_all,
          ...(input.expected_sha256 ? { expected_sha256: input.expected_sha256 } : {}),
        }));
      case "apply_edits":
        return result(await client.applyEdits({
          ...base,
          path: input.path,
          edits: requiredArray(input.edits, "edits"),
          ...(input.expected_sha256 ? { expected_sha256: input.expected_sha256 } : {}),
        }));
    }
  });

  server.registerTool("cptr_code_files", {
    title: "Code file-structure gateway",
    description: "Create a directory, move a file, or delete a file within the authorized workspace.",
    inputSchema: codeFilesGatewaySchema,
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
    _meta: oauthMeta,
  }, async (input) => {
    const base = { workspace_id: input.workspace_id, ...(input.worker_id ? { worker_id: input.worker_id } : {}) };
    switch (input.action) {
      case "mkdir": return result(await client.createCodingDirectory({ ...base, path: required(input.path, "path") }));
      case "move": return result(await client.moveCodingFile({
        ...base,
        source: required(input.source, "source"),
        destination: required(input.destination, "destination"),
        overwrite: input.overwrite,
      }));
      case "delete": return result(await client.deleteCodingFile({ ...base, path: required(input.path, "path") }));
    }
  });

  server.registerTool("cptr_git", {
    title: "Git inspection gateway",
    description: "Read Git status or a bounded workspace diff.",
    inputSchema: gitGatewaySchema,
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    _meta: oauthMeta,
  }, async (input) => result(input.action === "status"
    ? await client.getGitStatus({ workspace_id: input.workspace_id, ...(input.worker_id ? { worker_id: input.worker_id } : {}) })
    : await client.getDiff({
        workspace_id: input.workspace_id,
        ...(input.worker_id ? { worker_id: input.worker_id } : {}),
        ...(input.paths ? { paths: input.paths } : {}),
        max_bytes: input.max_bytes,
      })));

  server.registerTool("cptr_direct_workers", {
    title: "Direct Worker inspection",
    description: "Get one model-free Direct Coding Worker or an overview of all workers in a workspace.",
    inputSchema: directWorkersGatewaySchema,
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    _meta: oauthMeta,
  }, async (input) => result(input.action === "overview"
    ? await client.directWorkersOverview(input.workspace_id)
    : await client.getDirectWorker({ workspace_id: input.workspace_id, worker_id: required(input.worker_id, "worker_id") })));

  server.registerTool("cptr_direct_worker_control", {
    title: "Direct Worker lifecycle",
    description: "Create, integrate, or close isolated Git-worktree workers. Workers are model-free; ChatGPT remains the sole reasoner.",
    inputSchema: directWorkerControlGatewaySchema,
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
    _meta: oauthMeta,
  }, async (input) => {
    switch (input.action) {
      case "create": return result(await client.createDirectWorker({
        workspace_id: input.workspace_id,
        name: required(input.name, "name"),
        responsibility: input.responsibility,
        repo_path: input.repo_path,
      }));
      case "integrate": return result(await client.integrateDirectWorkers({
        workspace_id: input.workspace_id,
        worker_ids: requiredArray(input.worker_ids, "worker_ids"),
      }));
      case "close": return result(await client.closeDirectWorker({
        workspace_id: input.workspace_id,
        worker_id: required(input.worker_id, "worker_id"),
        discard_changes: input.discard_changes,
      }));
    }
  });

  server.registerTool("cptr_ssh", {
    title: "SSH control gateway",
    description: "List configured SSH aliases, run a remote command, read status/output, or cancel it through CPTR's dedicated SSH path.",
    inputSchema: sshGatewaySchema,
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    _meta: oauthMeta,
  }, async (input) => {
    switch (input.action) {
      case "hosts": return result(await client.listSshHosts({ workspace_id: input.workspace_id }));
      case "run": {
        const command = await client.runSshCommand({
          workspace_id: input.workspace_id,
          alias: required(input.alias, "alias"),
          command: required(input.command, "command"),
          wait_seconds: input.wait_seconds,
        });
        emitLive({ targetType: "command", targetId: command.command_id, workspaceId: input.workspace_id });
        return result(command);
      }
      case "status": {
        const commandId = required(input.command_id, "command_id");
        const command = await client.getSshCommand({
          workspace_id: input.workspace_id,
          command_id: commandId,
          offset: input.offset,
          wait_seconds: input.wait_seconds,
        });
        emitLive({ targetType: "command", targetId: commandId, workspaceId: input.workspace_id });
        return result(command);
      }
      case "cancel": return result(await client.cancelSshCommand({
        workspace_id: input.workspace_id,
        command_id: required(input.command_id, "command_id"),
      }));
    }
  });

  server.registerTool("cptr_delegate_task", {
    title: "Delegated task gateway",
    description: "Optional model/agent-backed task lifecycle. Never use for ordinary Direct Coding. Requires exact allow:delegate authorization for this prompt session.",
    inputSchema: delegateTaskGatewaySchema,
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    _meta: oauthMeta,
  }, async (input) => {
    switch (input.action) {
      case "models": return result(await client.listModels());
      case "list": return result(await client.listTasks({
        ...(input.workspace_id ? { workspace_id: input.workspace_id } : {}),
        ...(input.status ? { status: input.status } : {}),
        limit: input.limit,
      }));
      case "start": {
        const task = await client.startTask({
          workspace_id: required(input.workspace_id, "workspace_id"),
          prompt: delegatedPrompt(workspaceScopedPrompt(required(input.prompt, "prompt"))),
          ...(input.model_id ? { model_id: input.model_id } : {}),
          ...(input.idempotency_key ? { idempotency_key: input.idempotency_key } : {}),
          execution_policy: input.execution_policy,
        });
        emitLive({ targetType: "task", targetId: task.id });
        return result(task);
      }
      case "execute": {
        const task = await client.executeTask({
          workspace_id: required(input.workspace_id, "workspace_id"),
          prompt: delegatedPrompt(workspaceScopedPrompt(required(input.prompt, "prompt"))),
          ...(input.model_id ? { model_id: input.model_id } : {}),
          wait_seconds: input.wait_seconds,
          ...(input.idempotency_key ? { idempotency_key: input.idempotency_key } : {}),
          execution_policy: input.execution_policy,
        });
        emitLive({ targetType: "task", targetId: task.task_id });
        return result(task);
      }
      case "get": return result(await client.getTask(required(input.task_id, "task_id")));
      case "output": return result(await client.getTaskOutput({ task_id: required(input.task_id, "task_id"), offset: input.offset, max_chars: input.max_chars }));
      case "events": return result(await client.getTaskEvents({ task_id: required(input.task_id, "task_id"), after_sequence: input.after_sequence, max_events: input.max_events }));
      case "review": return result(await client.getTaskReview({ task_id: required(input.task_id, "task_id"), max_diff_bytes: input.max_diff_bytes }));
      case "decide_review": return result(await client.decideTaskReview(required(input.task_id, "task_id"), {
        decision: input.decision ?? "REQUEST_CHANGES",
        ...(input.note ? { note: input.note } : {}),
        ...(input.idempotency_key ? { idempotency_key: input.idempotency_key } : {}),
      }));
      case "message": return result(await client.sendMessage(required(input.task_id, "task_id"), required(input.content, "content"), input.idempotency_key));
      case "cancel": return result(await client.cancelTask(required(input.task_id, "task_id")));
    }
  });

  server.registerTool("cptr_delegate_monitor", {
    title: "Delegated autonomous monitor gateway",
    description: "Optional autonomous monitor lifecycle. Never use for ordinary Direct Coding. Requires exact allow:delegate authorization for this prompt session.",
    inputSchema: delegateMonitorGatewaySchema,
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    _meta: oauthMeta,
  }, async (input) => {
    switch (input.action) {
      case "list": return result(await client.listAutonomous({
        ...(input.workspace_id ? { workspace_id: input.workspace_id } : {}),
        ...(input.status ? { status: input.status } : {}),
        limit: input.limit,
      }));
      case "start": {
        const monitor = await client.createAutonomous({
          workspace_id: required(input.workspace_id, "workspace_id"),
          goal: delegatedPrompt(required(input.goal, "goal")),
          acceptance_criteria: requiredArray(input.acceptance_criteria, "acceptance_criteria"),
          ...(input.model_id ? { model_id: input.model_id } : {}),
          ...(input.idempotency_key ? { idempotency_key: input.idempotency_key } : {}),
          execution_policy: input.execution_policy,
        });
        const monitorId = String(monitor.monitor_id ?? monitor.goal_id ?? "");
        if (!monitorId) throw new Error("CPTR autonomous creation returned no monitor identity");
        emitLive({ targetType: "monitor", targetId: monitorId });
        return result({ ...monitor, monitor_id: monitorId });
      }
      case "get": return result(await client.getAutonomous(required(input.monitor_id, "monitor_id")));
      case "events": return result(await client.getAutonomousEvents({ monitor_id: required(input.monitor_id, "monitor_id"), after_sequence: input.after_sequence, max_events: input.max_events }));
      case "evidence": return result(await client.getAutonomousEvidence({ monitor_id: required(input.monitor_id, "monitor_id"), ...(input.scope_id ? { scope_id: input.scope_id } : {}) }));
      case "steer": return result(await client.steerAutonomous(required(input.monitor_id, "monitor_id"), required(input.content, "content"), input.idempotency_key));
      case "approve": return result(await client.approveAutonomous(
        required(input.monitor_id, "monitor_id"),
        required(input.approval_id, "approval_id"),
        input.approved ?? false,
        input.note,
      ));
      case "cancel": return result(await client.cancelAutonomous(required(input.monitor_id, "monitor_id")));
    }
  });
}
