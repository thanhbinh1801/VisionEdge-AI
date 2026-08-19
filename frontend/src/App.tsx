import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { GateDashboard } from './pages/GateDashboard';
import { AreaSecurityDashboard } from './pages/AreaSecurityDashboard';
import { ZoneTagSettings } from './pages/ZoneTagSettings';
import { AIChatbotAssistant } from './pages/AIChatbotAssistant';
import { TabId } from './types';

const MainLayout: React.FC = () => {
  const { tab, setTab } = useApp();

  const tabs: { id: TabId; label: string }[] = [
    { id: 'mon', label: 'Giám sát cổng' },
    { id: 'area', label: 'Giám sát khu vực' },
    { id: 'set', label: 'Cài đặt' },
    { id: 'qa', label: 'Hỏi đáp AI' },
  ];

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg)',
        color: 'var(--ink)',
        fontSize: '14px',
        WebkitFontSmoothing: 'antialiased',
      }}
    >
      {/* Header Bar */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          padding: '14px 22px',
          borderBottom: '1px solid var(--line)',
          background: 'var(--panel)',
        }}
      >
        {/* Brand Icon */}
        <div
          style={{
            width: '32px',
            height: '32px',
            flex: 'none',
            borderRadius: '9px',
            background: 'linear-gradient(145deg,#2f9bff,#1361c9)',
            position: 'relative',
          }}
        >
          <div
            style={{
              position: 'absolute',
              inset: '9px',
              border: '2px solid #fff',
              borderRadius: '50%',
            }}
          />
        </div>

        {/* Title */}
        <div style={{ lineHeight: 1.15 }}>
          <div style={{ fontSize: '15px', fontWeight: 700 }}>
            Bài tập Intern · Nhận diện biển số & phân loại xe tại cổng
          </div>
          <div style={{ fontSize: '11px', color: 'var(--ink3)' }}>
            SentriAI mini · 1 camera cổng · zone vẽ sẵn
          </div>
        </div>

        <div style={{ flex: 1 }} />

        {/* Navigation Tabs Switcher */}
        <div
          style={{
            display: 'flex',
            background: 'var(--card)',
            border: '1px solid var(--line)',
            borderRadius: '11px',
            padding: '4px',
            gap: '2px',
          }}
        >
          {tabs.map((t) => {
            const on = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                style={{
                  fontSize: '12.5px',
                  fontWeight: 600,
                  padding: '7px 16px',
                  borderRadius: '8px',
                  border: 'none',
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                  background: on ? 'var(--acc)' : 'transparent',
                  color: on ? '#fff' : 'var(--ink2)',
                }}
              >
                {t.label}
              </button>
            );
          })}
        </div>
      </header>

      {/* Main Page Content */}
      <main>
        {tab === 'mon' && <GateDashboard />}
        {tab === 'area' && <AreaSecurityDashboard />}
        {tab === 'set' && <ZoneTagSettings />}
        {tab === 'qa' && <AIChatbotAssistant />}
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AppProvider>
      <MainLayout />
    </AppProvider>
  );
};

export default App;
