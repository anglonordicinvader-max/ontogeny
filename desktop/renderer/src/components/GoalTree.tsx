import { Panel, MetricCard } from './Panel';
import type { AgentStatus } from '@/types';

interface GoalTreeProps {
  status: AgentStatus | null;
}

export function GoalTree({ status }: GoalTreeProps) {
  const activeGoal = status?.activeGoal;
  const drives = status?.drives;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <Panel title="Active Goal" accentGlow>
        {activeGoal ? (
          <div className="p-3 bg-surface-2 rounded-md">
            <p className="text-sm text-text-primary">{activeGoal}</p>
          </div>
        ) : (
          <div className="text-sm text-text-tertiary py-4 text-center">
            No active goal
          </div>
        )}
      </Panel>

      <Panel title="Goal Progress" accentGlow>
        <div className="space-y-3">
          <MetricCard
            label="Curiosity Drive"
            value={`${((drives?.curiosity || 0) * 100).toFixed(0)}%`}
          />
          <MetricCard
            label="Mastery Drive"
            value={`${((drives?.mastery || 0) * 100).toFixed(0)}%`}
          />
          <MetricCard
            label="Competence Drive"
            value={`${((drives?.competence || 0) * 100).toFixed(0)}%`}
          />
          <MetricCard
            label="Autonomy Drive"
            value={`${((drives?.autonomy || 0) * 100).toFixed(0)}%`}
          />
          <MetricCard
            label="Novelty Drive"
            value={`${((drives?.novelty || 0) * 100).toFixed(0)}%`}
          />
        </div>
      </Panel>

      <Panel title="Goal History">
        <div className="text-sm text-text-tertiary py-4 text-center">
          No goal history
        </div>
      </Panel>
    </div>
  );
}
