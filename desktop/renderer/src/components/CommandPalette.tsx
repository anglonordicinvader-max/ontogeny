import { useState, useEffect, useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';
import { Search, X, Terminal, Brain, Database, Target, GitBranch, Workflow, Cpu, Monitor, Eye, Settings, Play, Square, RefreshCw } from 'lucide-react';

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onCommand: (command: string, payload?: unknown) => void;
  onNavigate: (tab: string) => void;
}

interface Command {
  id: string;
  label: string;
  category: string;
  icon: React.ReactNode;
  action: () => void;
  keywords: string[];
}

export function CommandPalette({ open, onClose, onCommand, onNavigate }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: Command[] = [
    { id: 'start', label: 'Start Agent', category: 'Agent', icon: <Play className="w-4 h-4" />, action: () => onCommand('start_agent'), keywords: ['start', 'run', 'begin', 'agent'] },
    { id: 'stop', label: 'Stop Agent', category: 'Agent', icon: <Square className="w-4 h-4" />, action: () => onCommand('stop_agent'), keywords: ['stop', 'halt', 'pause', 'agent'] },
    { id: 'cycle', label: 'Run Single Cycle', category: 'Agent', icon: <RefreshCw className="w-4 h-4" />, action: () => onCommand('run_cycle'), keywords: ['cycle', 'step', 'run', 'single'] },
    { id: 'demo-start', label: 'Start Demo', category: 'Demo', icon: <Play className="w-4 h-4" />, action: () => { onCommand('demo_start'); onNavigate('demo'); onClose(); }, keywords: ['demo', 'start', 'showcase', 'hackathon'] },
    { id: 'demo-reset', label: 'Reset Demo', category: 'Demo', icon: <RefreshCw className="w-4 h-4" />, action: () => onCommand('demo_reset'), keywords: ['demo', 'reset', 'clear'] },
    { id: 'nav-demo', label: 'Go to Demo', category: 'Navigation', icon: <Play className="w-4 h-4" />, action: () => { onNavigate('demo'); onClose(); }, keywords: ['demo', 'nav'] },
    { id: 'nav-activity', label: 'Go to Activity', category: 'Navigation', icon: <Terminal className="w-4 h-4" />, action: () => { onNavigate('activity'); onClose(); }, keywords: ['activity', 'timeline', 'events', 'nav'] },
    { id: 'nav-cognitive', label: 'Go to Cognitive State', category: 'Navigation', icon: <Brain className="w-4 h-4" />, action: () => { onNavigate('cognitive'); onClose(); }, keywords: ['cognitive', 'brain', 'drives', 'emotion', 'nav'] },
    { id: 'nav-memory', label: 'Go to Memory', category: 'Navigation', icon: <Database className="w-4 h-4" />, action: () => { onNavigate('memory'); onClose(); }, keywords: ['memory', 'episodic', 'semantic', 'nav'] },
    { id: 'nav-goals', label: 'Go to Goals', category: 'Navigation', icon: <Target className="w-4 h-4" />, action: () => { onNavigate('goals'); onClose(); }, keywords: ['goals', 'targets', 'objectives', 'nav'] },
    { id: 'nav-knowledge', label: 'Go to Knowledge Graph', category: 'Navigation', icon: <GitBranch className="w-4 h-4" />, action: () => { onNavigate('knowledge'); onClose(); }, keywords: ['knowledge', 'graph', 'concepts', 'nav'] },
    { id: 'nav-crawlers', label: 'Go to Knowledge Acquisition', category: 'Navigation', icon: <Workflow className="w-4 h-4" />, action: () => { onNavigate('crawlers'); onClose(); }, keywords: ['knowledge', 'acquisition', 'sources', 'evidence', 'nav'] },
    { id: 'nav-maldoror', label: 'Go to Maldoror', category: 'Navigation', icon: <Cpu className="w-4 h-4" />, action: () => { onNavigate('maldoror'); onClose(); }, keywords: ['maldoror', 'model', 'training', 'nav'] },
    { id: 'nav-production', label: 'Go to Production', category: 'Navigation', icon: <Monitor className="w-4 h-4" />, action: () => { onNavigate('production'); onClose(); }, keywords: ['production', 'monitoring', 'health', 'nav'] },
    { id: 'nav-blender', label: 'Go to Blender Sandbox', category: 'Navigation', icon: <Eye className="w-4 h-4" />, action: () => { onNavigate('blender'); onClose(); }, keywords: ['blender', 'sandbox', '3d', 'simulation', 'nav'] },
    { id: 'nav-settings', label: 'Go to Settings', category: 'Navigation', icon: <Settings className="w-4 h-4" />, action: () => { onNavigate('settings'); onClose(); }, keywords: ['settings', 'config', 'preferences', 'nav'] },
  ];

  const filtered = commands.filter((cmd) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return cmd.label.toLowerCase().includes(q) ||
      cmd.category.toLowerCase().includes(q) ||
      cmd.keywords.some((k) => k.includes(q));
  });

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const executeCommand = useCallback((cmd: Command) => {
    cmd.action();
    onClose();
  }, [onClose]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      e.preventDefault();
      executeCommand(filtered[selectedIndex]);
    } else if (e.key === 'Escape') {
      onClose();
    }
  }, [filtered, selectedIndex, executeCommand, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div
        className="relative w-full max-w-lg glass-overlay rounded-xl shadow-xl overflow-hidden animate-fade-in"
        role="dialog"
        aria-label="Command palette"
        aria-modal="true"
      >
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
          <Search className="w-4 h-4 text-text-tertiary" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search commands..."
            aria-label="Search commands"
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-tertiary outline-none"
          />
          <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary" aria-label="Close">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="max-h-80 overflow-y-auto py-2" role="listbox">
          {filtered.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-text-tertiary">
              No commands found
            </div>
          ) : (
            filtered.map((cmd, i) => (
              <button
                key={cmd.id}
                onClick={() => executeCommand(cmd)}
                role="option"
                aria-selected={i === selectedIndex}
                className={cn(
                  'w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors',
                  i === selectedIndex
                    ? 'bg-surface-3 text-text-primary border-l-2 border-accent shadow-[inset_4px_0_12px_-4px_var(--bloom-color)]'
                    : 'text-text-secondary hover:bg-surface-2 border-l-2 border-transparent'
                )}
              >
                <span className="text-text-tertiary">{cmd.icon}</span>
                <span className="flex-1 text-left">{cmd.label}</span>
                <span className="text-2xs text-text-tertiary">{cmd.category}</span>
              </button>
            ))
          )}
        </div>
        <div className="flex items-center gap-4 px-4 py-2 border-t border-border text-2xs text-text-tertiary">
          <span>↑↓ navigate</span>
          <span>↵ select</span>
          <span>esc close</span>
        </div>
      </div>
    </div>
  );
}
