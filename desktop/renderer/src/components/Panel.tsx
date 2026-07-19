import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

interface PanelProps {
  title: string;
  children: ReactNode;
  className?: string;
  actions?: ReactNode;
  mono?: boolean;
  accentGlow?: boolean;
}

export function Panel({ title, children, className, actions, mono, accentGlow }: PanelProps) {
  return (
    <div className={cn('panel flex flex-col', accentGlow && 'panel-accent-glow', className)}>
      <div className="panel-header relative z-10">
        <span className={cn('panel-title', mono && 'font-mono')}>{title}</span>
        {actions && <div className="flex items-center gap-1">{actions}</div>}
      </div>
      <div className="panel-content flex-1 overflow-y-auto relative z-10">{children}</div>
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
}

export function MetricCard({ label, value, unit, trend, className }: MetricCardProps) {
  return (
    <div className={cn('metric-card', className)}>
      <div className="metric-label">{label}</div>
      <div className="flex items-baseline gap-1">
        <span className="metric-value">{value}</span>
        {unit && <span className="text-xs text-text-tertiary">{unit}</span>}
      </div>
      {trend && (
        <div className={cn(
          'text-2xs mt-1',
          trend === 'up' && 'text-status-success',
          trend === 'down' && 'text-status-error',
          trend === 'neutral' && 'text-text-tertiary'
        )}>
          {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '—'}
        </div>
      )}
    </div>
  );
}

interface StatusBadgeProps {
  status: 'success' | 'warning' | 'error' | 'info' | 'idle';
  label: string;
  className?: string;
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  return (
    <div className={cn('flex items-center gap-2 px-2 py-1 rounded-md bg-surface-2', className)}>
      <div className={cn(
        'status-dot',
        status === 'success' && 'status-dot-active',
        status === 'warning' && 'status-dot-warning',
        status === 'error' && 'status-dot-error',
        status === 'info' && 'bg-status-info',
        status === 'idle' && 'status-dot-idle'
      )} />
      <span className="text-xs text-text-secondary">{label}</span>
    </div>
  );
}

interface ProgressBarProps {
  value: number;
  max?: number;
  className?: string;
  showLabel?: boolean;
}

export function ProgressBar({ value, max = 100, className, showLabel }: ProgressBarProps) {
  const percentage = Math.min((value / max) * 100, 100);
  const isActive = percentage > 0;
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex-1 h-1.5 bg-surface-3 rounded-full overflow-hidden relative">
        <div
          className={cn(
            'h-full bg-accent rounded-full transition-all duration-300',
            isActive && 'shadow-[0_0_12px_2px_var(--bloom-color)]'
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-2xs text-text-tertiary tabular-nums">{Math.round(percentage)}%</span>
      )}
    </div>
  );
}
