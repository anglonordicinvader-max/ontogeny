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
      className="flex items-center justify-between h-11 glass-titlebar select-none drag"
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      <div className="flex items-center gap-2.5 px-4">
        <img
          src="/branding/ontogeny.png"
          alt=""
          className="w-5 h-5 object-contain"
          draggable={false}
        />
        <span
          className="text-[13px] font-semibold tracking-[0.18em] text-text-secondary"
          style={{ fontFamily: "'Geist', 'Geist Sans', sans-serif" }}
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
          className="flex items-center justify-center w-11 h-11 hover:bg-white/[0.05] transition-colors rounded-md"
        >
          <Minus className="w-3.5 h-3.5 text-text-tertiary hover:text-text-secondary transition-colors" />
        </button>
        <button
          onClick={handleMaximize}
          aria-label="Maximize"
          className="flex items-center justify-center w-11 h-11 hover:bg-white/[0.05] transition-colors rounded-md"
        >
          <Square className="w-2.5 h-2.5 text-text-tertiary hover:text-text-secondary transition-colors" />
        </button>
        <button
          onClick={handleClose}
          aria-label="Close"
          className="flex items-center justify-center w-11 h-11 hover:bg-white/[0.08] transition-colors rounded-md group"
        >
          <X className="w-3.5 h-3.5 text-text-tertiary group-hover:text-text-secondary transition-colors" />
        </button>
      </div>
    </div>
  );
}
