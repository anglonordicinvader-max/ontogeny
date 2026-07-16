import { Panel, MetricCard } from './Panel';
import type { AgentStatus } from '@/types';

interface MaldororPanelProps {
  status: AgentStatus | null;
}

export function MaldororPanel({ status }: MaldororPanelProps) {
  const maldoror = status?.maldoror;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <Panel title="Model Status">
        <div className="grid grid-cols-2 gap-3">
          <MetricCard label="Version" value={maldoror?.version || '—'} />
          <MetricCard label="Quality Gate" value={maldoror?.qualityGate || 'pending'} />
          <MetricCard label="Improvement" value={`${(maldoror?.improvementPct || 0).toFixed(1)}%`} />
          <MetricCard label="Last Loss" value={(maldoror?.lastTrainingLoss || 0).toFixed(4)} />
        </div>
      </Panel>

      <Panel title="Evaluation Results">
        <div className="text-sm text-text-tertiary py-4 text-center">
          No evaluation results
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
