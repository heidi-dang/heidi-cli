import React, { useEffect, useMemo, useRef, useState } from "react";
import type { TerminalRow } from "./state.js";
import { NativeWorkbenchStyles, StatusDot } from "./native-workbench-ui.js";

export type TerminalViewProps = {
  rows: TerminalRow[];
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
};

function isDiagnosticOutput(row: TerminalRow): boolean {
  return ["stdout", "stderr", "prompt"].includes(row.tone);
}

export function TerminalView({
  rows,
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
}: TerminalViewProps) {
  const viewport = useRef<HTMLDivElement>(null);
  const [showOutput, setShowOutput] = useState(false);
  const [follow, setFollow] = useState(true);
  const recentRows = useMemo(() => rows.filter((row) => !isDiagnosticOutput(row)).slice(-5), [rows]);

  useEffect(() => {
    if (!showOutput || !follow) return;
    const element = viewport.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [rows, follow, showOutput]);

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
        : "Ready";

  return <section className="cptr-native" aria-label="CPTR developer workbench">
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
        <button className="primary" type="button" onClick={onExpand}>Open Workbench</button>
      </div>
    </header>

    {updateCenter}

    <div className="cptr-native-body">
      <div className="cptr-summary">
        <div className="cptr-summary-main">
          <strong>{phase}</strong>
          <span>{connection}. ChatGPT controls execution; terminal output stays collapsed unless you ask for it.</span>
        </div>
        <div className="cptr-metric"><b>{rows.length}</b><span>activity rows</span></div>
        <div className="cptr-metric"><b>{canStop ? "1" : "0"}</b><span>active target</span></div>
        <div className="cptr-metric"><b>{showOutput ? "open" : "quiet"}</b><span>terminal</span></div>
      </div>

      <div className="cptr-rail" aria-label="Development phases">
        <div className="cptr-rail-step"><StatusDot status={rows.length ? "COMPLETE" : "READY"} /><b>Understand</b><span>context</span></div>
        <div className="cptr-rail-step"><StatusDot status={canStop ? "RUNNING" : normalized === "COMPLETE" ? "COMPLETE" : "READY"} /><b>Execute</b><span>{canStop ? "active" : "settled"}</span></div>
        <div className="cptr-rail-step"><StatusDot status={normalized === "COMPLETE" ? "COMPLETE" : "READY"} /><b>Verify</b><span>{normalized === "COMPLETE" ? "done" : "waiting"}</span></div>
      </div>

      <div className="cptr-panel">
        <div className="cptr-panel-head">
          <div><strong>Recent activity</strong><span>Compact lifecycle status instead of continuous terminal streaming.</span></div>
          <button type="button" onClick={() => setShowOutput((value) => !value)}>{showOutput ? "Hide output" : "Show output"}</button>
        </div>

        {recentRows.length ? <div className="cptr-compact-log">
          {recentRows.map((row) => <div className="cptr-compact-row" key={row.id}>
            <b>{row.label ?? row.tone}</b>
            <code>{row.text}</code>
          </div>)}
        </div> : <div className="cptr-empty"><strong>Ready for CPTR activity</strong><span>Lifecycle and verification checkpoints will appear here as ChatGPT works.</span></div>}

        {showOutput ? <div className="cptr-output-toggle">
          <div className="cptr-panel-head">
            <div><strong>Terminal diagnostics</strong><span>Raw redacted output is available on demand only.</span></div>
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
      </div>
    </div>

    <footer className="cptr-native-foot">
      <span>{actionStatus || "ChatGPT remains the reasoning and orchestration layer."}</span>
      <span>{connection}</span>
    </footer>
  </section>;
}
