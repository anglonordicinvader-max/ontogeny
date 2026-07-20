import { useState, useEffect, useCallback } from 'react';
import { TitleBar } from './components/TitleBar';
import { Sidebar } from './components/Sidebar';
import { StatusBar } from './components/StatusBar';
import { ActivityTimeline } from './components/ActivityTimeline';
import { CognitiveState } from './components/CognitiveState';
import { MemoryExplorer } from './components/MemoryExplorer';
import { GoalTree } from './components/GoalTree';
import { KnowledgeGraph } from './components/KnowledgeGraph';
import { CrawlerPanel } from './components/CrawlerPanel';
import { MaldororPanel } from './components/MaldororPanel';
import { ProductionPanel } from './components/ProductionPanel';
import { BlenderPanel } from './components/BlenderPanel';
import { MuJoCoPanel } from './components/MuJoCoPanel';
import { DemoPanel } from './components/DemoPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { CommandPalette } from './components/CommandPalette';
import { ErrorBoundary } from './components/ErrorBoundary';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const [activeTab, setActiveTab] = useState('activity');
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const { status, events, connected, send } = useWebSocket();
  const [backendPort, setBackendPort] = useState(8765);
  const [themeTransitioning, setThemeTransitioning] = useState(false);
  const [tabKey, setTabKey] = useState(0);

  useEffect(() => {
    window.electronAPI?.getBackendPort().then((port) => {
      if (port) setBackendPort(port);
    });
  }, []);

  // Initialize theme from saved settings
  useEffect(() => {
    const saved = localStorage.getItem('ontogeny-settings');
    if (saved) {
      try {
        const settings = JSON.parse(saved);
        const root = document.documentElement;
        root.classList.toggle('light', settings.theme === 'light');
        root.classList.toggle('dark', settings.theme !== 'light');
      } catch {
        // ignore parse errors
      }
    }
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'r') {
        e.preventDefault();
        send('command', { command: 'demo_reset' });
        return;
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [send]);

  const handleCommand = useCallback((command: string, payload?: unknown) => {
    send('command', { command, ...payload as object });
  }, [send]);

  const handleNavigate = useCallback((tab: string) => {
    setThemeTransitioning(true);
    setTimeout(() => {
      setActiveTab(tab);
      setTabKey((k) => k + 1);
      setTimeout(() => setThemeTransitioning(false), 50);
    }, 150);
  }, []);

  const renderWorkspace = () => {
    switch (activeTab) {
      case 'demo':
        return <DemoPanel status={status} send={send} backendPort={backendPort} />;
      case 'activity':
        return <ActivityTimeline events={events} />;
      case 'cognitive':
        return <CognitiveState status={status} />;
      case 'memory':
        return <MemoryExplorer status={status} />;
      case 'goals':
        return <GoalTree status={status} />;
      case 'knowledge':
        return <ErrorBoundary><KnowledgeGraph status={status} /></ErrorBoundary>;
      case 'crawlers':
        return <CrawlerPanel status={status} />;
      case 'maldoror':
        return <MaldororPanel status={status} />;
      case 'production':
        return <ProductionPanel status={status} />;
      case 'blender':
        return <BlenderPanel backendPort={backendPort + 1} />;
      case 'mujoco':
        return <MuJoCoPanel backendPort={backendPort + 2} />;
      case 'settings':
        return <SettingsPanel />;
      default:
        return <ActivityTimeline events={events} />;
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden" style={{ background: 'var(--surface-2)' }}>
      <TitleBar />
      <div className="flex flex-1 min-h-0">
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onSearchOpen={() => setCommandPaletteOpen(true)}
          connected={connected}
        />
        <main
          className={`flex-1 min-w-0 overflow-hidden transition-opacity duration-200 ${
            themeTransitioning ? 'opacity-0' : 'opacity-100'
          }`}
          style={{ background: 'var(--surface-2)' }}
        >
          <div key={tabKey} className="h-full animate-panel-in">
            {renderWorkspace()}
          </div>
        </main>
      </div>
      <StatusBar status={status} connected={connected} />
      <CommandPalette
        open={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        onCommand={handleCommand}
        onNavigate={handleNavigate}
      />
    </div>
  );
}

export default App;
