import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Chat from './pages/Chat';
import Settings from './pages/Settings';

function App() {
  const [currentView, setCurrentView] = useState<'chat' | 'settings'>('chat');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [refreshSidebarTrigger, setRefreshSidebarTrigger] = useState(0);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const handleNavigate = (view: 'chat' | 'settings') => {
    setCurrentView(view);
    if (view === 'settings') {
        setSelectedRunId(null);
    }
  };

  const handleSelectRun = (runId: string) => {
    setSelectedRunId(runId);
    setCurrentView('chat');
  };

  const handleNewChat = () => {
    setSelectedRunId(null);
    setCurrentView('chat');
  };

  const handleRunCreated = () => {
      // Trigger sidebar refresh
      setRefreshSidebarTrigger(prev => prev + 1);
  };

  return (
    <div className="flex h-screen bg-[#0f0c29] bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#240b36] via-[#0f0c29] to-[#000000] text-slate-100 overflow-hidden font-sans selection:bg-pink-500/30">
      
      {/* Left Sidebar Wrapper */}
      <div className={`${isSidebarOpen ? 'w-80' : 'w-0'} transition-[width] duration-300 ease-in-out flex-shrink-0 overflow-hidden`}>
        <div className="w-80 h-full">
            <Sidebar 
                currentView={currentView}
                onNavigate={(view) => {
                    if (view === 'chat') handleNewChat();
                    else handleNavigate(view as 'chat' | 'settings');
                }}
                onSelectRun={handleSelectRun}
                selectedRunId={selectedRunId}
                refreshTrigger={refreshSidebarTrigger}
                isOpen={isSidebarOpen}
                onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
            />
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative h-full overflow-hidden bg-black/20 backdrop-blur-sm min-w-0">
        {currentView === 'settings' ? (
            <Settings 
                isSidebarOpen={isSidebarOpen}
                onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
            />
        ) : (
            <Chat 
                initialRunId={selectedRunId} 
                onRunCreated={handleRunCreated}
                isSidebarOpen={isSidebarOpen}
                onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
            />
        )}
      </main>

    </div>
  );
}

export default App;