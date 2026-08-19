import React, { createContext, useContext, useState } from 'react';
import { TabId, EventRecord } from '../types';

interface AppContextType {
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
  recentEvents: EventRecord[];
  addEvent: (event: EventRecord) => void;
  selectedVideoClipUrl: string | null;
  setSelectedVideoClipUrl: (url: string | null) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeTab, setActiveTab] = useState<TabId>('gate');
  const [recentEvents, setRecentEvents] = useState<EventRecord[]>([]);
  const [selectedVideoClipUrl, setSelectedVideoClipUrl] = useState<string | null>(null);

  const addEvent = (event: EventRecord) => {
    setRecentEvents((prev) => [event, ...prev].slice(0, 50));
  };

  return (
    <AppContext.Provider
      value={{
        activeTab,
        setActiveTab,
        recentEvents,
        addEvent,
        selectedVideoClipUrl,
        setSelectedVideoClipUrl,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
