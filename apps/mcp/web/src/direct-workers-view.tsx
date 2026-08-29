import React from "react";
import {
  isIntelligenceTool,
  isVerificationTool,
  type DirectWorkerState,
  type WorkbenchToolActivity,
} from "./state.js";
import { displayClock, Metric, NativeWorkbenchStyles, StatusDot } from "./native-workbench-ui.js";
import { useOpenAiDisplayMode, type ChatGptDisplayMode } from "./openai-globals.js";

export type DirectWorkerTab = "overview" | "workers" | "changes" | "intelligence" | "verification" | "terminal";

type Props = {
  workers: Record<string, DirectWorkerState>;
  workerOrder: string[];
  toolActivity?: WorkbenchToolActivity[];
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
  displayMode?: ChatGptDisplayMode;
};

const COMPLETE_TOOL_STATUSES = new Set(["COMPLETE", "COMPLETED", "SUCCESS", "SUCCEEDED", "PASSED"]);

function activeStatus(status: string): boolean {
  return ["RUNNING", "WORKING", "CONNECTING"].includes(status.toUpperCase());
}

function completeStatus(status: string): boolean {
  return ["COMPLETE", "COMPLETED", "INTEGRATED"].includes(status.toUpperCase());
}

function ToolActivityList({
  items,
  emptyTitle,
  emptyText,
}: {
  items: WorkbenchToolActivity[];
  emptyTitle: string;
  emptyText: string;
}) {
  if (!items.length) return <div className="cptr-empty"><strong>{emptyTitle}</strong><span>{emptyText}</span></div>;
  return <div className="cptr-activity">
    {[...items].reverse().slice(0, 16).map((item) => <div className="cptr-activity-row" key={item.id}>
      <time>{displayClock(item.timestamp)}</time>
      <StatusDot status={item.status} />
      <div><strong>{item.toolName}</strong><span>{item.summary}</span></div>
    </div>)}
  </div>;
}

