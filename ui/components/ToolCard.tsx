import React from 'react';
import { ToolEvent } from '../types';
import { CheckCircle, XCircle, PlayCircle, Clock, Terminal } from 'lucide-react';

interface ToolCardProps {
  tool: ToolEvent;
}

const ToolCard: React.FC<ToolCardProps> = ({ tool }) => {
  const getStatusIcon = () => {
    switch (tool.status) {
      case 'completed':
        return <CheckCircle size={16} className="text-green-400" />;
      case 'failed':
        return <XCircle size={16} className="text-red-400" />;
      case 'started':
      default:
        return <PlayCircle size={16} className="text-blue-400 animate-pulse" />;
    }
  };

  const getStatusColor = () => {
    switch (tool.status) {
      case 'completed':
        return 'border-green-500/30 bg-green-950/20';
      case 'failed':
        return 'border-red-500/30 bg-red-950/20';
      case 'started':
      default:
        return 'border-blue-500/30 bg-blue-950/20';
    }
  };

  const formatTime = (ts?: string) => {
    if (!ts) return '';
    return new Date(ts).toLocaleTimeString();
  };

  return (
    <div className={`rounded-xl border ${getStatusColor()} p-4 my-2`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-slate-400" />
          <span className="text-sm font-medium text-slate-200">{tool.name}</span>
        </div>
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className="text-xs text-slate-400 capitalize">{tool.status}</span>
          {tool.startedAt && (
            <span className="text-xs text-slate-500 flex items-center gap-1">
              <Clock size={12} />
              {formatTime(tool.startedAt)}
            </span>
          )}
        </div>
      </div>

      {tool.input && (
        <div className="mb-2">
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Input</div>
          <div className="text-xs font-mono bg-black/30 rounded p-2 text-slate-300 max-h-24 overflow-y-auto">
            {tool.input}
          </div>
        </div>
      )}

      {tool.output && (
        <div className="mb-2">
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Output</div>
          <div className="text-xs font-mono bg-black/30 rounded p-2 text-green-300 max-h-32 overflow-y-auto">
            {tool.output}
          </div>
        </div>
      )}

      {tool.error && (
        <div className="text-xs text-red-300 bg-red-950/30 rounded p-2 mt-2">
          {tool.error}
        </div>
      )}
    </div>
  );
};

export default ToolCard;
