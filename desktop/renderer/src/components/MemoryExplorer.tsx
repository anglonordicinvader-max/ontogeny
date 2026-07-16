import { Panel, MetricCard, ProgressBar } from './Panel';
import type { AgentStatus } from '@/types';

interface MemoryExplorerProps {
  status: AgentStatus | null;
}

export function MemoryExplorer({ status }: MemoryExplorerProps) {
  const memory = status?.memory || { working: 0, episodic: 0, semantic: 0, procedural: 0 };
  const total = memory.working + memory.episodic + memory.semantic + memory.procedural;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <Panel title="Memory Layers">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="Working" value={memory.working} />
            <MetricCard label="Episodic" value={memory.episodic} />
            <MetricCard label="Semantic" value={memory.semantic} />
            <MetricCard label="Procedural" value={memory.procedural} />
          </div>

          <div className="space-y-2">
            <div className="text-2xs text-text-tertiary uppercase tracking-wider">Distribution</div>
            {Object.entries(memory).map(([type, count]) => (
              <div key={type} className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-text-secondary capitalize">{type}</span>
                  <span className="text-2xs text-text-tertiary">{count}</span>
                </div>
                <ProgressBar value={count} max={total || 1} />
              </div>
            ))}
          </div>
        </div>
      </Panel>

      <Panel title="Working Memory Contents">
        <div className="text-sm text-text-tertiary py-4 text-center">
          {memory.working > 0 ? `${memory.working} items in working memory` : 'No active items'}
        </div>
      </Panel>

      <Panel title="Recent Episodic">
        <div className="text-sm text-text-tertiary py-4 text-center">
          {memory.episodic > 0 ? `${memory.episodic} episodic memories` : 'No recent episodes'}
        </div>
      </Panel>
    </div>
  );
}
