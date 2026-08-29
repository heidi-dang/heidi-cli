export type WorkbenchEvent = {
  version?: number;
  event_id: string;
  sequence: number;
  timestamp: string;
  type: string;
  payload?: Record<string, unknown>;
  task_id?: string | null;
  monitor_id?: string | null;
  worker_task_id?: string | null;
  target?: { type: "task" | "monitor" | "command"; id: string };
  redaction_applied?: boolean;
};

export type McpToolActivity = {
  event_id: string;
  timestamp: string;
  type: "mcp.tool";
  payload?: {
    tool_name?: unknown;
    summary?: unknown;
    status?: unknown;
    arguments_json?: unknown;
    result_json?: unknown;
    error?: unknown;
  };
};

export type WorkbenchToolActivity = {
  id: string;
  timestamp: string;
  toolName: string;
  summary: string;
  status: string;
  argumentsJson: string;
  resultJson: string;
  error: string;
};

export type WorkbenchPhase = "ready" | "understanding" | "implementing" | "verifying" | "complete" | "blocked";

export type WorkbenchSummary = {
  phase: WorkbenchPhase;
  workerCount: number;
  activeWorkers: number;
  completedWorkers: number;
  changedFiles: number;
  intelligenceEvents: number;
  verificationEvents: number;
};

export type DirectWorkerActivity = {
  event_id: string;
  timestamp: string;
  type: "direct.worker";
  payload: {
    worker_id: string;
    workspace_id?: unknown;
    name?: unknown;
    responsibility?: unknown;
    repo_path?: unknown;
    status?: unknown;
    summary?: unknown;
    changed_file_count?: unknown;
    changed_paths?: unknown;
    active_command_ids?: unknown;
    recent_command_ids?: unknown;
  };
};

export type DirectWorkerActivityRow = {
  id: string;
  timestamp: string;
  status: string;
  summary: string;
};

export type DirectWorkerState = {
  workerId: string;
  workspaceId: string;
  name: string;
  responsibility: string;
  repoPath: string;
  status: string;
  summary: string;
  changedFileCount: number;
  changedPaths: string[];
  activeCommandIds: string[];
  recentCommandIds: string[];
  activity: DirectWorkerActivityRow[];
};

export type TerminalRow = {
  id: string;
  sequence: number;
  timestamp: string;
  tone: "prompt" | "stdout" | "stderr" | "system" | "success" | "error";
  text: string;
  commandId?: string;
  label?: string;
};

export type WorkbenchState = {
  status: string;
  lastSequence: number;
  transcript: TerminalRow[];
  workers: Record<string, DirectWorkerState>;
  workerOrder: string[];
  toolActivity?: WorkbenchToolActivity[];
};

const MAX_TERMINAL_ROWS = 2_000;
const MAX_WORKER_ACTIVITY_ROWS = 120;
const MAX_TOOL_ACTIVITY_ROWS = 240;

export const TERMINAL_WORKBENCH_STATUSES = new Set([
  "COMPLETE",
  "COMPLETE_WITH_TOOL_ERRORS",
  "CANCELLED",
  "FAILED",
  "BLOCKED",
  "REVIEW_REQUIRED",
  "REJECTED",
]);

const AUTHORITATIVE_STATUS_EVENTS = new Set([
  "task.started",
  "task.failed",
  "task.cancelled",
  "task.terminal",
  "task.review_ready",
  "task.review_changes_requested",
  "task.review_accepted",
  "task.review_rejected",
  "monitor.started",
  "monitor.terminal",
  "monitor.approval",
  "command.started",
  "command.completed",
]);

const COMPLETE_TOOL_STATUSES = new Set(["COMPLETE", "COMPLETED", "SUCCESS", "SUCCEEDED", "PASSED"]);

export function isTerminalWorkbenchStatus(status: string): boolean {
  return TERMINAL_WORKBENCH_STATUSES.has(status.toUpperCase());
}

export function isIntelligenceTool(toolName: string): boolean {
  const normalized = toolName.toLowerCase();
  return normalized === "cptr_fdx_intelligence" || normalized.includes("fdx");
}

export function isVerificationTool(toolName: string): boolean {
  return /(?:test|build|typecheck|verify|release_readiness|chrome_browser)/i.test(toolName);
}

