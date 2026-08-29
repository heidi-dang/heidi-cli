import React from "react";
import type { DirectWorkerState } from "./state.js";
import { displayClock, Metric, NativeWorkbenchStyles, StatusDot } from "./native-workbench-ui.js";

export type DirectWorkerTab = "activity" | "changes" | "terminal";

type Props = {
  workers: Record<string, DirectWorkerState>;
  workerOrder: string[];
  selectedWorkerId: string | null;
  selectedTab: DirectWorkerTab;
  connection: string;
  actionStatus: string;
  changesText: string;
  terminalText: string;
  onSelectWorker: (workerId: string) => void;
  onSelectTab: (tab: DirectWorkerTab) => void;
  onRefreshChanges: () => void;
  onRefreshTerminal: () => void;
  onPin: () => void;
  onExpand: () => void;
  onStopCommand?: () => void;
  canStopCommand?: boolean;
  updateCenter?: React.ReactNode;
};

function activeStatus(status: string): boolean {
  return ["RUNNING", "WORKING", "CONNECTING"].includes(status.toUpperCase());
}

function completeStatus(status: string): boolean {
  return ["COMPLETE", "COMPLETED", "INTEGRATED"].includes(status.toUpperCase());
}

export function DirectWorkersView({
  workers,
  workerOrder,
  selectedWorkerId,
  selectedTab,
  connection,
  actionStatus,
  changesText,
  terminalText,
  onSelectWorker,
  onSelectTab,
  onRefreshChanges,
  onRefreshTerminal,
  onPin,
  onExpand,
  onStopCommand,
  canStopCommand = false,
  updateCenter,
}: Props) {
  const orderedWorkers = workerOrder.map((id) => workers[id]).filter(Boolean);
  const selected = (selectedWorkerId && workers[selectedWorkerId]) || orderedWorkers[0] || null;
  const activeCount = orderedWorkers.filter((worker) => activeStatus(worker.status)).length;
  const completeCount = orderedWorkers.filter((worker) => completeStatus(worker.status)).length;
  const changedFiles = new Set(orderedWorkers.flatMap((worker) => worker.changedPaths)).size;
  const runningCommands = orderedWorkers.reduce((sum, worker) => sum + worker.activeCommandIds.length, 0);
  const phase = activeCount > 0 ? "Implementing" : completeCount === orderedWorkers.length && orderedWorkers.length ? "Verifying" : "Ready";
  const connectionStatus = connection.toLowerCase().includes("error") || connection.toLowerCase().includes("failed")
    ? "FAILED"
    : connection.toLowerCase().includes("live")
      ? "RUNNING"
      : "READY";

  return <section className="cptr-native" aria-label="CPTR developer workbench">
    <NativeWorkbenchStyles />
    <header className="cptr-native-head">
      <div className="cptr-native-brand">
        <span className="cptr-native-mark" aria-hidden="true">CP</span>
        <div className="cptr-native-title">
          <strong>CPTR Workbench</strong>
          <span>ChatGPT Direct Coding · {phase}</span>
        </div>
      </div>
      <div className="cptr-native-actions">
        <span className="cptr-status"><StatusDot status={connectionStatus} />{connection}</span>
        <button type="button" onClick={onPin}>Pin</button>
        <button className="primary" type="button" onClick={onExpand}>Open Workbench</button>
      </div>
    </header>

    {updateCenter}

    <div className="cptr-native-body">
      <div className="cptr-summary">
        <div className="cptr-summary-main">
          <strong>{phase}</strong>
          <span>{activeCount ? `${activeCount} worker${activeCount === 1 ? "" : "s"} executing isolated changes.` : "Implementation lanes are synchronized and ready for verification."}</span>
        </div>
        <Metric value={orderedWorkers.length} label="workers" />
        <Metric value={changedFiles} label="changed files" />
        <Metric value={runningCommands} label="commands" />
      </div>

      <div className="cptr-rail" aria-label="Development phases">
        <div className="cptr-rail-step"><StatusDot status="COMPLETE" /><b>Understand</b><span>FDX-first</span></div>
        <div className="cptr-rail-step"><StatusDot status={activeCount ? "RUNNING" : completeCount ? "COMPLETE" : "READY"} /><b>Implement</b><span>{completeCount}/{orderedWorkers.length}</span></div>
        <div className="cptr-rail-step"><StatusDot status={!activeCount && completeCount ? "RUNNING" : "READY"} /><b>Verify</b><span>{!activeCount && completeCount ? "next" : "waiting"}</span></div>
      </div>

      <nav className="cptr-native-nav" aria-label="Workbench views">
        <button type="button" className={selectedTab === "activity" ? "selected" : ""} onClick={() => onSelectTab("activity")}>Overview</button>
        <button type="button" className={selectedTab === "changes" ? "selected" : ""} onClick={() => onSelectTab("changes")}>Changes</button>
        <button type="button" className={selectedTab === "terminal" ? "selected" : ""} onClick={() => onSelectTab("terminal")}>Terminal</button>
      </nav>

      {selectedTab === "activity" ? <div className="cptr-panel">
        <div className="cptr-panel-head">
          <div><strong>Direct Coding Workers</strong><span>Model-free isolated Git worktrees controlled by ChatGPT.</span></div>
          <span className="cptr-status"><StatusDot status={activeCount ? "RUNNING" : "COMPLETE"} />{activeCount ? `${activeCount} active` : "settled"}</span>
        </div>
        <div className="cptr-worker-list" role="tablist" aria-label="Direct coding workers">
          {orderedWorkers.map((worker) => <button
            type="button"
            key={worker.workerId}
            className={`cptr-worker ${selected?.workerId === worker.workerId ? "selected" : ""}`}
            onClick={() => onSelectWorker(worker.workerId)}
            role="tab"
            aria-selected={selected?.workerId === worker.workerId}
          >
            <StatusDot status={worker.status} />
            <span className="cptr-worker-copy">
              <strong>{worker.name}</strong>
              <span>{worker.responsibility || "Direct coding"}</span>
              <small>{worker.summary || worker.status}</small>
            </span>
            <span className="cptr-worker-meta"><b>{worker.status}</b><small>{worker.changedFileCount} changed</small></span>
          </button>)}
        </div>

        {selected ? <div className="cptr-panel" style={{ marginTop: 12 }}>
          <div className="cptr-panel-head"><div><strong>{selected.name} activity</strong><span>{selected.repoPath}</span></div></div>
          <div className="cptr-activity">
            {selected.activity.length ? [...selected.activity].reverse().slice(0, 10).map((item) => <div className="cptr-activity-row" key={item.id}>
              <time>{displayClock(item.timestamp)}</time>
              <StatusDot status={item.status} />
              <div><strong>{item.status}</strong><span>{item.summary}</span></div>
            </div>) : <div className="cptr-empty"><strong>No worker activity yet</strong><span>ChatGPT will update this lane as work progresses.</span></div>}
          </div>
        </div> : <div className="cptr-empty"><strong>Waiting for a worker</strong><span>ChatGPT creates workers only when isolated parallel execution is useful.</span></div>}
      </div> : null}

      {selectedTab === "changes" ? <div className="cptr-panel">
        <div className="cptr-panel-head">
          <div><strong>Changed files</strong><span>{selected ? `${selected.name} · ${selected.changedFileCount} changed` : "No selected worker"}</span></div>
          <button type="button" onClick={onRefreshChanges}>Refresh</button>
        </div>
        <pre className="cptr-code">{changesText || (selected?.changedPaths.length ? selected.changedPaths.join("\n") : "No changed files.")}</pre>
      </div> : null}

      {selectedTab === "terminal" ? <div className="cptr-panel">
        <div className="cptr-panel-head">
          <div><strong>Recent command output</strong><span>Loaded on demand. Raw terminal output is never the default UI stream.</span></div>
          <div className="cptr-native-actions">
            {onStopCommand ? <button type="button" className="danger" disabled={!canStopCommand} onClick={onStopCommand}>Stop</button> : null}
            <button type="button" onClick={onRefreshTerminal}>Refresh output</button>
          </div>
        </div>
        <pre className="cptr-code">{terminalText || "No command output loaded."}</pre>
      </div> : null}
    </div>

    <footer className="cptr-native-foot">
      <span>{actionStatus || "ChatGPT remains the reasoning and orchestration layer."}</span>
      <span>{changedFiles} files · {completeCount}/{orderedWorkers.length} workers complete</span>
    </footer>
  </section>;
}
