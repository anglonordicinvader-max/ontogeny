import { Panel } from './Panel';
import type { ActivityEvent } from '@/types';
import { cn } from '@/lib/utils';
import { AlertCircle, Brain, Code, Database, Download, RefreshCw, Zap } from 'lucide-react';

interface ActivityTimelineProps {
  events: ActivityEvent[];
}

const eventIcons = {
  action: Zap,
  learning: Brain,
  planning: Brain,
  modification: Code,
  error: AlertCircle,
  training: RefreshCw,
  acquisition: Download,
  demo: Database,
};

const eventColors = {
  action: 'text-accent',
  learning: 'text-status-success',
  planning: 'text-text-secondary',
  modification: 'text-status-warning',
  error: 'text-status-error',
  training: 'text-status-info',
  acquisition: 'text-accent',
  demo: 'text-status-success',
};

export function ActivityTimeline({ events }: ActivityTimelineProps) {
  return (
    <Panel title="Activity Timeline" className="h-full">
      <div className="space-y-1">
        {events.length === 0 ? (
          <div className="text-center py-8 text-text-tertiary text-sm">
            Waiting for activity...
          </div>
        ) : (
          events.map((event, index) => {
            const Icon = eventIcons[event.type] || Zap;
            const color = eventColors[event.type] || 'text-text-tertiary';
            return (
              <div
                key={event.id}
                className={cn(
                  'flex items-start gap-3 py-2 px-2 rounded-md hover:bg-surface-2 transition-all duration-150',
                  'animate-slide-up'
                )}
                style={{ animationDelay: `${index * 20}ms` }}
              >
                <Icon className={cn('w-4 h-4 mt-0.5 shrink-0', color)} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary truncate">{event.message}</p>
                  <p className="text-2xs text-text-tertiary mt-0.5">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </Panel>
  );
}