export function DirectWorkersView({
  workers,
  workerOrder,
  toolActivity = [],
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
  displayMode,
}: Props) {
  const hostDisplayMode = useOpenAiDisplayMode();
  const mode = displayMode ?? hostDisplayMode;
  const detailed = mode === "fullscreen";
  const orderedWorkers = workerOrder.map((id) => workers[id]).filter(Boolean);
  const selected = (selectedWorkerId && workers[selectedWorkerId]) || orderedWorkers[0] || null;
  const activeCount = orderedWorkers.filter((worker) => activeStatus(worker.status)).length;
  const completeCount = orderedWorkers.filter((worker) => completeStatus(worker.status)).length;
  const allWorkersComplete = orderedWorkers.length > 0 && completeCount === orderedWorkers.length;
  const changedPathCount = new Set(orderedWorkers.flatMap((worker) => worker.changedPaths)).size;
  const reportedChangedFiles = orderedWorkers.reduce((sum, worker) => sum + worker.changedFileCount, 0);
  const changedFiles = changedPathCount || reportedChangedFiles;
  const runningCommands = orderedWorkers.reduce((sum, worker) => sum + worker.activeCommandIds.length, 0);
  const intelligence = toolActivity.filter((activity) => isIntelligenceTool(activity.toolName));
  const verification = toolActivity.filter((activity) => isVerificationTool(activity.toolName));
  const latestVerificationStatus = verification.at(-1)?.status.toUpperCase() ?? "";
  const verificationActive = latestVerificationStatus === "STARTED";
  const verificationComplete = COMPLETE_TOOL_STATUSES.has(latestVerificationStatus);
  const phase = activeCount > 0
    ? "Implementing"
    : verificationActive
      ? "Verifying"
      : allWorkersComplete && verificationComplete
        ? "Complete"
        : allWorkersComplete
          ? "Ready to verify"
          : intelligence.length
            ? "Understanding"
            : "Ready";
  const connectionStatus = connection.toLowerCase().includes("error") || connection.toLowerCase().includes("failed")
    ? "FAILED"
    : connection.toLowerCase().includes("live")
      ? "RUNNING"
      : "READY";
  const latestActivity = toolActivity.slice(-8);
  const summaryText = activeCount
    ? `${activeCount} worker${activeCount === 1 ? "" : "s"} executing isolated changes.`
    : phase === "Verifying"
      ? `${completeCount}/${orderedWorkers.length} workers settled; verification is running.`
      : phase === "Complete"
        ? `${completeCount}/${orderedWorkers.length} workers settled; latest verification completed.`
        : completeCount
          ? `${completeCount}/${orderedWorkers.length} workers settled; ready for verification.`
          : "ChatGPT is preparing the development workflow.";
  const verifyStatus = verificationActive ? "RUNNING" : verificationComplete ? "COMPLETE" : "READY";

  return <section className="cptr-native" aria-label="CPTR developer workbench" data-display-mode={mode}>
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
        {!detailed ? <button className="primary" type="button" onClick={onExpand}>Open Workbench</button> : null}
      </div>
    </header>

    {updateCenter}

    <div className="cptr-native-body">
      <div className="cptr-summary">
        <div className="cptr-summary-main">
          <strong>{phase}</strong>
          <span>{summaryText}</span>
        </div>
        <Metric value={orderedWorkers.length} label="workers" />
        <Metric value={changedFiles} label="changed files" />
        <Metric value={verification.length} label="check events" />
      </div>

      {detailed ? <>
        <div className="cptr-rail" aria-label="Development phases">
          <div className="cptr-rail-step"><StatusDot status={intelligence.length ? "COMPLETE" : "READY"} /><b>Understand</b><span>{intelligence.length ? `${intelligence.length} FDX` : "FDX-first"}</span></div>
          <div className="cptr-rail-step"><StatusDot status={activeCount ? "RUNNING" : completeCount ? "COMPLETE" : "READY"} /><b>Implement</b><span>{completeCount}/{orderedWorkers.length}</span></div>
          <div className="cptr-rail-step"><StatusDot status={verifyStatus} /><b>Verify</b><span>{verificationActive ? "running" : verificationComplete ? "complete" : "waiting"}</span></div>
        </div>

        <nav className="cptr-native-nav" aria-label="Workbench views">
          {([
            ["overview", "Overview"],
            ["workers", "Workers"],
            ["changes", "Changes"],
            ["intelligence", "Intelligence"],
            ["verification", "Verification"],
            ["terminal", "Terminal"],
          ] as Array<[DirectWorkerTab, string]>).map(([tab, label]) => <button
            type="button"
            key={tab}
            className={selectedTab === tab ? "selected" : ""}
            onClick={() => onSelectTab(tab)}
          >{label}</button>)}
        </nav>

        {selectedTab === "overview" ? <div className="cptr-panel">
          <div className="cptr-panel-head">
            <div><strong>Development overview</strong><span>One authoritative view of ChatGPT reasoning support, execution lanes, and validation.</span></div>
            <span className="cptr-status"><StatusDot status={activeCount ? "RUNNING" : phase === "Complete" ? "COMPLETE" : "READY"} />{runningCommands ? `${runningCommands} commands active` : "execution settled"}</span>
          </div>
          <ToolActivityList
            items={latestActivity}
            emptyTitle="Workbench ready"
            emptyText="FDX, code, test, browser, and verification lifecycle events will appear here."
          />
        </div> : null}

        {selectedTab === "workers" ? <div className="cptr-panel">
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
              {selected.activity.length ? [...selected.activity].reverse().slice(0, 12).map((item) => <div className="cptr-activity-row" key={item.id}>
                <time>{displayClock(item.timestamp)}</time>
                <StatusDot status={item.status} />
                <div><strong>{item.status}</strong><span>{item.summary}</span></div>
              </div>) : <div className="cptr-empty"><strong>No worker activity yet</strong><span>ChatGPT will update this lane as work progresses.</span></div>}
            </div>
          </div> : null}
        </div> : null}

        {selectedTab === "changes" ? <div className="cptr-panel">
          <div className="cptr-panel-head">
            <div><strong>Changed files</strong><span>{selected ? `${selected.name} · ${selected.changedFileCount} changed` : "No selected worker"}</span></div>
            <button type="button" onClick={onRefreshChanges}>Refresh</button>
          </div>
          <pre className="cptr-code">{changesText || (selected?.changedPaths.length ? selected.changedPaths.join("\n") : "No changed files.")}</pre>
        </div> : null}

        {selectedTab === "intelligence" ? <div className="cptr-panel">
          <div className="cptr-panel-head"><div><strong>FDX Intelligence</strong><span>Repository understanding, impact, references, architecture, and verification planning.</span></div><span>{intelligence.length} events</span></div>
          <ToolActivityList items={intelligence} emptyTitle="No FDX activity yet" emptyText="ChatGPT will use FDX when repository intelligence materially improves the task." />
        </div> : null}

        {selectedTab === "verification" ? <div className="cptr-panel">
          <div className="cptr-panel-head"><div><strong>Verification Center</strong><span>Tests, builds, type checks, browser verification, and release-readiness evidence.</span></div><span>{verification.length} checks</span></div>
          <ToolActivityList items={verification} emptyTitle="Verification not started" emptyText="Evidence appears here when ChatGPT runs checks against the affected workflow." />
        </div> : null}

        {selectedTab === "terminal" ? <div className="cptr-panel">
          <div className="cptr-panel-head">
            <div><strong>Terminal diagnostics</strong><span>Loaded on demand. Raw redacted output is never the default UI stream.</span></div>
            <div className="cptr-native-actions">
              {onStopCommand ? <button type="button" className="danger" disabled={!canStopCommand} onClick={onStopCommand}>Stop</button> : null}
              <button type="button" onClick={onRefreshTerminal}>Refresh output</button>
            </div>
          </div>
          <pre className="cptr-code">{terminalText || "No command output loaded."}</pre>
        </div> : null}
      </> : null}
    </div>

    <footer className="cptr-native-foot">
      <span>{actionStatus || "ChatGPT remains the reasoning and orchestration layer."}</span>
      <span>{changedFiles} files · {completeCount}/{orderedWorkers.length} workers complete</span>
    </footer>
  </section>;
}