export function workbenchTargetIdentity(
  targetType?: "task" | "monitor" | "command",
  targetId?: string,
  workspaceId?: string,
): string | null {
  if (!targetType || !targetId) return null;
  if (targetType === "command") return workspaceId ? `command:${workspaceId}:${targetId}` : null;
  return `${targetType}:${targetId}`;
}

export class LiveTargetSession {
  targetIdentity: string | null = null;
  cursor = 0;
  renewalAttempts = 0;

  bind(
    targetType?: "task" | "monitor" | "command",
    targetId?: string,
    workspaceId?: string,
  ): boolean {
    const nextIdentity = workbenchTargetIdentity(targetType, targetId, workspaceId);
    if (this.targetIdentity === nextIdentity) return false;
    this.targetIdentity = nextIdentity;
    this.cursor = 0;
    this.renewalAttempts = 0;
    return true;
  }
}

export function authoritativeWorkbenchStatus(event: WorkbenchEvent): string | null {
  if (!AUTHORITATIVE_STATUS_EVENTS.has(event.type)) return null;
  if (event.type.startsWith("command.") && event.target?.type !== "command") return null;
  const payloadStatus = stringValue(event.payload?.status).toUpperCase();
  if (payloadStatus) return payloadStatus;
  switch (event.type) {
    case "task.started":
    case "task.review_changes_requested":
    case "monitor.started":
    case "command.started":
      return "RUNNING";
    case "task.failed":
      return "FAILED";
    case "task.cancelled":
      return "CANCELLED";
    case "task.review_ready":
      return "REVIEW_REQUIRED";
    case "task.review_accepted":
      return "COMPLETE";
    case "task.review_rejected":
      return "REJECTED";
    case "monitor.approval":
      return "APPROVAL_REQUIRED";
    default:
      return null;
  }
}

export function eventTerminatesWorkbench(event: WorkbenchEvent): boolean {
  const status = authoritativeWorkbenchStatus(event);
  return status !== null && isTerminalWorkbenchStatus(status);
}

