export type UiUsagePeriodDisplay = {
  requests: number;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  simulatedCostUsd: string;
};

export type UiEngineeringDisplay = {
  model: string | null;
  reliability: number;
  verificationRatio: number;
  toolCalls: number;
} | null;

export type UiBenchmarkDisplay = {
  model: string | null;
  bestScore: number;
  averageScore: number;
  maxScore: number;
  attempts: number;
  perfectRuns: number;
} | null;

export type UiOverviewDisplay = {
  status: "ok" | "degraded" | "unavailable";
  databaseStatus: string;
  uptimeSeconds: number;
  requestCount: number;
  requestP95Ms: number;
  eventLoopLagMs: number;
  workspaceCount: number;
  availableWorkspaceCount: number;
  modelCount: number;
  defaultModel: string | null;
  mcpServerCount: number;
  sourceRevision: string | null;
  apiFamilies: string[];
  usageWeek: UiUsagePeriodDisplay;
  usageMonth: UiUsagePeriodDisplay;
  engineering: UiEngineeringDisplay;
  benchmark: UiBenchmarkDisplay;
  benchmarkSuite: string | null;
  benchmarkVersion: string | null;
};

function record(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function boundedNumber(value: unknown, max = 9999, decimals = 0): number {
  const numeric = typeof value === "number" && Number.isFinite(value) ? value : 0;
  const bounded = Math.max(0, Math.min(max, numeric));
  const scale = 10 ** decimals;
  return Math.round(bounded * scale) / scale;
}

function boundedString(value: unknown, maxLength = 120): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  return trimmed.slice(0, maxLength);
}

function boundedDecimal(value: unknown): string {
  const text = typeof value === "number" && Number.isFinite(value)
    ? String(Math.max(0, value))
    : boundedString(value, 40) ?? "0";
  return /^\d+(?:\.\d{1,18})?$/.test(text) ? text : "0";
}

function usagePeriod(value: unknown): UiUsagePeriodDisplay {
  const period = record(value) ?? {};
  const inputTokens = boundedNumber(period.input_tokens_estimated, 1_000_000_000_000);
  const outputTokens = boundedNumber(period.output_tokens_estimated, 1_000_000_000_000);
  return {
    requests: boundedNumber(period.requests, 1_000_000_000),
    inputTokens,
    outputTokens,
    totalTokens: boundedNumber(period.total_tokens_estimated, 2_000_000_000_000) || inputTokens + outputTokens,
    simulatedCostUsd: boundedDecimal(period.simulated_cost_usd),
  };
}

export function findUiOverviewMetadata(value: unknown, depth = 0): unknown | null {
  if (depth > 7) return null;
  const current = record(value);
  if (!current) return null;
  if (record(current["cptr/ui"])) return current["cptr/ui"];
  for (const key of ["_meta", "params", "result", "toolResult", "structuredContent"]) {
    const found = findUiOverviewMetadata(current[key], depth + 1);
    if (found) return found;
  }
  return null;
}

export function normalizeUiOverview(value: unknown): UiOverviewDisplay {
  const root = record(value) ?? {};
  const system = record(root.system) ?? {};
  const requests = record(system.requests) ?? {};
  const requestLatency = record(requests.latency_ms) ?? {};
  const eventLoop = record(system.event_loop) ?? {};
  const workspaces = record(root.workspaces) ?? {};
  const models = record(root.models) ?? {};
  const mcpServers = record(root.mcp_servers) ?? {};
  const usage = record(root.mcp_usage) ?? {};
  const engineeringRoot = record(root.engineering) ?? {};
  const benchmarkRoot = record(root.coding_benchmark) ?? {};
  const apiSurface = record(root.api_surface) ?? {};

  const rawStatus = boundedString(root.status, 24)?.toLowerCase();
  const status: UiOverviewDisplay["status"] = rawStatus === "ok"
    ? "ok"
    : rawStatus === "degraded" ? "degraded" : "unavailable";
  const source = boundedString(apiSurface.source, 180);
  const revisionMatch = source?.match(/@([0-9a-f]{8,64})\b/i);
  const families = Array.isArray(apiSurface.families)
    ? apiSurface.families
        .map((item) => boundedString(item, 40))
        .filter((item): item is string => Boolean(item))
        .slice(0, 16)
    : [];

  const engineeringSessions = Array.isArray(engineeringRoot.sessions) ? engineeringRoot.sessions : [];
  const engineeringSession = record(engineeringSessions[0]);
  const engineering: UiEngineeringDisplay = engineeringSession
    ? {
        model: boundedString(engineeringSession.model_reported, 120)
          ?? boundedString(engineeringSession.model_canonical, 120),
        reliability: boundedNumber(engineeringSession.reliability, 1, 4),
        verificationRatio: boundedNumber(engineeringSession.verification_ratio, 1, 4),
        toolCalls: boundedNumber(engineeringSession.tool_calls, 1_000_000_000),
      }
    : null;

  const benchmarkModels = Array.isArray(benchmarkRoot.models) ? benchmarkRoot.models : [];
  const benchmarkLeader = record(benchmarkModels[0]);
  const maxScore = boundedNumber(benchmarkRoot.max_score, 10_000) || 100;
  const benchmark: UiBenchmarkDisplay = benchmarkLeader
    ? {
        model: boundedString(benchmarkLeader.model_reported, 120)
          ?? boundedString(benchmarkLeader.model_canonical, 120),
        bestScore: boundedNumber(benchmarkLeader.best_score, maxScore, 2),
        averageScore: boundedNumber(benchmarkLeader.average_score, maxScore, 2),
        maxScore,
        attempts: boundedNumber(benchmarkLeader.attempts, 1_000_000),
        perfectRuns: boundedNumber(benchmarkLeader.perfect_runs, 1_000_000),
      }
    : null;

  return {
    status,
    databaseStatus: boundedString(system.database, 24) ?? "unknown",
    uptimeSeconds: boundedNumber(system.uptime_seconds, 31_536_000),
    requestCount: boundedNumber(requests.count, 99_999_999),
    requestP95Ms: boundedNumber(requestLatency.p95, 60_000, 3),
    eventLoopLagMs: boundedNumber(eventLoop.last_lag_ms, 60_000, 3),
    workspaceCount: boundedNumber(workspaces.count),
    availableWorkspaceCount: boundedNumber(workspaces.available),
    modelCount: boundedNumber(models.count),
    defaultModel: boundedString(models.default_model, 160),
    mcpServerCount: boundedNumber(mcpServers.count),
    sourceRevision: revisionMatch?.[1]?.slice(0, 8) ?? null,
    apiFamilies: families,
    usageWeek: usagePeriod(usage.week),
    usageMonth: usagePeriod(usage.month),
    engineering,
    benchmark,
    benchmarkSuite: boundedString(benchmarkRoot.suite_id, 80),
    benchmarkVersion: boundedString(benchmarkRoot.suite_version, 40),
  };
}

export function uiOverviewUrl(streamUrl: string | undefined): string | null {
  if (!streamUrl) return null;
  try {
    const url = new URL(streamUrl);
    if (!/^https?:$/.test(url.protocol)) return null;
    return new URL("/ui/overview", url.origin).toString();
  } catch {
    return null;
  }
}
