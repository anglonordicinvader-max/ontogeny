import { Panel, MetricCard, StatusBadge } from './Panel';
import type { AgentStatus } from '@/types';

interface ProductionPanelProps {
  status: AgentStatus | null;
}

export function ProductionPanel({ status }: ProductionPanelProps) {
  const production = status?.production;

  const circuitColors = {
    closed: 'success' as const,
    open: 'error' as const,
    'half-open': 'warning' as const,
  };

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <Panel title="Performance Metrics">
        <div className="grid grid-cols-2 gap-3">
          <MetricCard label="Latency" value={production?.latency?.toString() || '0'} unit="ms" />
          <MetricCard label="Quality" value={`${((production?.qualityScore || 0) * 100).toFixed(1)}%`} />
          <MetricCard label="Error Rate" value={`${((production?.errorRate || 0) * 100).toFixed(2)}%`} />
          <MetricCard label="Circuit Breaker" value={production?.circuitBreaker || 'closed'} />
        </div>
      </Panel>

      <Panel title="Health Status">
        <div className="space-y-2">
          <StatusBadge
            status={circuitColors[production?.circuitBreaker || 'closed']}
            label={`Circuit: ${production?.circuitBreaker || 'closed'}`}
          />
          <StatusBadge
            status={(production?.errorRate || 0) < 0.05 ? 'success' : 'error'}
            label={`Error Rate: ${((production?.errorRate || 0) * 100).toFixed(2)}%`}
          />
          <StatusBadge
            status={(production?.latency || 0) < 200 ? 'success' : 'warning'}
            label={`Latency: ${production?.latency || 0}ms`}
          />
        </div>
      </Panel>

      <Panel title="Retraining Trigger">
        <div className="text-sm text-text-tertiary py-4 text-center">
          No retraining pending
        </div>
      </Panel>
    </div>
  );
}
