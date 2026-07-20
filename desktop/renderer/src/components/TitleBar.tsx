import { Minus, Square, X } from 'lucide-react';

interface TitleBarProps {
  title?: string;
}

export function TitleBar({ title = 'Ontogeny' }: TitleBarProps) {
  const handleMinimize = () => window.electronAPI?.minimize();
  const handleMaximize = () => window.electronAPI?.maximize();
  const handleClose = () => window.electronAPI?.close();

  const isLight = document.documentElement.classList.contains('light');

  return (
    <div
      className="flex items-center justify-between h-11 glass-titlebar select-none drag"
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      <div className="flex items-center px-4">
        <span
          className="text-[13px] font-semibold text-text-secondary"
          style={{
            fontFamily: "'Geist', 'Geist Sans', sans-serif",
            letterSpacing: '0.32em',
          }}
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
          className="flex items-center justify-center w-11 h-11 transition-colors rounded-md"
          style={{ background: 'transparent' }}
          onMouseEnter={(e) => e.currentTarget.style.background = isLight ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
        >
          <Minus className="w-3.5 h-3.5 text-text-tertiary hover:text-text-secondary transition-colors" />
        </button>
        <button
          onClick={handleMaximize}
          aria-label="Maximize"
          className="flex items-center justify-center w-11 h-11 transition-colors rounded-md"
          style={{ background: 'transparent' }}
          onMouseEnter={(e) => e.currentTarget.style.background = isLight ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
        >
          <Square className="w-2.5 h-2.5 text-text-tertiary hover:text-text-secondary transition-colors" />
        </button>
        <button
          onClick={handleClose}
          aria-label="Close"
          className="flex items-center justify-center w-11 h-11 transition-colors rounded-md group"
          style={{ background: 'transparent' }}
          onMouseEnter={(e) => e.currentTarget.style.background = isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
        >
          <X className="w-3.5 h-3.5 text-text-tertiary group-hover:text-text-secondary transition-colors" />
        </button>
      </div>
    </div>
  );
}
