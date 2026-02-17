import React, { useState, useEffect, useRef } from 'react';
import { api, getSettings } from '../services/heidi';
import { Agent, AppMode, RunEvent, RunStatus, ToolEvent } from '../types';
import { 
  Send, Repeat, StopCircle, CheckCircle, AlertCircle, Loader2, PlayCircle, PanelLeft,
  Sparkles, Cpu, Search, Map, Terminal, Eye, Shield, MessageSquare, ArrowDown
} from 'lucide-react';
import TranscriptItem from '../components/TranscriptItem';
import ThinkingBubble from '../components/ThinkingBubble';
import ToolCard from '../components/ToolCard';

interface ChatProps {
  initialRunId?: string | null;
  onRunCreated?: () => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
}

const Chat: React.FC<ChatProps> = ({ initialRunId, onRunCreated, isSidebarOpen, onToggleSidebar }) => {
  // Config State
  const [prompt, setPrompt] = useState('');
  const [mode, setMode] = useState<AppMode>(AppMode.CHAT); // Default to CHAT
  const [executor, setExecutor] = useState('copilot');
  const [maxRetries, setMaxRetries] = useState(2);
  const [dryRun, setDryRun] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);

  // Runtime State
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('idle');
  const [transcript, setTranscript] = useState<RunEvent[]>([]);
  const [thinking, setThinking] = useState<string>('');
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [showJumpToBottom, setShowJumpToBottom] = useState(false);

  // Refs for streaming management
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingRef = useRef<any>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // --- Initialization ---

  useEffect(() => {
    api.getAgents().then(setAgents).catch(() => {
      // Fallback if agents endpoint is not ready
      setAgents([{ name: 'copilot', description: 'Default executor' }]);
    });
  }, []);

  useEffect(() => {
    if (initialRunId && initialRunId !== runId) {
      loadRun(initialRunId);
    } else if (!initialRunId) {
      resetChat();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialRunId]);

  useEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcript, status]);

  // Auto-scroll detection - show jump-to-bottom when user scrolls up
  useEffect(() => {
    const container = chatContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      setShowJumpToBottom(!isNearBottom);
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, [transcript]);

  useEffect(() => {
    return () => stopStreaming();
  }, []);

  // --- Core Logic ---

  const resetChat = () => {
    stopStreaming();
    setRunId(null);
    setTranscript([]);
    setThinking('');
    setToolEvents([]);
    setStatus('idle');
    setResult(null);
    setError(null);
    setPrompt('');
    setIsCancelling(false);
  };

  const stopStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const loadRun = async (id: string) => {
    stopStreaming();
    setRunId(id);
    setTranscript([]); 
    setError(null);
    setResult(null);

    try {
      const details = await api.getRun(id);
      setTranscript(details.events || []);
      setStatus(details.meta?.status || 'unknown');
      setMode(details.meta?.task ? AppMode.LOOP : AppMode.RUN);
      setExecutor(details.meta?.executor || 'copilot');
      if (details.result) setResult(details.result);
      if (details.error) setError(details.error);

      if (
        details.meta?.status !== RunStatus.COMPLETED &&
        details.meta?.status !== RunStatus.FAILED
      ) {
        startStreaming(id);
      }
    } catch (err) {
      console.error(err);
      setError('Failed to load run details');
    }
  };

  const terminalStatuses = new Set(['completed', 'failed', 'cancelled', 'idle']);
  const isRunning = runId && !terminalStatuses.has(status.toLowerCase());

  const handleStart = async () => {
    if (!prompt.trim()) return;

    resetChat();
    setIsSending(true);
    setStatus('initiating');

    try {
      let response;
      
      if (mode === AppMode.CHAT) {
        // Simple chat - no artifacts, just response
        const chatRes = await api.chat(prompt, executor);
        setTranscript([{
          type: 'assistant',
          message: chatRes.response,
          ts: Date.now().toString()
        }]);
        setStatus(RunStatus.COMPLETED);
        setResult(chatRes.response);
        setIsSending(false);
        return;
      }
      
      if (mode === AppMode.RUN) {
        // Spec: POST /run { prompt, executor, workdir }
        response = await api.startRun({
          prompt,
          executor,
          workdir: null,
          dry_run: dryRun
        });
      } else {
        // Spec: POST /loop { task, executor, max_retries, workdir }
        response = await api.startLoop({
          task: prompt,
          executor,
          max_retries: maxRetries,
          workdir: null,
          dry_run: dryRun
        });
      }

      setRunId(response.run_id);
      setStatus(RunStatus.RUNNING);
      
      if (onRunCreated) onRunCreated();
      startStreaming(response.run_id);
    } catch (err: any) {
      setError(err.message || 'Failed to start run');
      setStatus(RunStatus.FAILED);
    } finally {
      setIsSending(false);
    }
  };

  const handleStop = async () => {
      if (!runId) return;
      setIsCancelling(true);
      try {
          await api.cancelRun(runId);
          // Don't reset immediately, let polling/SSE catch the status change
          setStatus('cancelling');
      } catch (e) {
          console.error("Cancel failed", e);
      }
  };

  const startStreaming = (id: string) => {
    stopStreaming(); 
    
    // NOTE: EventSource does not support headers. 
    // If auth is enabled later, we must use polling or a fetch-based stream reader.
    // For now, if API key is present in settings (even if not sent), we might prefer polling 
    // to be safe, OR we assume the SSE endpoint doesn't need auth yet (as per prompt).
    // Spec says: "GET /runs/{run_id}/stream using EventSource".
    // Fallback: "Poll every 1s if SSE fails".

    const streamUrl = api.getStreamUrl(id);
    
    try {
      const es = new EventSource(streamUrl);
      eventSourceRef.current = es;

      es.onopen = () => {
        console.log("SSE Connected");
      };

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setTranscript((prev) => [...prev, data]);
          
          // Process structured events for streaming UI
          if (data.type === 'thinking') {
            setThinking(data.data?.message || 'Thinking...');
          } else if (data.type === 'tool_start') {
            setToolEvents(prev => [...prev, {
              id: `${data.data?.tool}-${Date.now()}`,
              name: data.data?.tool || 'Unknown',
              status: 'started',
              input: data.data?.input,
              startedAt: new Date().toISOString()
            }]);
          } else if (data.type === 'tool_log') {
            setToolEvents(prev => prev.map(t => 
              t.name === data.data?.tool 
                ? { ...t, output: (t.output || '') + (data.data?.log || '') }
                : t
            ));
          } else if (data.type === 'tool_done') {
            setToolEvents(prev => prev.map(t => 
              t.name === data.data?.tool 
                ? { ...t, status: 'completed', output: data.data?.output, completedAt: new Date().toISOString() }
                : t
            ));
          } else if (data.type === 'tool_error') {
            setToolEvents(prev => prev.map(t => 
              t.name === data.data?.tool 
                ? { ...t, status: 'failed', error: data.data?.error, completedAt: new Date().toISOString() }
                : t
            ));
          } else if (data.type === 'run_state') {
            setStatus(data.data?.state || data.data?.status || 'running');
            if (data.data?.state === 'completed') {
              setThinking('');
            }
          }
        } catch (e) {
          console.warn("Error parsing SSE data", event.data);
        }
      };

      es.onerror = (err) => {
        // If SSE fails (e.g. 404 or connection error), fall back to polling
        console.warn("SSE Error, switching to polling", err);
        es.close();
        eventSourceRef.current = null;
        startPolling(id);
      };

    } catch (e) {
      console.error("Failed to setup SSE", e);
      startPolling(id);
    }
  };

  const startPolling = (id: string) => {
    if (pollingRef.current) return;
    
    const check = async () => {
      try {
        const details = await api.getRun(id);
        
        // Update transcript (deduplication logic might be needed if mixing SSE and polling, 
        // but simple replacement is safer for polling fallback)
        if (details.events) {
            setTranscript(details.events);
        }
        
        const currentStatus = details.meta?.status || 'unknown';
        setStatus(currentStatus);
        
        if (details.result) setResult(details.result);
        if (details.error) setError(details.error);

        const s = currentStatus.toLowerCase();
        if (s === 'completed' || s === 'failed' || s === 'cancelled') {
          stopStreaming(); // Clear the interval
          setIsCancelling(false);
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    };
    
    check();
    pollingRef.current = setInterval(check, 1000); // Poll every 1s
  };

  // --- Rendering Helpers ---

  const renderStatusBadge = () => {
    const rawStatus = status || 'idle';
    const s = rawStatus.toLowerCase();
    
    let color = "bg-white/5 text-slate-400 border border-white/10";
    let icon = <Loader2 size={14} className="animate-spin text-purple-400" />;
    let label = rawStatus;

    if (s === 'completed') {
      color = "bg-green-500/10 text-green-300 border border-green-500/20";
      icon = <CheckCircle size={14} />;
    } else if (s === 'failed' || s === 'error') {
      color = "bg-red-500/10 text-red-300 border border-red-500/20";
      icon = <AlertCircle size={14} />;
    } else if (s === 'idle') {
      color = "bg-white/5 text-slate-400 border border-white/10";
      icon = <div className="w-2 h-2 rounded-full bg-slate-600" />;
      label = "Idle";
    } else if (s.includes('cancelling') || s.includes('cancelled')) {
      color = "bg-orange-500/10 text-orange-300 border border-orange-500/20";
      icon = <StopCircle size={14} />;
    } else if (s.includes('initiating')) {
      color = "bg-blue-500/10 text-blue-300 border border-blue-500/20";
      icon = <Loader2 size={14} className="animate-spin" />;
      label = "Initiating...";
    } else {
      // Granular Running States
      color = "bg-purple-500/10 text-purple-300 border border-purple-500/20 shadow-[0_0_15px_rgba(168,85,247,0.15)]";
      
      if (s.includes('planning')) {
         label = "Planning...";
         icon = <Map size={14} />;
      } else if (s.includes('executing')) {
         label = "Executing...";
         icon = <Terminal size={14} />;
      } else if (s.includes('reviewing')) {
         label = "Reviewing...";
         icon = <Eye size={14} />;
      } else if (s.includes('auditing')) {
         label = "Auditing...";
         icon = <Shield size={14} />;
      } else if (s.includes('retrying')) {
          label = "Retrying...";
          icon = <Repeat size={14} className="animate-spin-slow" />;
      } else {
          // Generic running
          label = "Running...";
          icon = <Cpu size={14} className="animate-pulse" />;
      }
    }

    return (
      <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider backdrop-blur-md transition-all duration-300 ${color}`}>
        {icon}
        <span className="truncate max-w-[180px]">{label}</span>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-transparent">
      
      {/* 1. Header Area */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-black/20 backdrop-blur-md z-10">
        <div className="flex items-center gap-4">
           {!isSidebarOpen && (
               <button 
                 onClick={onToggleSidebar} 
                 className="text-slate-400 hover:text-white transition-colors p-1 rounded hover:bg-white/5"
                 title="Open Sidebar"
                 aria-label="Open Sidebar"
                >
                   <PanelLeft size={20} />
               </button>
           )}
           {renderStatusBadge()}
           {runId && <span className="text-xs font-mono text-purple-200/50">ID: {runId}</span>}
        </div>
      </div>

      {/* 2. Main Chat / Transcript Area */}
      <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-6 space-y-8 scroll-smooth custom-scrollbar">
        
        {/* User Prompt Bubble */}
        {(prompt || initialRunId) && (runId || transcript.length > 0) && (
            <div className="flex justify-end">
                <div className="max-w-[80%] bg-gradient-to-br from-pink-600 to-purple-700 text-white px-5 py-4 rounded-2xl rounded-tr-sm shadow-xl shadow-purple-900/20 border border-white/10">
                    <div className="text-xs text-pink-200 mb-1 font-bold uppercase opacity-80 tracking-wide">
                        {mode === AppMode.LOOP ? 'Task' : 'Prompt'}
                    </div>
                    <div className="whitespace-pre-wrap leading-relaxed">
                        {prompt || (transcript.find(e => e.type === 'user_prompt')?.message) || 'Run started...'}
                    </div>
                </div>
            </div>
        )}

        {/* Empty State */}
        {!runId && transcript.length === 0 && !isSending && (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 opacity-80 pb-20">
             <div className="w-32 h-32 mb-6 relative">
                 <div className="absolute inset-0 bg-purple-500/20 blur-3xl rounded-full"></div>
                  <div className="relative w-full h-full flex items-center justify-center">
                    <Sparkles className="w-16 h-16 text-purple-400" />
                  </div>
             </div>
            <h2 className="mt-4 text-3xl font-bold text-white tracking-tight">How can I help you?</h2>
            <p className="text-slate-400 mt-2">Configure your agent below and start a new run.</p>
          </div>
        )}

        {/* System/Agent Events */}
        <div className="space-y-4">
            {transcript.map((event, idx) => (
                <TranscriptItem key={idx} event={event} />
            ))}
            
            {/* Thinking Bubble - show for RUN/LOOP modes during execution */}
            {(mode !== AppMode.CHAT) && thinking && (
                <ThinkingBubble message={thinking} />
            )}

            {/* Tool Cards - show for RUN/LOOP modes */}
            {(mode !== AppMode.CHAT) && toolEvents.map((tool) => (
                <ToolCard key={tool.id} tool={tool} />
            ))}
            
            {/* Loading Indicator - fallback for CHAT mode or when no thinking */}
            {(status.toLowerCase() !== 'completed' && status.toLowerCase() !== 'failed' && status.toLowerCase() !== 'idle' && status.toLowerCase() !== 'cancelled') && (
                <div className="flex gap-4 max-w-[90%]">
                    <div className="w-10 h-10 flex-shrink-0" />
                    <div className="flex items-center gap-2 text-purple-400/70 text-sm bg-purple-900/10 px-3 py-1.5 rounded-full border border-purple-500/10">
                        <Loader2 size={14} className="animate-spin" />
                        <span>{status.includes('running') ? 'Thinking...' : status}</span>
                    </div>
                </div>
            )}
        </div>

        {/* Final Result Block */}
        {result && (
            <div className="mt-8 border-t border-white/10 pt-8 animate-in fade-in zoom-in-95 duration-500">
                <h3 className="text-green-400 font-bold mb-3 flex items-center gap-2 text-sm uppercase tracking-wider">
                    <CheckCircle size={16} />
                    Final Output
                </h3>
                <div className="bg-black/30 border border-green-500/20 rounded-xl p-5 font-mono text-sm text-green-100/90 overflow-x-auto shadow-inner relative">
                    <div className="absolute top-0 left-0 w-1 h-full bg-green-500/50 rounded-l-xl"></div>
                    <pre>{result}</pre>
                </div>
            </div>
        )}

        {error && (
            <div className="mt-8 border-t border-white/10 pt-8">
                 <h3 className="text-red-400 font-bold mb-3 flex items-center gap-2 text-sm uppercase tracking-wider">
                    <AlertCircle size={16} />
                    Execution Failed
                </h3>
                <div className="bg-red-950/20 border border-red-500/20 rounded-xl p-5 font-mono text-sm text-red-200">
                    {error}
                </div>
            </div>
        )}

        <div ref={chatBottomRef} />
        
        {/* Jump to bottom button - shows when user scrolls up */}
        {showJumpToBottom && (
          <button
            onClick={() => chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })}
            className="fixed bottom-24 right-8 bg-purple-600 hover:bg-purple-500 text-white p-3 rounded-full shadow-lg transition-all transform hover:scale-110 z-50"
            title="Jump to bottom"
            aria-label="Jump to bottom"
          >
            <ArrowDown size={20} />
          </button>
        )}
      </div>

      {/* 3. Input Area */}
      <div className="p-6 z-20">
        <div className="max-w-4xl mx-auto space-y-4 bg-black/40 backdrop-blur-xl border border-white/10 p-4 rounded-2xl shadow-2xl">
            
            {/* Input Controls */}
            {!runId && (
                <div className="flex flex-wrap items-center gap-4 text-sm text-slate-400 p-1">
                    {/* Mode Toggle */}
                    <div className="flex bg-black/40 rounded-lg p-1 border border-white/5">
                        <button 
                            onClick={() => setMode(AppMode.CHAT)}
                            aria-pressed={mode === AppMode.CHAT}
                            className={`px-4 py-1.5 rounded-md transition-all font-medium ${mode === AppMode.CHAT ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'hover:text-white hover:bg-white/5'}`}
                        >
                            <span className="flex items-center gap-1.5"><MessageSquare size={14} /> Chat</span>
                        </button>
                        <button 
                            onClick={() => setMode(AppMode.RUN)}
                            aria-pressed={mode === AppMode.RUN}
                            className={`px-4 py-1.5 rounded-md transition-all font-medium ${mode === AppMode.RUN ? 'bg-purple-600 text-white shadow-lg shadow-purple-900/50' : 'hover:text-white hover:bg-white/5'}`}
                        >
                            <span className="flex items-center gap-1.5"><PlayCircle size={14} /> Run</span>
                        </button>
                        <button 
                            onClick={() => setMode(AppMode.LOOP)}
                            aria-pressed={mode === AppMode.LOOP}
                            className={`px-4 py-1.5 rounded-md transition-all font-medium ${mode === AppMode.LOOP ? 'bg-pink-600 text-white shadow-lg shadow-pink-900/50' : 'hover:text-white hover:bg-white/5'}`}
                        >
                            <span className="flex items-center gap-1.5"><Repeat size={14} /> Loop</span>
                        </button>
                    </div>

                    <div className="w-px h-5 bg-white/10 mx-1"></div>

                    {/* Executor Select */}
                    <div className="flex items-center gap-2">
                        <span className="text-xs uppercase font-bold tracking-wider text-slate-500">
                            <label htmlFor="agent-select">Agent</label>
                        </span>
                        <select 
                            id="agent-select"
                            value={executor} 
                            onChange={(e) => setExecutor(e.target.value)}
                            className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-slate-200 text-xs focus:ring-1 focus:ring-purple-500 outline-none hover:bg-white/10 transition-colors"
                        >
                            {agents.map(a => (
                                <option key={a.name} value={a.name} className="bg-slate-900">{a.name}</option>
                            ))}
                        </select>
                    </div>

                    {mode === AppMode.LOOP && (
                         <label className="flex items-center gap-2 animate-in fade-in zoom-in-95 cursor-pointer">
                            <span className="text-xs uppercase font-bold tracking-wider text-slate-500">Retries</span>
                            <input 
                                type="number" 
                                min={0} 
                                max={10} 
                                value={maxRetries} 
                                onChange={(e) => setMaxRetries(parseInt(e.target.value))}
                                className="w-14 bg-white/5 border border-white/10 rounded px-2 py-1.5 text-slate-200 text-xs focus:ring-1 focus:ring-purple-500 outline-none hover:bg-white/10 transition-colors"
                            />
                        </label>
                    )}

                    <div className="flex-1"></div>

                    <label className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors">
                        <input 
                            type="checkbox" 
                            checked={dryRun} 
                            onChange={(e) => setDryRun(e.target.checked)}
                            className="rounded bg-white/10 border-white/20 text-purple-500 focus:ring-offset-black focus:ring-purple-500"
                        />
                        <span className="text-xs font-medium">Dry Run</span>
                    </label>
                </div>
            )}

            {/* Main Text Input */}
            <div className="relative group">
                <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey && !isRunning) {
                            e.preventDefault();
                            handleStart();
                        }
                    }}
                    placeholder={mode === AppMode.LOOP ? "Describe the task you want Heidi to complete..." : "Ask Heidi a question or give a command..."}
                    aria-label="Prompt input"
                    disabled={isSending || isRunning}
                    className="w-full bg-black/20 border border-white/10 text-white placeholder-slate-500/70 rounded-xl p-4 pr-16 focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 outline-none resize-none min-h-[60px] max-h-[200px] shadow-inner disabled:opacity-50 disabled:cursor-not-allowed transition-all group-hover:bg-black/30"
                    rows={1}
                    style={{ minHeight: '80px' }}
                />
                
                <div className="absolute right-3 bottom-3">
                    {!isRunning ? (
                        <button
                            onClick={handleStart}
                            disabled={!prompt.trim() || isSending}
                            aria-label={isSending ? "Sending..." : "Send message"}
                            title={mode === AppMode.LOOP ? "Start task" : "Send message"}
                            className={`p-2.5 rounded-lg flex items-center justify-center transition-all duration-300 ${
                                prompt.trim() && !isSending ? 'bg-gradient-to-tr from-purple-600 to-pink-600 hover:shadow-lg hover:shadow-purple-500/30 text-white transform hover:scale-105' : 'bg-white/10 text-slate-500 cursor-not-allowed'
                            }`}
                        >
                            {isSending ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
                        </button>
                    ) : (
                        <button
                            onClick={handleStop} 
                            disabled={isCancelling}
                            className={`p-2.5 rounded-lg border transition-colors ${
                                isCancelling 
                                ? 'bg-orange-500/20 text-orange-400 border-orange-500/30' 
                                : 'bg-red-500/10 hover:bg-red-500/20 text-red-300 border-red-500/20 hover:border-red-500/40'
                            }`}
                            title="Stop Run"
                            aria-label={isCancelling ? "Stopping..." : "Stop run"}
                        >
                           {isCancelling ? <Loader2 size={20} className="animate-spin" /> : <StopCircle size={20} />}
                        </button>
                    )}
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;