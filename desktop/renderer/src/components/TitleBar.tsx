import { Minus, Square, X } from 'lucide-react';

interface TitleBarProps {
  title?: string;
}

export function TitleBar({ title = 'Ontogeny' }: TitleBarProps) {
  const handleMinimize = () => window.electronAPI?.minimize();
  const handleMaximize = () => window.electronAPI?.maximize();
  const handleClose = () => window.electronAPI?.close();

  return (
    <div className="flex items-center justify-between h-10 bg-surface-1 border-b border-border select-none drag">
      <div className="flex items-center gap-3 px-4">
        <div className="w-3 h-3 rounded-full bg-accent" />
        <span className="text-xs font-medium text-text-secondary">{title}</span>
      </div>

      <div className="flex items-center no-drag">
        <button
          onClick={handleMinimize}
          className="flex items-center justify-center w-11 h-10 hover:bg-surface-3 transition-colors"
        >
          <Minus className="w-4 h-4 text-text-secondary" />
        </button>
        <button
          onClick={handleMaximize}
          className="flex items-center justify-center w-11 h-10 hover:bg-surface-3 transition-colors"
        >
          <Square className="w-3 h-3 text-text-secondary" />
        </button>
        <button
          onClick={handleClose}
          className="flex items-center justify-center w-11 h-10 hover:bg-status-error/20 hover:text-status-error transition-colors"
        >
          <X className="w-4 h-4 text-text-secondary" />
        </button>
      </div>
    </div>
  );
}
