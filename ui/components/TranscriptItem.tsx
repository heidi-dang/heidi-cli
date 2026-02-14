import React from 'react';
import { RunEvent } from '../types';
import { AlertCircle, Sparkles } from 'lucide-react';

interface TranscriptItemProps {
  event: RunEvent;
}

const TranscriptItem = React.memo(({ event }: TranscriptItemProps) => {
  if (!event.message) return null;

  return (
    <div className="flex gap-4 max-w-[90%] animate-in fade-in slide-in-from-bottom-2 duration-300 group">
      <div className="flex-shrink-0 mt-1">
        <div className="w-10 h-10 rounded-xl bg-black/40 flex items-center justify-center border border-white/10 shadow-lg overflow-hidden">
          {event.type === 'error'
            ? <AlertCircle size={20} className="text-red-400"/>
            : <Sparkles size={20} className="text-purple-400" />
          }
        </div>
      </div>
      <div className="flex-1 space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-purple-300 uppercase tracking-wider">{event.type || 'System'}</span>
          <span className="text-[10px] text-slate-500 font-mono">{event.ts ? new Date(event.ts).toLocaleTimeString() : ''}</span>
        </div>

        <div className={`text-sm leading-relaxed p-4 rounded-2xl rounded-tl-sm border shadow-sm backdrop-blur-sm ${
            event.type === 'error' ? 'bg-red-950/30 border-red-500/30 text-red-200' :
            'bg-[#1a162e]/80 border-white/5 text-slate-200 group-hover:bg-[#1f1b35] transition-colors'
        }`}>
            <pre className="whitespace-pre-wrap font-sans">{event.message}</pre>
        </div>
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  return prevProps.event.ts === nextProps.event.ts &&
         prevProps.event.message === nextProps.event.message &&
         prevProps.event.type === nextProps.event.type;
});

export default TranscriptItem;
