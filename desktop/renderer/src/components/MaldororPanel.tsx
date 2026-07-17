import { Panel, MetricCard } from './Panel';
import type { AgentStatus } from '@/types';

interface MaldororPanelProps {
  status: AgentStatus | null;
}

export function MaldororPanel({ status }: MaldororPanelProps) {
  const maldoror = status?.maldoror;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4 animate-panel-in">
      <Panel title="Model Status">
        <div className="grid grid-cols-2 gap-3">
          <MetricCard label="Version" value={maldoror?.version || '—'} />
          <MetricCard label="Quality Gate" value={maldoror?.qualityGate || 'pending'} />
          <MetricCard
            label="Improvement"
            value={`${(maldoror?.improvementPct || 0).toFixed(1)}%`}
            trend={maldoror?.improvementPct ? 'up' : 'neutral'}
          />
          <MetricCard label="Last Loss" value={(maldoror?.lastTrainingLoss || 0).toFixed(4)} />
        </div>
      </Panel>

      <Panel title="Training">
        <div className="grid grid-cols-2 gap-3">
          <MetricCard label="Version" value={maldoror?.version || '—'} />
          <MetricCard label="Quality Gate" value={maldoror?.qualityGate || 'pending'} />
          <MetricCard
            label="Improvement"
            value={`${(maldoror?.improvementPct || 0).toFixed(1)}%`}
          />
          <MetricCard label="Last Loss" value={(maldoror?.lastTrainingLoss || 0).toFixed(4)} />
        </div>
      </Panel>

      <Panel title="Training Metrics">
        <div className="grid grid-cols-2 gap-3">
          <MetricCard label="Epochs" value="—" />
          <MetricCard label="Batch Size" value="—" />
          <MetricCard label="Learning Rate" value="—" />
          <MetricCard label="Loss" value={(maldoror?.lastTrainingLoss || 0).toFixed(4)} />
        </div>
      </Panel>

      <Panel title="Loss Curve">
        <div className="h-48 flex items-center justify-center text-text-tertiary text-sm">
          No training data
        </div>
      </Panel>

      <Panel title="Evaluation Results">
        <div className="text-sm text-text-tertiary py-4 text-center">
          No evaluation results
        </div>
      </Panel>

      <Panel title="Population">
        <div className="text-sm text-text-tertiary py-4 text-center">
          No population data
        </div>
      </Panel>

      <Panel title="Rollback History">
        <div className="text-sm text-text-tertiary py-4 text-center">
          No rollback history
        </div>
      </Panel>
    </div>
  );
}
