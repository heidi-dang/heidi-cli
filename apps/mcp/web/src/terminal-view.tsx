import React, { useEffect, useMemo, useRef, useState } from "react";
import type { TerminalRow, WorkbenchToolActivity } from "./state.js";
import { NativeWorkbenchStyles, StatusDot } from "./native-workbench-ui.js";
import { useOpenAiDisplayMode, type ChatGptDisplayMode } from "./openai-globals.js";

export type TerminalViewProps = {
  rows: TerminalRow[];
  toolActivity?: WorkbenchToolActivity[];
  status: string;
  connection: string;
  targetLabel: string;
  actionStatus?: string;
  updateCenter?: React.ReactNode;
  canStop: boolean;
  onStop: () => void;
  onCopy: () => void;
  onPin: () => void;
  onExpand: () => void;
  displayMode?: ChatGptDisplayMode;
};

type StandaloneWorkbenchTab = "overview" | "intelligence" | "verification" | "terminal";

function isDiagnosticOutput(row: TerminalRow): boolean {
  return ["stdout", "stderr", "prompt"].includes(row.tone);
}

function verificationTool(toolName: string): boolean {
  return /(?:test|build|typecheck|verify|release_readiness|chrome_browser)/i.test(toolName);
}

function intelligenceTool(toolName: string): boolean {
  return toolName === "cptr_fdx_intelligence" || toolName.toLowerCase().includes("fdx");
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
      <time>{new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>
      <StatusDot status={item.status} />
      <div><strong>{item.toolName}</strong><span>{item.summary}</span></div>
    </div>)}
  </div>;
}

