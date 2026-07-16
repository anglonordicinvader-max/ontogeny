import { Panel, MetricCard, ProgressBar } from './Panel';
import type { AgentStatus } from '@/types';

interface CognitiveStateProps {
  status: AgentStatus | null;
}

export function CognitiveState({ status }: CognitiveStateProps) {
  const drives = status?.drives || {
    curiosity: 0,
    mastery: 0,
    competence: 0,
    autonomy: 0,
    novelty: 0,
  };

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <Panel title="Intrinsic Drives">
        <div className="space-y-3">
          {Object.entries(drives).map(([name, value]) => (
            <div key={name} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-secondary capitalize">{name}</span>
                <span className="text-2xs text-text-tertiary tabular-nums">{(value * 100).toFixed(0)}%</span>
              </div>
              <ProgressBar value={value * 100} />
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Emotional State">
        <div className="glass-subtle rounded-md p-4">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="Mood" value={status?.mood || '—'} />
            <MetricCard label="Confidence" value={`${((status?.drives?.competence || 0) * 100).toFixed(0)}%`} />
          </div>
        </div>
      </Panel>

      <Panel title="Reasoning">
        <div className="grid grid-cols-2 gap-3">
          <MetricCard label="Quality" value="—" />
          <MetricCard label="Uncertainty" value="—" />
        </div>
      </Panel>

      <Panel title="Self-Reflection">
        <div className="text-sm text-text-tertiary py-4 text-center">
          No reflections yet
        </div>
      </Panel>
    </div>
  );
}
