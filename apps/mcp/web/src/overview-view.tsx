import React from "react";

import type { UiOverviewDisplay, UiUsagePeriodDisplay } from "./overview-model.js";

function formatUptime(seconds: number): string {
  const totalMinutes = Math.floor(Math.max(0, seconds) / 60);
  const days = Math.floor(totalMinutes / 1440);
  const hours = Math.floor((totalMinutes % 1440) / 60);
  const minutes = totalMinutes % 60;
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function formatTokens(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(value >= 10_000_000_000 ? 1 : 2)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(value >= 10_000_000 ? 1 : 2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(value >= 10_000 ? 1 : 2)}K`;
  return String(Math.round(value));
}

function formatUsd(value: string): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return "$0.0000";
  if (numeric < 1) return `$${numeric.toFixed(4)}`;
  return `$${numeric.toFixed(2)}`;
}

function percent(value: number): string {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

function metric(value: React.ReactNode, label: string, detail?: React.ReactNode) {
  return <div className="overview-metric">
    <strong>{value}</strong>
    <span>{label}</span>
    {detail ? <small>{detail}</small> : null}
  </div>;
}

function usagePeriod(label: string, period: UiUsagePeriodDisplay) {
  return <div className="overview-usage-period">
    <div className="overview-usage-period-heading">
      <span>{label}</span>
      <small>{period.requests} requests</small>
    </div>
    <strong>{formatTokens(period.totalTokens)}</strong>
    <span>estimated tokens</span>
    <small>{formatTokens(period.inputTokens)} in · {formatTokens(period.outputTokens)} out</small>
    <b>{formatUsd(period.simulatedCostUsd)}</b>
    <small>API-equivalent simulated cost</small>
  </div>;
}

export function OverviewView({
  overview,
  loading,
  error,
  refreshedAt,
  onRefresh,
}: {
  overview: UiOverviewDisplay | null;
  loading: boolean;
  error: string;
  refreshedAt: string;
  onRefresh: () => void;
}) {
  if (!overview) {
    return <section className="overview-card overview-empty" aria-label="CPTR overview">
      <div>
        <strong>Overview unavailable</strong>
        <span>{error || (loading ? "Loading CPTR runtime summary…" : "Open the Workbench again to refresh its scoped UI ticket.")}</span>
      </div>
      <button type="button" onClick={onRefresh} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button>
    </section>;
  }

  const statusLabel = overview.status === "ok" ? "Healthy" : overview.status === "degraded" ? "Degraded" : "Unavailable";
  return <section className="overview-card" aria-label="CPTR overview">
    <header className="overview-header">
      <div className="overview-heading">
        <span className={`overview-status overview-status-${overview.status}`} aria-hidden="true" />
        <div>
          <strong>CPTR overview</strong>
          <span>{statusLabel} · DB {overview.databaseStatus} · uptime {formatUptime(overview.uptimeSeconds)}</span>
        </div>
      </div>
      <div className="overview-actions">
        {refreshedAt ? <small>Updated {refreshedAt}</small> : null}
        <button type="button" onClick={onRefresh} disabled={loading}>{loading ? "Refreshing…" : "Refresh"}</button>
      </div>
    </header>

    <div className="overview-grid">
      {metric(`${overview.availableWorkspaceCount}/${overview.workspaceCount}`, "workspaces", "available")}
      {metric(overview.modelCount, "models", overview.defaultModel ?? "no default")}
      {metric(overview.mcpServerCount, "MCP servers", "configured")}
      {metric(overview.requestCount, "requests", `p95 ${overview.requestP95Ms} ms`)}
    </div>

    <div className="overview-analytics">
      <section className="overview-analytics-panel" aria-label="Model usage and simulated cost">
        <div className="overview-analytics-heading">
          <div>
            <strong>Model usage &amp; simulated cost</strong>
            <span>Estimated · MCP-visible tokens · database-backed</span>
          </div>
          <small>UTC · Monday week</small>
        </div>
        <div className="overview-usage-grid">
          {usagePeriod("This week", overview.usageWeek)}
          {usagePeriod("This month", overview.usageMonth)}
        </div>
        <p className="overview-disclaimer">UTF-8 byte token estimate. API-equivalent simulation only — not your ChatGPT bill; hidden prompt context, reasoning, cache usage, and final-answer tokens are not visible to MCP.</p>
      </section>

      <section className="overview-analytics-panel" aria-label="Coding benchmark">
        <div className="overview-analytics-heading">
          <div>
            <strong>Coding benchmark</strong>
            <span>{overview.benchmarkSuite ?? "cptr-python-core"}{overview.benchmarkVersion ? ` · v${overview.benchmarkVersion}` : ""}</span>
          </div>
          <small>server-owned grader</small>
        </div>
        <div className="overview-benchmark-grid">
          <div className="overview-benchmark-block">
            <span className="overview-benchmark-label comparable">Comparable standardized</span>
            {overview.benchmark ? <>
              <strong>{overview.benchmark.bestScore}/{overview.benchmark.maxScore}</strong>
              <span>{overview.benchmark.model ?? "Unreported model"}</span>
              <small>{overview.benchmark.attempts} attempts · avg {overview.benchmark.averageScore}/{overview.benchmark.maxScore} · {overview.benchmark.perfectRuns} perfect</small>
            </> : <>
              <strong>—</strong>
              <span>No standardized run yet</span>
              <small>Start with cptr_benchmark · hidden randomized grading</small>
            </>}
          </div>
          <div className="overview-benchmark-block">
            <span className="overview-benchmark-label">Observed real-work · not comparable</span>
            {overview.engineering ? <>
              <strong>{percent(overview.engineering.reliability)}</strong>
              <span>{overview.engineering.model ?? "Unreported model"}</span>
              <small>reliability · verification {percent(overview.engineering.verificationRatio)} · {overview.engineering.toolCalls} tool calls</small>
            </> : <>
              <strong>—</strong>
              <span>No attributed engineering session yet</span>
              <small>Operational evidence appears as ChatGPT uses MCP coding tools</small>
            </>}
          </div>
        </div>
        <p className="overview-disclaimer">Only the standardized suite is suitable for model-to-model comparison. Real-work task difficulty and scope differ, so operational scores are intentionally excluded from the leaderboard.</p>
      </section>
    </div>

    <footer className="overview-footer">
      <span>event loop {overview.eventLoopLagMs} ms</span>
      {overview.sourceRevision ? <span>computer@{overview.sourceRevision}</span> : null}
      <span className="overview-families" title={overview.apiFamilies.join(", ")}>{overview.apiFamilies.join(" · ") || "scoped control API"}</span>
    </footer>
  </section>;
}