export function TerminalView({
  rows,
  toolActivity = [],
  status,
  connection,
  targetLabel,
  actionStatus,
  updateCenter,
  canStop,
  onStop,
  onCopy,
  onPin,
  onExpand,
  displayMode,
}: TerminalViewProps) {
  const viewport = useRef<HTMLDivElement>(null);
  const hostDisplayMode = useOpenAiDisplayMode();
  const mode = displayMode ?? hostDisplayMode;
  const detailed = mode === "fullscreen";
  const [selectedTab, setSelectedTab] = useState<StandaloneWorkbenchTab>("overview");
  const [follow, setFollow] = useState(true);
  const recentRows = useMemo(() => rows.filter((row) => !isDiagnosticOutput(row)).slice(-5), [rows]);
  const intelligence = toolActivity.filter((activity) => intelligenceTool(activity.toolName));
  const verification = toolActivity.filter((activity) => verificationTool(activity.toolName));

  useEffect(() => {
    if (!detailed || selectedTab !== "terminal" || !follow) return;
    const element = viewport.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [rows, detailed, selectedTab, follow]);

  const onScroll = () => {
    const element = viewport.current;
    if (!element) return;
    setFollow(element.scrollHeight - element.scrollTop - element.clientHeight < 32);
  };

  const normalized = status.toUpperCase();
  const phase = ["COMPLETE", "COMPLETED"].includes(normalized)
    ? "Complete"
    : ["FAILED", "BLOCKED", "CANCELLED", "REJECTED", "COMPLETE_WITH_TOOL_ERRORS"].includes(normalized)
      ? "Needs attention"
      : ["RUNNING", "WORKING", "ACTIVE", "CONNECTING"].includes(normalized)
        ? "Working"
        : intelligence.length
          ? "Understanding"
          : "Ready";

  return <section className="cptr-native" aria-label="CPTR developer workbench" data-display-mode={mode}>
    <NativeWorkbenchStyles />
    <header className="cptr-native-head">
      <div className="cptr-native-brand">
        <span className="cptr-native-mark" aria-hidden="true">CP</span>
        <div className="cptr-native-title">
          <strong>CPTR Workbench</strong>
          <span title={targetLabel}>{targetLabel}</span>
        </div>
      </div>
      <div className="cptr-native-actions">
        <span className="cptr-status"><StatusDot status={status} />{phase}</span>
        <button type="button" onClick={onPin}>Pin</button>
        {!detailed ? <button className="primary" type="button" onClick={onExpand}>Open Workbench</button> : null}
      </div>
    </header>

    {updateCenter}

    <div className="cptr-native-body">
      <div className="cptr-summary">
        <div className="cptr-summary-main">
          <strong>{phase}</strong>
          <span>{connection}. ChatGPT controls execution; raw command output stays outside the default conversation surface.</span>
        </div>
        <div className="cptr-metric"><b>{toolActivity.length}</b><span>tool events</span></div>
        <div className="cptr-metric"><b>{intelligence.length}</b><span>FDX intelligence</span></div>
        <div className="cptr-metric"><b>{verification.length}</b><span>verification</span></div>
      </div>

      {detailed ? <>
        <div className="cptr-rail" aria-label="Development phases">
          <div className="cptr-rail-step"><StatusDot status={intelligence.length ? "COMPLETE" : rows.length ? "COMPLETE" : "READY"} /><b>Understand</b><span>{intelligence.length ? `${intelligence.length} FDX` : "context"}</span></div>
          <div className="cptr-rail-step"><StatusDot status={canStop ? "RUNNING" : normalized === "COMPLETE" ? "COMPLETE" : "READY"} /><b>Execute</b><span>{canStop ? "active" : "settled"}</span></div>
          <div className="cptr-rail-step"><StatusDot status={verification.length ? "RUNNING" : normalized === "COMPLETE" ? "COMPLETE" : "READY"} /><b>Verify</b><span>{verification.length || "waiting"}</span></div>
        </div>

        <nav className="cptr-native-nav" aria-label="Workbench views">
          {([
            ["overview", "Overview"],
            ["intelligence", "Intelligence"],
            ["verification", "Verification"],
            ["terminal", "Terminal"],
          ] as Array<[StandaloneWorkbenchTab, string]>).map(([tab, label]) => <button
            type="button"
            key={tab}
            className={selectedTab === tab ? "selected" : ""}
            onClick={() => setSelectedTab(tab)}
          >{label}</button>)}
        </nav>

        {selectedTab === "overview" ? <div className="cptr-panel">
          <div className="cptr-panel-head"><div><strong>Recent activity</strong><span>Compact lifecycle and tool status, with raw output kept separate.</span></div></div>
          {recentRows.length ? <div className="cptr-compact-log">
            {recentRows.map((row) => <div className="cptr-compact-row" key={row.id}>
              <b>{row.label ?? row.tone}</b>
              <code>{row.text}</code>
            </div>)}
          </div> : <ToolActivityList items={toolActivity.slice(-8)} emptyTitle="Workbench ready" emptyText="ChatGPT tool lifecycle and verification checkpoints will appear here." />}
        </div> : null}

        {selectedTab === "intelligence" ? <div className="cptr-panel">
          <div className="cptr-panel-head"><div><strong>FDX Intelligence</strong><span>Repository understanding, references, impact, architecture, and verification planning.</span></div><span>{intelligence.length} events</span></div>
          <ToolActivityList items={intelligence} emptyTitle="No FDX activity yet" emptyText="ChatGPT will use FDX when repository intelligence materially improves the task." />
        </div> : null}

        {selectedTab === "verification" ? <div className="cptr-panel">
          <div className="cptr-panel-head"><div><strong>Verification Center</strong><span>Tests, builds, type checks, browser verification, and release-readiness evidence.</span></div><span>{verification.length} checks</span></div>
          <ToolActivityList items={verification} emptyTitle="Verification not started" emptyText="Evidence appears here when ChatGPT validates the affected workflow." />
        </div> : null}

        {selectedTab === "terminal" ? <div className="cptr-panel">
          <div className="cptr-panel-head">
            <div><strong>Terminal diagnostics</strong><span>Raw redacted output is available only in this explicit fullscreen surface.</span></div>
            <div className="cptr-native-actions">
              <button className="danger" disabled={!canStop} onClick={onStop}>Stop</button>
              <button disabled={!rows.length} onClick={onCopy}>Copy</button>
              {!follow ? <button onClick={() => setFollow(true)}>Latest</button> : null}
            </div>
          </div>
          <div ref={viewport} onScroll={onScroll} tabIndex={0} aria-label="Redacted terminal diagnostics">
            <pre className="cptr-code">{rows.length ? rows.map((row) => row.text).join("\n") : "No command output available."}</pre>
          </div>
        </div> : null}
      </> : <div className="cptr-panel">
        <div className="cptr-panel-head"><div><strong>Recent activity</strong><span>Lifecycle status only; open the Workbench for intelligence, verification, changes, and diagnostics.</span></div></div>
        {recentRows.length ? <div className="cptr-compact-log">
          {recentRows.map((row) => <div className="cptr-compact-row" key={row.id}>
            <b>{row.label ?? row.tone}</b>
            <code>{row.text}</code>
          </div>)}
        </div> : <div className="cptr-empty"><strong>Ready for CPTR activity</strong><span>Lifecycle and verification checkpoints will appear here as ChatGPT works.</span></div>}
      </div>}
    </div>

    <footer className="cptr-native-foot">
      <span>{actionStatus || "ChatGPT remains the reasoning and orchestration layer."}</span>
      <span>{connection}</span>
    </footer>
  </section>;
}
