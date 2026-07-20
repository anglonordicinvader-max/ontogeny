import { useState } from 'react';
import type { AgentStatus } from '@/types';
import { APP_VERSION } from '@/types';
import { formatDuration } from '@/lib/utils';
import { cn } from '@/lib/utils';
import { ChevronUp, X } from 'lucide-react';

interface StatusBarProps {
  status: AgentStatus | null;
  connected: boolean;
}

const stateLabels: Record<string, string> = {
  idle: 'Idle',
  thinking: 'Thinking',
  planning: 'Planning',
  executing: 'Executing',
  learning: 'Learning',
  self_modifying: 'Self-modifying',
  waiting: 'Waiting',
  running: 'Running',
  training: 'Training',
  error: 'Error',
  paused: 'Paused',
};

export function StatusBar({ status, connected }: StatusBarProps) {
  const [expanded, setExpanded] = useState(false);

  const stateLabel = stateLabels[status?.state || 'idle'] || 'Unknown';
  const modelVersion = status?.maldoror?.version || '—';

  return (
    <>
      <div
        className="relative flex items-center justify-between h-9 px-4 border-t transition-colors"
        style={{
          background: 'var(--statusbar-bg)',
          borderColor: 'var(--statusbar-border)',
          backdropFilter: 'blur(16px) saturate(180%)',
          WebkitBackdropFilter: 'blur(16px) saturate(180%)',
        }}
      >
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-2">
            <div className={cn('status-dot', connected ? 'status-dot-active' : 'status-dot-error')} />
            <span className="text-2xs text-text-tertiary">
              {connected ? 'UI Connected' : 'UI Disconnected'}
            </span>
          </div>
          {status && (
            <>
              <span className="text-2xs text-text-tertiary">
                Backend <span className="text-text-secondary">{stateLabel}</span>
              </span>
              <span className="text-2xs text-text-tertiary">
                Model <span className="text-text-secondary">{modelVersion}</span>
              </span>
              <span className="text-2xs text-text-tertiary" style={{ fontFamily: "'Geist Mono', monospace" }}>
                #{status.iteration}
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-5">
          {status && (
            <>
              <span className="text-2xs text-text-tertiary">
                Last cycle <span className="text-text-secondary" style={{ fontFamily: "'Geist Mono', monospace" }}>{formatDuration(status.uptime * 1000)}</span>
              </span>
              <span className="text-2xs text-text-tertiary" style={{ fontFamily: "'Geist Mono', monospace" }}>
                runtime {formatDuration(status.uptime * 1000)}
              </span>
            </>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-2xs text-text-tertiary hover:text-text-secondary transition-colors"
            aria-label="Toggle system details"
          >
            <ChevronUp className={cn('w-3 h-3 transition-transform', expanded ? '' : 'rotate-180')} />
          </button>
        </div>
      </div>

      {expanded && (
        <div
          className="absolute bottom-9 right-0 left-0 z-40 border-t animate-fade-in"
          style={{
            background: 'var(--glass-bg)',
            backdropFilter: 'blur(20px) saturate(180%)',
            WebkitBackdropFilter: 'blur(20px) saturate(180%)',
            borderColor: 'var(--glass-border)',
          }}
        >
          <div className="max-w-2xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-text-secondary">System Health</span>
              <button onClick={() => setExpanded(false)} className="text-text-tertiary hover:text-text-secondary">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-x-8 gap-y-2">
              <DetailRow label="UI Bridge" value={connected ? 'Connected' : 'Disconnected'} status={connected ? 'green' : 'red'} />
              <DetailRow label="Backend API" value={connected ? 'Online' : 'Offline'} status={connected ? 'green' : 'red'} />
              <DetailRow label="WebSocket" value={connected ? 'Open' : 'Closed'} status={connected ? 'green' : 'red'} />
              <DetailRow label="Active Model" value={modelVersion} status="gray" />
              <DetailRow label="Blender" value={status?.embodimentDetails?.blender?.lifecycle || (status?.embodiment?.blender ? 'ready' : 'unavailable')} status={status?.embodiment?.blender ? 'green' : 'gray'} />
              <DetailRow label="MuJoCo" value={status?.embodimentDetails?.mujoco?.lifecycle || (status?.embodiment?.mujoco ? 'ready' : 'unavailable')} status={status?.embodiment?.mujoco ? 'green' : 'gray'} />
              <DetailRow label="Sandbox" value={status?.state === 'demo' ? 'Demo Mode' : 'Standby'} status="gray" />
              <DetailRow label="Current Cycle" value={`#${status?.iteration || 0}`} status="gray" />
              <DetailRow label="Runtime" value={status ? formatDuration(status.uptime * 1000) : '—'} status="gray" />
              <DetailRow label="State" value={stateLabel} status={status?.state === 'error' ? 'red' : 'green'} />
              <DetailRow label="Version" value={`v${APP_VERSION}`} status="gray" />
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function DetailRow({ label, value, status }: { label: string; value: string; status: 'green' | 'amber' | 'red' | 'gray' }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-2xs text-text-tertiary">{label}</span>
      <div className="flex items-center gap-1.5">
        <div className={cn('status-dot',
          status === 'green' && 'status-dot-active',
          status === 'amber' && 'status-dot-warning',
          status === 'red' && 'status-dot-error',
          status === 'gray' && 'status-dot-idle'
        )} />
        <span className="text-2xs text-text-secondary" style={{ fontFamily: "'Geist Mono', monospace" }}>{value}</span>
      </div>
    </div>
  );
}
