import type { AgentStatus } from '@/types';
import { formatDuration } from '@/lib/utils';

interface StatusBarProps {
  status: AgentStatus | null;
  connected: boolean;
}

export function StatusBar({ status, connected }: StatusBarProps) {
  return (
    <div
      className="flex items-center justify-between h-9 px-4 border-t border-border"
      style={{ background: 'var(--surface-1)' }}
    >
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className={`status-dot ${connected ? 'status-dot-active' : 'status-dot-error'}`} />
          <span className="text-2xs text-text-tertiary">
            {connected ? 'Backend Connected' : 'Backend Disconnected'}
          </span>
        </div>
        {status && (
          <>
            <span className="text-2xs text-text-tertiary">
              Iteration {status.iteration}
            </span>
            <span className="text-2xs text-text-tertiary">
              {formatDuration(status.uptime * 1000)}
            </span>
          </>
        )}
      </div>
      <div className="flex items-center gap-4">
        {status && (
          <>
            <span className="text-2xs text-text-tertiary">
              State: <span className="text-text-secondary">{status.state}</span>
            </span>
            <span className="text-2xs text-text-tertiary">
              Mood: <span className="text-text-secondary">{status.mood}</span>
            </span>
          </>
        )}
      </div>
    </div>
  );
}
