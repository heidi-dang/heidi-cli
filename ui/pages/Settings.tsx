import React, { useState, useEffect } from 'react';
import { getSettings, saveSettings, api } from '../services/heidi';
import { Save, Server, Wifi, AlertTriangle, PanelLeft } from 'lucide-react';

interface SettingsProps {
    isSidebarOpen: boolean;
    onToggleSidebar: () => void;
}

const Settings: React.FC<SettingsProps> = ({ isSidebarOpen, onToggleSidebar }) => {
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [status, setStatus] = useState<'idle' | 'checking' | 'connected' | 'error'>('idle');
  const [msg, setMsg] = useState('');

  useEffect(() => {
    const current = getSettings();
    setBaseUrl(current.baseUrl);
    setApiKey(current.apiKey);
    // Explicitly check connection using loaded values without saving
    checkConnection(current.baseUrl, current.apiKey);
  }, []);

  const checkConnection = async (url: string, key: string) => {
    setStatus('checking');
    try {
      // Pass params directly to api.health to avoid using potentially stale local storage
      await api.health(url, key);
      setStatus('connected');
      setMsg('Successfully connected to Heidi backend.');
    } catch (error) {
      setStatus('error');
      setMsg('Could not connect. Ensure the backend is running and URL is correct.');
    }
  };

  const handleSave = () => {
    // Only save when user explicitly clicks save
    saveSettings({ baseUrl, apiKey });
    checkConnection(baseUrl, apiKey);
  };

  return (
    <div className="h-full flex flex-col">
       {/* Header with Sidebar Toggle */}
       <div className="px-6 py-4 flex items-center gap-4 bg-black/20 backdrop-blur-md border-b border-white/5">
           {!isSidebarOpen && (
               <button 
                onClick={onToggleSidebar} 
                className="text-slate-400 hover:text-white transition-colors p-1 rounded hover:bg-white/5"
                title="Open Sidebar"
               >
                   <PanelLeft size={20} />
               </button>
           )}
           <h1 className="text-lg font-bold text-white flex items-center gap-2">
                Settings
           </h1>
       </div>

        <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-3xl mx-auto space-y-8">
                
                <h1 className="text-3xl font-bold mb-8 text-white flex items-center gap-3">
                    <div className="p-2 bg-purple-500/20 rounded-lg border border-purple-500/30">
                        <Server className="text-purple-400" size={24} />
                    </div>
                    Connection Settings
                </h1>

                <div className="bg-black/30 backdrop-blur-xl rounded-2xl p-8 border border-white/10 shadow-2xl space-y-8">
                    
                    {/* Connection Status Banner */}
                    <div className={`p-5 rounded-xl flex items-center gap-4 border ${
                    status === 'connected' ? 'bg-green-500/10 text-green-300 border-green-500/20' :
                    status === 'error' ? 'bg-red-500/10 text-red-300 border-red-500/20' :
                    'bg-white/5 text-slate-300 border-white/10'
                    }`}>
                    <div className={`p-2 rounded-full ${
                        status === 'connected' ? 'bg-green-500/20' :
                        status === 'error' ? 'bg-red-500/20' :
                        'bg-white/10'
                    }`}>
                        {status === 'checking' && <Wifi size={20} className="animate-pulse" />}
                        {status === 'connected' && <Wifi size={20} />}
                        {status === 'error' && <AlertTriangle size={20} />}
                        {status === 'idle' && <Server size={20} />}
                    </div>
                    
                    <div className="flex flex-col">
                        <span className="text-sm font-bold uppercase tracking-wider opacity-80">System Status</span>
                        <span className="text-base font-medium">
                            {status === 'idle' && "Check connection..."}
                            {status === 'checking' && "Connecting to backend..."}
                            {status === 'connected' && "Backend Connected"}
                            {status === 'error' && "Connection Failed"}
                        </span>
                    </div>
                    </div>

                    <div className="space-y-6">
                        <div>
                        <label className="block text-sm font-bold text-purple-200 mb-2 uppercase tracking-wide">
                            Heidi Base URL
                        </label>
                        <input
                            type="text"
                            value={baseUrl}
                            onChange={(e) => setBaseUrl(e.target.value)}
                            placeholder="http://localhost:7777"
                            className="w-full bg-black/40 border border-white/10 rounded-xl px-5 py-4 text-white focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 outline-none transition-all placeholder-slate-600 shadow-inner"
                        />
                        <p className="mt-2 text-xs text-slate-500">
                            Default is http://localhost:7777. If using a tunnel, paste the full public URL.
                        </p>
                        </div>

                        <div>
                        <label className="block text-sm font-bold text-purple-200 mb-2 uppercase tracking-wide">
                            API Key (Optional)
                        </label>
                        <input
                            type="password"
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            placeholder="sk-..."
                            className="w-full bg-black/40 border border-white/10 rounded-xl px-5 py-4 text-white focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 outline-none transition-all placeholder-slate-600 shadow-inner"
                        />
                        <p className="mt-2 text-xs text-slate-500">
                            Stored locally. Sent as X-Heidi-Key header.
                        </p>
                        </div>
                    </div>

                    <div className="pt-6 flex flex-col md:flex-row items-center justify-between gap-4 border-t border-white/5">
                    {msg ? (
                        <span className={`text-sm font-medium px-4 py-2 rounded-lg ${status === 'error' ? 'bg-red-500/10 text-red-300' : 'bg-green-500/10 text-green-300'}`}>
                            {msg}
                        </span>
                    ) : <span></span>}

                    <button
                        onClick={handleSave}
                        disabled={status === 'checking'}
                        className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white px-8 py-3 rounded-xl font-bold shadow-lg shadow-purple-900/40 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                    >
                        <Save size={18} />
                        Save & Connect
                    </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
  );
};

export default Settings;