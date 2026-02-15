import React, { useEffect, useState } from 'react';
import { RunSummary } from '../types';
import { api } from '../services/heidi';
import { RefreshCw, Settings, MessageSquare, Circle, CheckCircle, XCircle, AlertTriangle, PanelLeft, User, Sparkles } from 'lucide-react';

interface SidebarProps {
  currentView: 'chat' | 'settings';
  onNavigate: (view: 'chat' | 'settings') => void;
  onSelectRun: (runId: string) => void;
  selectedRunId: string | null;
  refreshTrigger: number;
  isOpen: boolean;
  onToggle: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ currentView, onNavigate, onSelectRun, selectedRunId, refreshTrigger, isOpen, onToggle }) => {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const fetchRuns = async () => {
    setLoading(true);
    setError(false);
    try {
      // Req: GET /runs?limit=10
      const data = await api.getRuns(10);
      setRuns(data);
    } catch (error) {
      // Log as warning instead of error to prevent console spam when backend is offline
      console.warn("Failed to load history (backend may be offline):", error);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, [refreshTrigger]);

  const getStatusIcon = (status: string) => {
    const s = status?.toLowerCase() || '';
    if (s === 'completed') return <CheckCircle size={14} className="text-pink-400" />;
    if (s === 'failed') return <XCircle size={14} className="text-red-400" />;
    return <Circle size={14} className="text-purple-400 animate-pulse" />;
  };

  return (
    <div className="w-full bg-black/40 border-r border-white/10 flex flex-col h-full backdrop-blur-md">
      {/* Header */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 relative flex-shrink-0 flex items-center justify-center bg-gradient-to-tr from-pink-500 to-purple-600 rounded-xl shadow-lg shadow-purple-900/50">
            <Sparkles size={20} className="text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-pink-300 to-purple-300 drop-shadow-sm whitespace-nowrap">
            Heidi AI
            </span>
        </div>
        <button 
            onClick={onToggle}
            className="text-slate-400 hover:text-white transition-colors p-1 rounded-md hover:bg-white/5"
            title="Close Sidebar"
            aria-label="Close Sidebar"
        >
            <PanelLeft size={20} />
        </button>
      </div>

      {/* Navigation */}
      <div className="p-2 space-y-1 mt-2">
        <button
          onClick={() => onNavigate('chat')}
          aria-current={currentView === 'chat' ? 'page' : undefined}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
            currentView === 'chat' && !selectedRunId 
            ? 'bg-gradient-to-r from-purple-900/50 to-pink-900/20 text-pink-200 border border-purple-500/30' 
            : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
          }`}
          aria-current={currentView === 'chat' && !selectedRunId ? 'page' : undefined}
        >
          <MessageSquare size={18} />
          <span className="text-sm font-medium">Heidi Chat</span>
        </button>

        <button
          onClick={() => onNavigate('settings')}
          aria-current={currentView === 'settings' ? 'page' : undefined}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
            currentView === 'settings' 
            ? 'bg-gradient-to-r from-purple-900/50 to-pink-900/20 text-pink-200 border border-purple-500/30' 
            : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
          }`}
          aria-current={currentView === 'settings' ? 'page' : undefined}
        >
          <Settings size={18} />
          <span className="text-sm font-medium">Settings</span>
        </button>
      </div>

      {/* History Header */}
      <div className="px-4 pt-6 pb-2 flex items-center justify-between text-slate-400">
        <span className="text-xs font-bold uppercase tracking-wider text-purple-300/70">Recent Runs</span>
        <button
          onClick={fetchRuns}
          className="hover:text-pink-300 transition-colors"
          title="Refresh history"
          aria-label="Refresh history"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* History List */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1 custom-scrollbar">
        {error ? (
           <div className="px-2 py-8 text-center">
             <div className="flex justify-center mb-2 text-red-400/80">
               <AlertTriangle size={20} /> 
             </div>
             <p className="text-xs text-red-300 font-medium mb-1">Connection Error</p>
             <p className="text-[10px] text-slate-500 mb-3">Is the backend running?</p>
             <button 
                onClick={fetchRuns}
                className="text-xs bg-white/5 hover:bg-white/10 text-slate-300 px-3 py-1 rounded border border-white/10 transition-colors"
             >
                Retry
             </button>
           </div>
        ) : (
          <>
            {runs.map((run) => (
              <button
                key={run.run_id}
                onClick={() => onSelectRun(run.run_id)}
                className={`w-full text-left p-3 rounded-lg transition-all border ${
                  selectedRunId === run.run_id
                    ? 'bg-white/10 border-purple-500/30 text-white'
                    : 'border-transparent text-slate-400 hover:bg-white/5 hover:text-slate-200'
                }`}
                aria-current={selectedRunId === run.run_id ? 'true' : undefined}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono opacity-60 truncate max-w-[80px]">
                    {run.run_id.substring(0, 8)}
                  </span>
                  {getStatusIcon(run.status)}
                </div>
                <div className="text-sm line-clamp-2 leading-snug">
                  {run.task || run.executor || 'Untitled Run'}
                </div>
              </button>
            ))}
            {runs.length === 0 && !loading && (
              <div className="px-4 py-8 text-center text-slate-600 text-sm">
                No runs found.
              </div>
            )}
          </>
        )}
      </div>
      
      {/* Footer Profile Section */}
      <div className="p-4 border-t border-white/10 mt-auto bg-black/20">
          <button className="flex items-center gap-3 w-full p-2 hover:bg-white/5 rounded-xl transition-all group">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold shadow-lg shadow-purple-900/20 ring-1 ring-white/10">
              <User size={18} />
            </div>
            <div className="flex flex-col items-start overflow-hidden">
              <span className="text-sm font-bold text-slate-200 group-hover:text-white truncate w-full text-left">Heidi User</span>
              <span className="text-[10px] uppercase tracking-wider text-purple-300 font-semibold bg-purple-500/20 px-1.5 py-0.5 rounded border border-purple-500/20">Pro Plan</span>
            </div>
          </button>
      </div>
    </div>
  );
};

export default Sidebar;