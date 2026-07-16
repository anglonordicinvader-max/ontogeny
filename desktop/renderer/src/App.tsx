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
import { TrainingPanel } from './components/TrainingPanel';
import { ProductionPanel } from './components/ProductionPanel';
import { BlenderPanel } from './components/BlenderPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { CommandPalette } from './components/CommandPalette';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const [activeTab, setActiveTab] = useState('activity');
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const { status, events, connected, send } = useWebSocket();
  const [backendPort, setBackendPort] = useState(8765);

  useEffect(() => {
    window.electronAPI?.getBackendPort().then((port) => {
      if (port) setBackendPort(port);
    });
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleCommand = useCallback((command: string, payload?: unknown) => {
    send('command', { command, ...payload as object });
  }, [send]);

  const handleNavigate = useCallback((tab: string) => {
    setActiveTab(tab);
  }, []);

  const renderWorkspace = () => {
    switch (activeTab) {
      case 'activity':
        return <ActivityTimeline events={events} />;
      case 'cognitive':
        return <CognitiveState status={status} />;
      case 'memory':
        return <MemoryExplorer status={status} />;
      case 'goals':
        return <GoalTree status={status} />;
      case 'knowledge':
        return <KnowledgeGraph status={status} />;
      case 'crawlers':
        return <CrawlerPanel status={status} />;
      case 'maldoror':
        return <MaldororPanel status={status} />;
      case 'training':
        return <TrainingPanel status={status} />;
      case 'production':
        return <ProductionPanel status={status} />;
      case 'blender':
        return <BlenderPanel backendPort={backendPort + 1} />;
      case 'settings':
        return <SettingsPanel />;
      default:
        return <ActivityTimeline events={events} />;
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-surface-0 overflow-hidden">
      <TitleBar />
      <div className="flex flex-1 min-h-0">
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} connected={connected} />
        <main className="flex-1 min-w-0 overflow-hidden">
          {renderWorkspace()}
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
