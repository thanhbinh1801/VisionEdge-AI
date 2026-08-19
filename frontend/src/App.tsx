import React, { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { AudioBeepPlayer } from './components/common/AudioBeepPlayer';
import { VideoModal } from './components/common/VideoModal';

import { GateDashboard } from './pages/GateDashboard';
import { AreaSecurityDashboard } from './pages/AreaSecurityDashboard';
import { ZoneTagSettings } from './pages/ZoneTagSettings';
import { AIChatbotAssistant } from './pages/AIChatbotAssistant';

const MainContent: React.FC = () => {
  const { activeTab, recentEvents } = useApp();
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const lastEvent = recentEvents.length > 0 ? recentEvents[0] : null;

  return (
    <div className="flex flex-col min-h-screen bg-[#020617] text-slate-100 font-sans select-none">
      <Header isMuted={isMuted} onToggleMute={() => setIsMuted((prev) => !prev)} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <main className="flex-1 p-6 overflow-y-auto">
          {activeTab === 'gate' && <GateDashboard />}
          {activeTab === 'area' && <AreaSecurityDashboard />}
          {activeTab === 'settings' && <ZoneTagSettings />}
          {activeTab === 'assistant' && <AIChatbotAssistant />}
        </main>
      </div>

      <AudioBeepPlayer lastEvent={lastEvent} isMuted={isMuted} />
      <VideoModal />
    </div>
  );
};

export function App() {
  return (
    <AppProvider>
      <MainContent />
    </AppProvider>
  );
}

export default App;
