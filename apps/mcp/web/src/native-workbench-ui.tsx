import React from "react";

export function NativeWorkbenchStyles() {
  return <style>{`
    .cptr-native{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:CanvasText;background:Canvas;border:1px solid color-mix(in srgb,CanvasText 12%,transparent);border-radius:16px;overflow:hidden;box-shadow:0 1px 2px color-mix(in srgb,CanvasText 7%,transparent)}
    .cptr-native[data-display-mode="fullscreen"]{border:0;border-radius:0;box-shadow:none;min-height:min(760px,100vh)}
    .cptr-native *{box-sizing:border-box}
    .cptr-native button{font:inherit;color:inherit;background:transparent;border:1px solid color-mix(in srgb,CanvasText 14%,transparent);border-radius:9px;padding:7px 10px;cursor:pointer}
    .cptr-native button:hover:not(:disabled){background:color-mix(in srgb,CanvasText 6%,transparent)}
    .cptr-native button:focus-visible{outline:2px solid Highlight;outline-offset:2px}
    .cptr-native button:disabled{opacity:.45;cursor:default}
    .cptr-native button.primary{background:CanvasText;color:Canvas;border-color:CanvasText}
    .cptr-native button.danger{color:#b42318;border-color:color-mix(in srgb,#b42318 35%,transparent)}
    .cptr-native-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:16px 16px 12px}
    .cptr-native[data-display-mode="fullscreen"] .cptr-native-head,.cptr-native[data-display-mode="fullscreen"] .cptr-native-body{width:min(1180px,100%);margin-inline:auto}
    .cptr-native-brand{display:flex;gap:10px;min-width:0;align-items:center}
    .cptr-native-mark{display:grid;place-items:center;width:30px;height:30px;border-radius:9px;background:color-mix(in srgb,CanvasText 8%,transparent);font-size:12px;font-weight:750;letter-spacing:-.02em}
    .cptr-native-title{display:grid;gap:2px;min-width:0}.cptr-native-title strong{font-size:14px}.cptr-native-title span{font-size:12px;opacity:.62;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .cptr-native-actions{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
    .cptr-status{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:650;white-space:nowrap;max-width:220px;overflow:hidden;text-overflow:ellipsis}
    .cptr-dot{flex:0 0 auto;width:7px;height:7px;border-radius:50%;background:#12a150}.cptr-dot.wait{background:#d29922}.cptr-dot.bad{background:#d92d20}.cptr-dot.idle{background:color-mix(in srgb,CanvasText 30%,transparent)}
    .cptr-native-body{padding:0 16px 16px}
    .cptr-summary{display:grid;grid-template-columns:minmax(0,1.6fr) repeat(3,minmax(76px,.7fr));gap:8px;margin-bottom:12px}
    .cptr-summary-main,.cptr-metric{border:1px solid color-mix(in srgb,CanvasText 10%,transparent);border-radius:12px;padding:11px 12px;background:color-mix(in srgb,CanvasText 2%,transparent)}
    .cptr-summary-main{display:grid;gap:5px}.cptr-summary-main strong{font-size:14px}.cptr-summary-main span{font-size:12px;opacity:.65}
    .cptr-metric{display:grid;gap:3px}.cptr-metric b{font-size:16px}.cptr-metric span{font-size:11px;opacity:.58}
    .cptr-rail{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:0 0 12px}.cptr-rail-step{display:flex;align-items:center;gap:7px;font-size:12px;padding:7px 9px;border-radius:9px;background:color-mix(in srgb,CanvasText 4%,transparent)}
    .cptr-rail-step b{font-size:11px}.cptr-rail-step span{opacity:.58}
    .cptr-native-nav{display:flex;gap:4px;overflow:auto;padding-bottom:10px;scrollbar-width:none}.cptr-native-nav::-webkit-scrollbar{display:none}.cptr-native-nav button{border:0;padding:7px 9px;color:color-mix(in srgb,CanvasText 62%,transparent);white-space:nowrap}.cptr-native-nav button.selected{background:color-mix(in srgb,CanvasText 8%,transparent);color:CanvasText;font-weight:650}
    .cptr-panel{border-top:1px solid color-mix(in srgb,CanvasText 10%,transparent);padding-top:12px}.cptr-panel-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:9px}.cptr-panel-head div{display:grid;gap:2px}.cptr-panel-head strong{font-size:13px}.cptr-panel-head span{font-size:11px;opacity:.58}
    .cptr-worker-list{display:grid;gap:6px}.cptr-worker{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:9px;align-items:center;width:100%;text-align:left;padding:9px!important;border-color:color-mix(in srgb,CanvasText 9%,transparent)!important}.cptr-worker.selected{background:color-mix(in srgb,CanvasText 6%,transparent)}
    .cptr-worker-copy{display:grid;gap:1px;min-width:0}.cptr-worker-copy strong{font-size:12px}.cptr-worker-copy span,.cptr-worker-copy small{font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.cptr-worker-copy span{opacity:.68}.cptr-worker-copy small{opacity:.5}.cptr-worker-meta{display:grid;justify-items:end;gap:1px;font-size:10px}.cptr-worker-meta b{font-size:10px}.cptr-worker-meta small{opacity:.55}
    .cptr-activity{display:grid;gap:0}.cptr-activity-row{display:grid;grid-template-columns:68px auto minmax(0,1fr);gap:8px;padding:8px 0;border-bottom:1px solid color-mix(in srgb,CanvasText 7%,transparent);align-items:start}.cptr-activity-row:last-child{border-bottom:0}.cptr-activity-row time{font-size:10px;opacity:.5}.cptr-activity-row div{display:grid;gap:2px}.cptr-activity-row strong{font-size:11px}.cptr-activity-row span{font-size:11px;opacity:.67}
    .cptr-code{margin:0;max-height:300px;overflow:auto;background:color-mix(in srgb,CanvasText 4%,transparent);border-radius:10px;padding:11px;font:11px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;overflow-wrap:anywhere}
    .cptr-native[data-display-mode="fullscreen"] .cptr-code{max-height:min(55vh,620px)}
    .cptr-empty{padding:18px;text-align:center;display:grid;gap:4px}.cptr-empty strong{font-size:12px}.cptr-empty span{font-size:11px;opacity:.58}
    .cptr-native-foot{display:flex;justify-content:space-between;gap:10px;align-items:center;border-top:1px solid color-mix(in srgb,CanvasText 9%,transparent);padding:10px 16px;font-size:11px}.cptr-native-foot span{opacity:.58;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .cptr-output-toggle{margin-top:10px}.cptr-compact-log{display:grid;gap:4px}.cptr-compact-row{display:grid;grid-template-columns:48px minmax(0,1fr);gap:8px;padding:6px 0;font-size:11px;border-bottom:1px solid color-mix(in srgb,CanvasText 6%,transparent)}.cptr-compact-row:last-child{border-bottom:0}.cptr-compact-row b{font-size:10px;opacity:.48;text-transform:uppercase}.cptr-compact-row code{font:inherit;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    @media(max-width:620px){.cptr-native{border-radius:14px}.cptr-native[data-display-mode="fullscreen"]{border-radius:0}.cptr-native-head{padding:13px 13px 10px}.cptr-native-body{padding:0 13px 13px}.cptr-summary{grid-template-columns:1fr 1fr}.cptr-summary-main{grid-column:1/-1}.cptr-rail{grid-template-columns:1fr}.cptr-native-head .cptr-native-actions button:not(.primary){display:none}.cptr-native-foot{padding:9px 13px}.cptr-native-foot span{max-width:65%}.cptr-panel-head{align-items:flex-start}.cptr-panel-head>.cptr-native-actions{display:flex}.cptr-activity-row{grid-template-columns:52px auto minmax(0,1fr)}}
    @media(prefers-reduced-motion:reduce){.cptr-native *{scroll-behavior:auto!important;transition:none!important}}
  `}</style>;
}

export function StatusDot({ status }: { status: string }) {
  const value = status.toUpperCase();
  const className = ["FAILED", "ERROR", "BLOCKED", "REJECTED", "CANCELLED", "COMPLETE_WITH_TOOL_ERRORS"].includes(value)
    ? "bad"
    : ["APPROVAL_REQUIRED", "REVIEW_REQUIRED", "WAITING", "QUEUED"].includes(value)
      ? "wait"
      : ["RUNNING", "WORKING", "CONNECTING", "ACTIVE", "STARTED", "IN_PROGRESS"].includes(value)
        ? ""
        : ["COMPLETE", "COMPLETED", "INTEGRATED", "SUCCESS", "SUCCEEDED", "PASSED"].includes(value)
          ? ""
          : "idle";
  return <span className={`cptr-dot ${className}`} aria-hidden="true" />;
}

export function Metric({ value, label }: { value: React.ReactNode; label: string }) {
  return <div className="cptr-metric"><b>{value}</b><span>{label}</span></div>;
}

export function displayClock(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