function bounded<T>(items: T[], limit: number): T[] {
  return items.length > limit ? items.slice(items.length - limit) : items;
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function stringArray(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined;
  return value.filter((item): item is string => typeof item === "string");
}

export function appendDirectWorkerActivity(
  state: WorkbenchState,
  event: DirectWorkerActivity,
): WorkbenchState {
  const payload = event.payload;
  const workerId = stringValue(payload.worker_id);
  if (!workerId) return state;
  const existing = state.workers[workerId];
  if (existing?.activity.some((row) => row.id === event.event_id)) return state;
  const status = stringValue(payload.status, existing?.status ?? "READY").toUpperCase();
  const summary = stringValue(payload.summary, existing?.summary ?? "Worker ready");
  const changedPaths = stringArray(payload.changed_paths) ?? existing?.changedPaths ?? [];
  const activeCommandIds = stringArray(payload.active_command_ids) ?? existing?.activeCommandIds ?? [];
  const recentCommandIds = stringArray(payload.recent_command_ids) ?? existing?.recentCommandIds ?? [];
  const changedCount = typeof payload.changed_file_count === "number"
    ? Math.max(0, Math.trunc(payload.changed_file_count))
    : existing?.changedFileCount ?? changedPaths.length;
  const worker: DirectWorkerState = {
    workerId,
    workspaceId: stringValue(payload.workspace_id, existing?.workspaceId ?? ""),
    name: stringValue(payload.name, existing?.name ?? workerId.slice(0, 12)),
    responsibility: stringValue(payload.responsibility, existing?.responsibility ?? "Direct coding"),
    repoPath: stringValue(payload.repo_path, existing?.repoPath ?? "."),
    status,
    summary,
    changedFileCount: changedCount,
    changedPaths,
    activeCommandIds,
    recentCommandIds,
    activity: bounded([
      ...(existing?.activity ?? []),
      { id: event.event_id, timestamp: event.timestamp, status, summary },
    ], MAX_WORKER_ACTIVITY_ROWS),
  };
  return {
    ...state,
    workers: { ...state.workers, [workerId]: worker },
    workerOrder: existing ? state.workerOrder : [...state.workerOrder, workerId],
  };
}

export function appendMcpToolActivity(state: WorkbenchState, activity: McpToolActivity): WorkbenchState {
  const rowPrefix = `${activity.event_id}:mcp`;
  if (state.transcript.some((row) => row.id.startsWith(rowPrefix))) return state;
  const payload = activity.payload ?? {};
  const toolName = stringValue(payload.tool_name, "CPTR tool");
  const summary = stringValue(payload.summary, `ChatGPT completed ${toolName}.`);
  const status = stringValue(payload.status, "COMPLETE").toUpperCase();
  const argumentsJson = stringValue(payload.arguments_json);
  const resultJson = stringValue(payload.result_json);
  const errorText = stringValue(payload.error);
  const rows: TerminalRow[] = [];
  const add = (suffix: string, label: string, text: string, tone: TerminalRow["tone"] = "system") => {
    if (!text) return;
    rows.push({
      id: `${rowPrefix}:${suffix}`,
      sequence: state.lastSequence,
      timestamp: activity.timestamp,
      tone,
      text,
      label,
    });
  };

  if (status === "STARTED") {
    add("work", "work", summary);
    add("call", "call", toolName, "prompt");
    add("args", "args", argumentsJson);
  } else if (["FAILED", "ERROR", "CANCELLED", "BLOCKED"].includes(status)) {
    add("error", "error", errorText || summary, "error");
  } else {
    add("result", "result", resultJson, "stdout");
    add("done", "done", summary, "success");
  }

  if (!rows.length) add("tool", "tool", summary);
  const toolActivity = bounded([
    ...(state.toolActivity ?? []),
    {
      id: activity.event_id,
      timestamp: activity.timestamp,
      toolName,
      summary,
      status,
      argumentsJson,
      resultJson,
      error: errorText,
    },
  ], MAX_TOOL_ACTIVITY_ROWS);
  return {
    ...state,
    transcript: bounded([...state.transcript, ...rows], MAX_TERMINAL_ROWS),
    toolActivity,
  };
}

function terminalRows(event: WorkbenchEvent): TerminalRow[] {
  const payload = event.payload ?? {};
  const commandId = stringValue(payload.command_id) || undefined;
  if (event.type === "tool.started") {
    const toolName = stringValue(payload.name, stringValue(payload.tool, "tool"));
    return [{
      id: `${event.event_id}:tool-start`,
      sequence: event.sequence,
      timestamp: event.timestamp,
      tone: "system",
      text: `${toolName} started`,
      label: "tool",
    }];
  }
  if (event.type === "tool.output") {
    const toolName = stringValue(payload.tool, stringValue(payload.name, "tool"));
    const status = stringValue(payload.status, "completed").toUpperCase();
    const failed = ["FAILED", "ERROR", "CANCELLED", "BLOCKED"].includes(status);
    return [{
      id: `${event.event_id}:tool-output`,
      sequence: event.sequence,
      timestamp: event.timestamp,
      tone: failed ? "error" : "system",
      text: `${toolName} ${status.toLowerCase()}`,
      label: "tool",
    }];
  }
  if (event.type === "command.started") {
    return [{
      id: `${event.event_id}:start`,
      sequence: event.sequence,
      timestamp: event.timestamp,
      tone: "prompt",
      commandId,
      text: stringValue(payload.summary, stringValue(payload.tool_name, "Running command")),
    }];
  }
  if (event.type === "terminal.chunk" || event.type === "shell.stdout") {
    const text = stringValue(payload.text, stringValue(payload.output));
    const tone = stringValue(payload.stream) === "stderr" ? "stderr" : "stdout";
    return text.split(/\r?\n/).map((line, index) => ({
      id: `${event.event_id}:${index}`,
      sequence: event.sequence,
      timestamp: event.timestamp,
      tone,
      commandId,
      text: line || " ",
    }));
  }
  if (event.type === "command.completed") {
    const status = stringValue(payload.status, "COMPLETE").toUpperCase();
    const exitCode = typeof payload.exit_code === "number" ? payload.exit_code : null;
    const succeeded = status === "COMPLETE" && (exitCode === null || exitCode === 0);
    return [{
      id: `${event.event_id}:complete`,
      sequence: event.sequence,
      timestamp: event.timestamp,
      tone: succeeded ? "success" : "error",
      commandId,
      text: exitCode === null
        ? `Command ${status.toLowerCase()}.`
        : `Command exited with code ${exitCode}${succeeded ? "." : " (failed)."}`,
    }];
  }
  if (event.type.endsWith(".terminal") || event.type === "session.terminal") {
    const status = stringValue(payload.status, "COMPLETE").toUpperCase();
    return [{
      id: `${event.event_id}:terminal`,
      sequence: event.sequence,
      timestamp: event.timestamp,
      tone: ["COMPLETE", "COMPLETED"].includes(status) ? "success" : "error",
      text: `Session ${status.toLowerCase()}.`,
    }];
  }
  if (event.type === "task.review_ready") {
    return [{
      id: `${event.event_id}:review`,
      sequence: event.sequence,
      timestamp: event.timestamp,
      tone: "success",
      text: "Agent execution finished; review the scoped diff before accepting changes.",
    }];
  }
  if (event.type === "agent.phase") {
    return [{
      id: `${event.event_id}:phase`,
      sequence: event.sequence,
      timestamp: event.timestamp,
      tone: "system",
      text: stringValue(payload.summary, stringValue(payload.phase, "Agent activity")),
    }];
  }
  return [];
}

export function initialWorkbenchState(): WorkbenchState {
  return {
    status: "CONNECTING",
    lastSequence: 0,
    transcript: [],
    workers: {},
    workerOrder: [],
    toolActivity: [],
  };
}

export function reduceWorkbenchEvent(state: WorkbenchState, event: WorkbenchEvent): WorkbenchState {
  if (!Number.isFinite(event.sequence) || event.sequence <= state.lastSequence) return state;
  const next: WorkbenchState = {
    ...state,
    lastSequence: event.sequence,
  };
  const authoritativeStatus = authoritativeWorkbenchStatus(event);
  if (authoritativeStatus) next.status = authoritativeStatus;
  const rows = terminalRows(event);
  if (rows.length) {
    next.transcript = bounded([...state.transcript, ...rows], MAX_TERMINAL_ROWS);
  }
  return next;
}

export function reduceWorkbenchEvents(state: WorkbenchState, events: readonly WorkbenchEvent[]): WorkbenchState {
  let next = state;
  for (const event of events) next = reduceWorkbenchEvent(next, event);
  return next;
}

function activeWorker(status: string): boolean {
  return ["RUNNING", "WORKING", "CONNECTING"].includes(status.toUpperCase());
}

function completedWorker(status: string): boolean {
  return ["COMPLETE", "COMPLETED", "INTEGRATED"].includes(status.toUpperCase());
}

export function summarizeWorkbench(state: WorkbenchState): WorkbenchSummary {
  const workers = state.workerOrder.map((id) => state.workers[id]).filter(Boolean);
  const activeWorkers = workers.filter((worker) => activeWorker(worker.status)).length;
  const completedWorkers = workers.filter((worker) => completedWorker(worker.status)).length;
  const changedPathCount = new Set(workers.flatMap((worker) => worker.changedPaths)).size;
  const reportedChangedFiles = workers.reduce((sum, worker) => sum + worker.changedFileCount, 0);
  const changedFiles = changedPathCount || reportedChangedFiles;
  const toolActivity = state.toolActivity ?? [];
  const intelligenceEvents = toolActivity.filter((activity) => isIntelligenceTool(activity.toolName)).length;
  const verification = toolActivity.filter((activity) => isVerificationTool(activity.toolName));
  const verificationEvents = verification.length;
  const latestVerificationStatus = verification.at(-1)?.status.toUpperCase() ?? "";
  const normalizedStatus = state.status.toUpperCase();
  const allWorkersComplete = workers.length > 0 && completedWorkers === workers.length;
  let phase: WorkbenchPhase = "ready";

  if (["FAILED", "BLOCKED", "CANCELLED", "REJECTED", "COMPLETE_WITH_TOOL_ERRORS"].includes(normalizedStatus)) {
    phase = "blocked";
  } else if (normalizedStatus === "COMPLETE") {
    phase = "complete";
  } else if (activeWorkers > 0) {
    phase = "implementing";
  } else if (latestVerificationStatus === "STARTED") {
    phase = "verifying";
  } else if (allWorkersComplete && COMPLETE_TOOL_STATUSES.has(latestVerificationStatus)) {
    phase = "complete";
  } else if (intelligenceEvents > 0) {
    phase = "understanding";
  } else if (["RUNNING", "WORKING", "ACTIVE"].includes(normalizedStatus)) {
    phase = "implementing";
  }

  return {
    phase,
    workerCount: workers.length,
    activeWorkers,
    completedWorkers,
    changedFiles,
    intelligenceEvents,
    verificationEvents,
  };
}
