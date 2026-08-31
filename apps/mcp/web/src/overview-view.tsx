import React from "react";

import type { UiOverviewDisplay } from "./overview-model.js";

function formatUptime(seconds: number): string {
  const totalMinutes = Math.floor(Math.max(0, seconds) / 60);
  const days = Math.floor(totalMinutes / 1440);
  const hours = Math.floor((totalMinutes % 1440) / 60);
  const minutes = totalMinutes % 60;
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function metric(value: React.ReactNode, label: string, detail?: React.ReactNode) {
  return <div className="overview-metric">
    <strong>{value}</strong>
    <span>{label}</span>
    {detail ? <small>{detail}</small> : null}
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

    <footer className="overview-footer">
      <span>event loop {overview.eventLoopLagMs} ms</span>
      {overview.sourceRevision ? <span>computer@{overview.sourceRevision}</span> : null}
      <span className="overview-families" title={overview.apiFamilies.join(", ")}>{overview.apiFamilies.join(" · ") || "scoped control API"}</span>
    </footer>
  </section>;
}
