import { Minus, Square, X } from 'lucide-react';

interface TitleBarProps {
  title?: string;
}

export function TitleBar({ title = 'Ontogeny' }: TitleBarProps) {
  const handleMinimize = () => window.electronAPI?.minimize();
  const handleMaximize = () => window.electronAPI?.maximize();
  const handleClose = () => window.electronAPI?.close();

  return (
    <div
      className="flex items-center justify-between h-11 glass-overlay select-none drag"
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      <div className="flex items-center gap-3 px-4">
        <span
          className="text-sm font-bold tracking-widest text-text-primary"
          style={{ fontFamily: "'Geist', 'Geist Sans', sans-serif", letterSpacing: '0.2em' }}
        >
          {title.toUpperCase()}
        </span>
      </div>

      <div
        className="flex items-center no-drag"
        style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
      >
        <button
          onClick={handleMinimize}
          aria-label="Minimize"
          className="flex items-center justify-center w-11 h-11 hover:bg-surface-3/60 transition-colors rounded-md"
        >
          <Minus className="w-4 h-4 text-text-secondary" />
        </button>
        <button
          onClick={handleMaximize}
          aria-label="Maximize"
          className="flex items-center justify-center w-11 h-11 hover:bg-surface-3/60 transition-colors rounded-md"
        >
          <Square className="w-3 h-3 text-text-secondary" />
        </button>
        <button
          onClick={handleClose}
          aria-label="Close"
          className="flex items-center justify-center w-11 h-11 hover:bg-status-error/20 hover:text-status-error transition-colors rounded-md"
        >
          <X className="w-4 h-4 text-text-secondary" />
        </button>
      </div>
    </div>
  );
}
