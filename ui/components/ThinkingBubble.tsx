import React from 'react';
import { Loader2 } from 'lucide-react';

interface ThinkingBubbleProps {
  message?: string;
}

const ThinkingBubble: React.FC<ThinkingBubbleProps> = ({ 
  message = 'Thinking...' 
}) => {
  return (
    <div className="flex gap-4 max-w-[90%] animate-pulse">
      <div className="flex-shrink-0 mt-1">
        <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center border border-purple-500/30">
          <Loader2 size={20} className="text-purple-400 animate-spin" />
        </div>
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold text-purple-300 uppercase tracking-wider">Thinking</span>
        </div>
        <div className="bg-purple-950/20 border border-purple-500/20 rounded-2xl rounded-tl-sm p-4">
          <div className="flex items-center gap-2 text-purple-300/70 text-sm">
            <span className="flex gap-1">
              <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
              <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
              <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
            </span>
            <span className="ml-2">{message}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ThinkingBubble;
